using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using Celeste.Mod;
using Celeste.Mod.Core;
using Monocle;
using MonoMod.RuntimeDetour;

static class Program {
    const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
    static int checks, decisions, notifications, reloads;
    static bool force;
    static bool Decide(VirtualTexture texture) { decisions++; return force; }
    static void Notify(VirtualTexture texture) { notifications++; }
    static void FakeReload(VirtualTexture texture) { reloads++; }
    static string ContentDirectory() => "/tmp";
    static void Check(bool value, string label) {
        if (!value) throw new Exception(label);
        checks++;
        Console.WriteLine("PASS " + label);
    }
    static void Main(string[] args) {
        string directory = Path.GetFullPath(args[0]);
        AssemblyLoadContext.Default.Resolving += (_, name) => {
            string path = Path.Combine(directory, name.Name + ".dll");
            return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
        };
        Run();
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run() {
        // Do not construct Engine, start the game or create a graphics device.
        CoreModule.Instance = (CoreModule)RuntimeHelpers.GetUninitializedObject(typeof(CoreModule));
        CoreModule.Instance._Settings = new CoreModuleSettings();
        using var contentPath = new Hook(typeof(Engine).GetProperty("ContentDirectory").GetMethod,
            (Func<string>)ContentDirectory);
        var texture = (VirtualTexture)RuntimeHelpers.GetUninitializedObject(typeof(VirtualTexture));
        using (var file = new BinaryWriter(File.Create("/tmp/lazy-probe.data"))) {
            file.Write(17); file.Write(23);
        }
        typeof(VirtualTexture).GetProperty("Path").SetValue(texture, "/tmp/lazy-probe.data");
        MethodInfo preload = typeof(VirtualTexture).GetMethod("Preload", Private);
        bool Preload(bool forced = false) => (bool)preload.Invoke(texture, new object[] { forced });
        CoreModule.Settings.LazyLoading = false;
        Check(!Preload(), "no subscriber preserves eager loading");
        Everest.Events.VirtualTexture.ShouldForceLazyLoad += Decide;
        Everest.Events.VirtualTexture.OnLazyLoad += Notify;
        force = true;
        Check(Preload() && texture.Width == 17 && texture.Height == 23,
            "mod can defer allocation and preload dimensions");
        int before = decisions;
        Check(Preload(true) && decisions == before, "forced size read preserves mod decision");
        using var hook = new Hook(typeof(VirtualTexture).GetMethod("Reload", Private),
            (Action<VirtualTexture>)FakeReload);
        _ = texture.Texture_Safe;
        Check(reloads == 1 && notifications == 1, "mod deferred texture access reloads and notifies");
        // An explicit Reload is a mod's preload, not a late access notification.
        typeof(VirtualTexture).GetMethod("Reload", Private).Invoke(texture, null);
        Check(reloads == 2 && notifications == 1, "explicit reload does not report a lazy access");
        force = false;
        CoreModule.Settings.LazyLoading = true;
        before = decisions;
        Check(Preload() && decisions == before + 1,
            "global lazy setting survives a false subscriber and still invokes it");
        _ = texture.Texture_Safe;
        Check(reloads == 3 && notifications == 2, "global deferred access reloads and notifies");
        CoreModule.Settings.LazyLoading = false;
        Check(!Preload(), "false subscriber preserves eager loading when global is off");
        _ = texture.Texture_Safe;
        Check(reloads == 3 && notifications == 2, "eager texture access adds no lazy reload");
        Everest.Events.VirtualTexture.ShouldForceLazyLoad -= Decide;
        Everest.Events.VirtualTexture.OnLazyLoad -= Notify;
        Check(!Preload(), "unsubscribing restores original eager policy");
        Console.WriteLine($"PASS {checks} assertions; no game entry or GPU calls");
    }
}
