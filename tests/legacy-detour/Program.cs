using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;

// Original fixture: exercise Everest's actual adapter without running the game.
static class Program {
    [MethodImpl(MethodImplOptions.NoInlining)]
    public static int Source(int value) => value + 3;
    [MethodImpl(MethodImplOptions.NoInlining)]
    public static int Target(int value) => value + 100;
    static void Check(bool value, string label) {
        if (!value) throw new Exception(label);
        Console.WriteLine("PASS " + label);
    }
    static void Main(string[] args) {
        string directory = Path.GetFullPath(args[0]);
        AssemblyLoadContext.Default.Resolving += (_, name) => {
            string path = Path.Combine(directory, name.Name + ".dll");
            return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
        };
        Assembly game = AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(directory, "Celeste.dll"));
        Type adapter = game.GetType("Celeste.Mod.Helpers.LegacyMonoMod.LegacyDetour", throwOnError: true)!;
        MethodInfo source = typeof(Program).GetMethod(nameof(Source))!;
        MethodInfo target = typeof(Program).GetMethod(nameof(Target))!;
        Check(Source(4) == 7, "original before detour");
        using (var detour = (IDisposable)Activator.CreateInstance(adapter, new object[] { source, target })!) {
            Check(Source(4) == 104, "legacy detour redirects original fixture");
            MethodInfo factory = adapter.GetMethods().Single(m => m.Name == "GenerateTrampoline" && m.IsGenericMethodDefinition);
            var original = (Func<int, int>)factory.MakeGenericMethod(typeof(Func<int, int>)).Invoke(detour, null)!;
            Check(original(4) == 7, "legacy trampoline calls original");
            adapter.GetMethod("Undo")!.Invoke(detour, null);
            Check(Source(4) == 7, "undo restores fixture");
            adapter.GetMethod("Apply")!.Invoke(detour, null);
            Check(Source(4) == 104 && original(4) == 7, "reapply preserves original delegate");
        }
        Check(Source(4) == 7, "dispose restores fixture");
    }
}
