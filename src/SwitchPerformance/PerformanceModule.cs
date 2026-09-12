using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Text.Json;
using Celeste;
using Celeste.Mod;
using Microsoft.Xna.Framework;
using Monocle;
using MonoMod.RuntimeDetour;

namespace SwitchPerformance;

public sealed class PerformanceModule : EverestModule {
    private const BindingFlags Methods = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
    private readonly List<Hook> hooks = new();
    private readonly List<Meter> meters = new();
    private readonly BlockingCollection<object> output = new(512);
    private Thread? writer;
    private long nextWindow, windowStart, lastTick, dropped;
    private string contextStart = "startup";
    private int window;
    private volatile bool stopped;
    private readonly string run = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N")[..8];
    private string directory = "";
    private readonly Meter intervals = new("FrameInterval");

    public override void Load() {
        directory = Path.Combine(Everest.PathGame, "performance", run);
        Directory.CreateDirectory(directory);
        writer = new Thread(WriteRecords) { IsBackground = true, Name = "SwitchPerformance writer" };
        writer.Start();
        Emit(new { kind = "start", run, utc = DateTime.UtcNow, frequency = Stopwatch.Frequency,
            runtime = Environment.Version.ToString(), processorCount = Environment.ProcessorCount,
            purpose = "measurement only; each hook calls orig exactly once",
            tieredCompilation = Environment.GetEnvironmentVariable("DOTNET_TieredCompilation"),
            quickJit = Environment.GetEnvironmentVariable("DOTNET_TC_QuickJit"),
            minOpts = Environment.GetEnvironmentVariable("DOTNET_JITMinOpts") });
        windowStart = Stopwatch.GetTimestamp(); nextWindow = windowStart + Stopwatch.Frequency * 10;
        meters.Add(intervals);
        TimedGameTime<Engine>("Engine.Update", "Update");
        TimedGameTime<Engine>("Engine.Draw", "Draw");
        TimedVoid<Game>("Game.EndDraw", "EndDraw");
        TimedVoid<Level>("Level.Update", "Update");
        TimedVoid<Level>("Level.Render", "Render");
        TimedVoid<Level>("Level.BeforeRender", "BeforeRender");
        TimedVoid<Scene>("Scene.Update", "Update");
        TimedVoid<EntityList>("EntityList.Update", "Update");
        TimedVoid<VirtualTexture>("VirtualTexture.Reload", "Reload");
        var checksums = NewMeter("Everest.GetChecksum(path)");
        Add(typeof(Everest).GetMethod("GetChecksum", Methods, null, new[] { typeof(string) }, null),
            (Func<Func<string, byte[]>, string, byte[]>)((orig, path) => {
                long start = checksums.Start();
                try { return orig(path); }
                finally {
                    checksums.Stop(start);
                    Emit(new { kind = "checksum", file = Path.GetFileName(path), ticks = Stopwatch.GetTimestamp()-start });
                }
            }), "Everest.GetChecksum(path)");
        Add(typeof(Everest.Loader).GetMethod("LoadZip", Methods, null, new[] { typeof(string) }, null),
            (Action<Action<string>, string>)((orig, path) => {
                long start = Stopwatch.GetTimestamp();
                try { orig(path); }
                finally { Emit(new { kind = "loadZip", file = Path.GetFileName(path), ticks = Stopwatch.GetTimestamp()-start }); }
            }), "Everest.Loader.LoadZip");
        var tick = NewMeter("Game.Tick");
        Add(typeof(Game).GetMethod("Tick", Methods, null, Type.EmptyTypes, null),
            (Action<Action<Game>, Game>)((orig, self) => {
                long start = tick.Start();
                if (lastTick != 0) intervals.Stop(lastTick);
                lastTick = start;
                try { orig(self); }
                finally {
                    tick.Stop(start);
                    long now = Stopwatch.GetTimestamp();
                    if (now >= nextWindow) {
                        try { Snapshot(now); }
                        catch (Exception e) {
                            nextWindow = long.MaxValue;
                            Emit(new { kind = "snapshotFailure", error = e.ToString() });
                        }
                    }
                }
            }), "Game.Tick");
        Logger.Log("SwitchPerformance", "Measurement hooks loaded; closed JSON records under " + directory);
    }

