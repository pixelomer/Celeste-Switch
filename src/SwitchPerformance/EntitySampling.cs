using System.Reflection;
using Celeste;
using Monocle;
using Mono.Cecil.Cil;
using MonoMod.Cil;
using MonoMod.RuntimeDetour;

namespace SwitchPerformance;

public sealed partial class PerformanceModule {
    // Only one in 120 update/draw calls measures individual entities. Other
    // frames execute the existing call instruction, with one conditional branch.
    [ThreadStatic] public static bool SampleUpdate;
    [ThreadStatic] public static bool SampleRender;
    private long updateNumber, drawNumber;
    private int sampledUpdates, sampledDraws;
    private readonly List<ILHook> entityHooks = new();
    private readonly Dictionary<(string, Type), Meter> entityMeters = new();
    private bool chainsDumped;

    private void DumpChains() {
        if (chainsDumped || Engine.Scene is not Level) return;
        chainsDumped = true;
        foreach (Type type in new[] { typeof(Player), typeof(Solid), typeof(SolidTiles), typeof(Entity), typeof(ComponentList), typeof(Platform) }) {
            foreach (MethodInfo method in type.GetMethods(Methods).Where(m => m.DeclaringType == type &&
                (m.Name == "Update" || m.Name == "MoveH" || m.Name == "MoveV"))) {
                try {
                    var info = DetourManager.GetDetourInfo(method);
                    Emit(new { kind = "hookChain", method = type.FullName + "." + method,
                        detours = info.Detours.Select(d => d.Entry.DeclaringType?.FullName + "." + d.Entry.Name).ToArray(),
                        il = info.ILHooks.Select(d => d.ManipulatorMethod.DeclaringType?.FullName + "." + d.ManipulatorMethod.Name).ToArray() });
                } catch (Exception e) { Emit(new { kind = "hookChainFailure", method = method.ToString(), error = e.Message }); }
            }
        }
    }

    private void InstallEntitySampling() {
        foreach (string method in new[] { "Update", "Render", "RenderOnly", "RenderOnlyFullMatch", "RenderExcept" }) {
            string called = method == "Update" ? "Update" : "Render";
            try {
                MethodInfo target = typeof(EntityList).GetMethod(method, Methods)!;
                var hook = new ILHook(target, il => {
                    var cursor = new ILCursor(il);
                    if (!cursor.TryGotoNext(MoveType.Before, i => i.MatchCallvirt<Entity>(called)))
                        throw new InvalidOperationException("Expected Entity." + called + " call missing");
                    var original = cursor.DefineLabel();
                    var after = cursor.DefineLabel();
                    cursor.Emit(OpCodes.Ldsfld, typeof(PerformanceModule).GetField(
                        called == "Update" ? nameof(SampleUpdate) : nameof(SampleRender))!);
                    cursor.Emit(OpCodes.Brfalse, original);
                    cursor.EmitDelegate<Action<Entity>>(entity => SampleEntity(entity, called));
                    cursor.Emit(OpCodes.Br, after);
                    cursor.MarkLabel(original);
                    cursor.Index++;
                    cursor.MarkLabel(after);
                    if (cursor.TryGotoNext(i => i.MatchCallvirt<Entity>(called)))
                        throw new InvalidOperationException("Multiple entity calls; refuse ambiguous sampling");
                });
                entityHooks.Add(hook);
                Emit(new { kind = "hook", label = "sample EntityList." + method, success = true });
            } catch (Exception e) {
                Emit(new { kind = "hook", label = "sample EntityList." + method, success = false, error = e.ToString() });
            }
        }
    }

    private void SampleEntity(Entity entity, string phase) {
        var key = (phase, entity.GetType());
        if (!entityMeters.TryGetValue(key, out Meter? meter)) {
            meter = new Meter(phase + ":" + key.Item2.FullName);
            entityMeters.Add(key, meter);
        }
        long start = meter.Start();
        try {
            // Retain virtual dispatch and all hooks on the entity method.
            if (phase == "Update") entity.Update(); else entity.Render();
        } finally { meter.Stop(start); }
    }

    private void TimedScene<T>(string method) {
        string label = typeof(T).Name + "." + method;
        var meter = NewMeter(label);
        Add(typeof(T).GetMethod(method, Methods, null, new[] { typeof(Scene) }, null),
            (Action<Action<T, Scene>, T, Scene>)((orig, self, scene) => {
                long start = meter.Start(); try { orig(self, scene); } finally { meter.Stop(start); }
            }), label);
    }
}
