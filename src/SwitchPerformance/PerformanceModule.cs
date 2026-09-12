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

public sealed partial class PerformanceModule : EverestModule {
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
        if (!Settings.Diagnostics) {
            InstallChecksumBuffering();
            InstallChecksumHook(false);
            Logger.Log("SwitchPerformance", "Checksum buffer hook loaded; frame profiling and profile file output disabled.");
            return;
        }
        directory = Path.Combine(Everest.PathGame, "performance", run);
        Directory.CreateDirectory(directory);
        writer = new Thread(WriteRecords) { IsBackground = true, Name = "SwitchPerformance writer" };
        writer.Start();
        Emit(new { kind = "start", run, utc = DateTime.UtcNow, frequency = Stopwatch.Frequency,
            runtime = Environment.Version.ToString(), processorCount = Environment.ProcessorCount,
            purpose = "diagnostics with optional scoped checksum buffering; outer hooks call orig exactly once",
            diagnostics = Settings.Diagnostics, bufferChecksums = Settings.BufferChecksums,
            detailedEntities = Settings.DetailedEntities,
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
        if (Settings.DetailedEntities) InstallEntitySampling();
        TimedScene<GameplayRenderer>("Render");
        TimedScene<LightingRenderer>("BeforeRender");
        TimedScene<LightingRenderer>("Render");
        TimedScene<BackdropRenderer>("Render");
        TimedVoid<Microsoft.Xna.Framework.Graphics.SpriteBatch>("SpriteBatch.FlushBatch", "FlushBatch");
        TimedVoid<VirtualTexture>("VirtualTexture.Reload", "Reload");
        InstallChecksumBuffering();
        InstallChecksumHook(true);
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

    private void InstallChecksumHook(bool diagnostics) {
        Meter? checksums = diagnostics ? NewMeter("Everest.GetChecksum(path)") : null;
        Add(typeof(Everest).GetMethod("GetChecksum", Methods, null, new[] { typeof(string) }, null),
            (Func<Func<string, byte[]>, string, byte[]>)((orig, path) => {
                long start = checksums?.Start() ?? 0;
                int previousDepth = checksumDepth++;
                try { return orig(path); }
                finally {
                    checksumDepth = previousDepth;
                    if (checksums != null) {
                        checksums.Stop(start);
                        Emit(new { kind = "checksum", file = Path.GetFileName(path), ticks = Stopwatch.GetTimestamp()-start });
                    }
                }
            }), "Everest.GetChecksum(path)");
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
                bool update = label == "Engine.Update";
                if (update) SampleUpdate = ++updateNumber % 120 == 0;
                else SampleRender = ++drawNumber % 120 == 0;
                if (update && SampleUpdate) sampledUpdates++;
                if (!update && SampleRender) sampledDraws++;
                long start = meter.Start(); try { orig(self, time); } finally {
                    meter.Stop(start);
                    if (update) SampleUpdate = false; else SampleRender = false;
                }
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
            meters = meters.Select(m => m.Snapshot()).ToArray(),
            entitySamples = entityMeters.Values.Where(m => m.HasSamples).Select(m => m.Snapshot()).ToArray(),
            sampledUpdates, sampledDraws,
            dropped = Interlocked.Read(ref dropped) });
        sampledUpdates = sampledDraws = 0;
        contextStart = context; windowStart = now; nextWindow = now + Stopwatch.Frequency * 10;
        DumpChains();
    }
    private void Emit(object record) {
        if (stopped || writer == null) return;
        try { if (!output.TryAdd(record)) Interlocked.Increment(ref dropped); }
        catch (InvalidOperationException) { /* teardown raced with a loader hook */ }
    }
    private void WriteRecords() {
        int index = 0;
        try {
            while (!output.IsCompleted) {
                if (!output.TryTake(out object? first, 1000)) continue;
                var batch = new List<object> { first };
                long deadline = Stopwatch.GetTimestamp() + Stopwatch.Frequency * 2;
                while (batch.Count < 64 && !output.IsCompleted && Stopwatch.GetTimestamp() < deadline) {
                    if (output.TryTake(out object? more, 100)) batch.Add(more);
                }
                // Batch startup records, then close the completed JSON array.
                string path = Path.Combine(directory, (index++).ToString("D6") + ".json");
                File.WriteAllText(path, JsonSerializer.Serialize(batch));
            }
        } catch (Exception e) {
            Interlocked.Increment(ref dropped);
            Logger.Log("SwitchPerformance", "Profile writer stopped: " + e.Message);
        }
    }
    public override void Unload() {
        checksumBufferHook?.Dispose();
        foreach (var hook in entityHooks) hook.Dispose();
        entityHooks.Clear();
        foreach (Hook hook in Enumerable.Reverse(hooks)) hook.Dispose();
        hooks.Clear();
        if (!stopped) {
            Emit(new { kind = "stop", utc = DateTime.UtcNow, dropped = Interlocked.Read(ref dropped) });
            stopped = true; output.CompleteAdding(); writer?.Join(2000);
        }
    }
}