    private Meter NewMeter(string name) { var meter = new Meter(name); meters.Add(meter); return meter; }
    private void TimedVoid<T>(string label, string method) {
        var meter = NewMeter(label);
        Add(typeof(T).GetMethod(method, Methods, null, Type.EmptyTypes, null),
            (Action<Action<T>, T>)((orig, self) => {
                long start = meter.Start(); try { orig(self); } finally { meter.Stop(start); }
            }), label);
    }
    private void TimedGameTime<T>(string label, string method) {
        var meter = NewMeter(label);
        Add(typeof(T).GetMethod(method, Methods, null, new[] { typeof(GameTime) }, null),
            (Action<Action<T, GameTime>, T, GameTime>)((orig, self, time) => {
                long start = meter.Start(); try { orig(self, time); } finally { meter.Stop(start); }
            }), label);
    }
    private void Add(MethodInfo? method, Delegate handler, string label) {
        try {
            if (method == null) throw new MissingMethodException(label);
            hooks.Add(new Hook(method, handler));
            Emit(new { kind = "hook", label, success = true, declaringType = method.DeclaringType?.FullName });
        } catch (Exception e) {
            Emit(new { kind = "hook", label, success = false, error = e.ToString() });
            Logger.Log("SwitchPerformance", "Could not measure " + label + ": " + e.Message);
        }
    }
    private void Snapshot(long now) {
        // Aggregate costs overlap by design; do not sum parent and child meters.
        Scene? scene = Engine.Scene; Level? level = scene as Level;
        string context = level == null ? scene?.GetType().FullName ?? "none" :
            level.Session.Area.SID + "/" + level.Session.Level + (level.Paused ? "/paused" : "/playing");
        Emit(new { kind = "window", index = window++, start = windowStart, end = now,
            contextStart, contextEnd = context, paused = level?.Paused,
            entities = scene?.Entities.Count, gc0 = GC.CollectionCount(0), gc1 = GC.CollectionCount(1),
            gc2 = GC.CollectionCount(2), heapBytes = GC.GetTotalMemory(false),
            allocatedBytes = GC.GetTotalAllocatedBytes(false), gcPauseTicks = GC.GetTotalPauseDuration().Ticks,
            meters = meters.Select(m => m.Snapshot()).ToArray(), dropped = Interlocked.Read(ref dropped) });
        contextStart = context; windowStart = now; nextWindow = now + Stopwatch.Frequency * 10;
    }
    private void Emit(object record) {
        if (stopped) return;
        try { if (!output.TryAdd(record)) Interlocked.Increment(ref dropped); }
        catch (InvalidOperationException) { /* teardown raced with a loader hook */ }
    }
    private void WriteRecords() {
        int index = 0;
        try {
            foreach (object record in output.GetConsumingEnumerable()) {
                // Close each record so readers can inspect a completed file.
                string path = Path.Combine(directory, (index++).ToString("D6") + ".json");
                File.WriteAllText(path, JsonSerializer.Serialize(record));
            }
        } catch (Exception e) {
            Interlocked.Increment(ref dropped);
            Logger.Log("SwitchPerformance", "Profile writer stopped: " + e.Message);
        }
    }
    public override void Unload() {
        foreach (Hook hook in Enumerable.Reverse(hooks)) hook.Dispose();
        hooks.Clear();
        if (!stopped) {
            Emit(new { kind = "stop", utc = DateTime.UtcNow, dropped = Interlocked.Read(ref dropped) });
            stopped = true; output.CompleteAdding(); writer?.Join(2000);
        }
    }
}
