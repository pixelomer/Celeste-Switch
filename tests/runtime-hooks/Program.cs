using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using Mono.Cecil.Cil;
using MonoMod.Cil;
using MonoMod.RuntimeDetour;

internal static class Program
{
    private static void Equal(int expected, int actual)
    {
        if (expected != actual) throw new InvalidOperationException($"Expected {expected}; got {actual}");
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference Run(string path)
    {
        var context = new AssemblyLoadContext(path, isCollectible: true);
        var assembly = context.LoadFromAssemblyPath(path);
        var method = assembly.GetType("OwnedHookFixture")!.GetMethod("Compute")!;
        var compute = (Func<int, int>)method.CreateDelegate(typeof(Func<int, int>));
        Console.WriteLine($"LOAD {assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName}");
        Equal(13, compute(6));
        if (Environment.GetEnvironmentVariable("CELESTE_HOOK_CONTROL") != "load-only")
        {
        using (var first = new Hook(method, (Func<Func<int, int>, int, int>)((original, value) => original(value) + 100)))
        {
            Equal(113, compute(6));
            using (var second = new Hook(method, (Func<Func<int, int>, int, int>)((original, value) => original(value) + 1000)))
                Equal(1113, compute(6));
            Equal(113, compute(6));
        }
        Equal(13, compute(6));
        using (var hook = new ILHook(method, il => {
            var cursor = new ILCursor(il);
            if (!cursor.TryGotoNext(instruction => instruction.MatchLdcI4(7)))
                throw new InvalidOperationException("Owned fixture constant not found");
            cursor.Remove(); cursor.Emit(OpCodes.Ldc_I4, 11);
        }))
        {
            for (int i = 0; i < 32; ++i)
            {
                Equal(17, compute(6));
                GC.Collect(2, GCCollectionMode.Forced, blocking: true, compacting: true);
            }
            try { compute(-1); throw new InvalidOperationException("Exception was lost"); }
            catch (ArgumentOutOfRangeException) { }
        }
        Equal(13, compute(6));
        Console.WriteLine("PASS Hook chain/original/disposal, ILHook/GC/exception/restoration");
        }
        var weak = new WeakReference(context);
        context.Unload();
        return weak;
    }

    public static int Main(string[] args)
    {
        try {
            Console.WriteLine($"HOST {System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription}");
            bool failed = false;
            foreach (string path in args)
            {
                var weak = Run(System.IO.Path.GetFullPath(path));
                for (int i = 0; weak.IsAlive && i < 20; ++i) {
                    GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();
                    System.Threading.Thread.Sleep(25);
                }
                if (weak.IsAlive) {
                    Console.Error.WriteLine("FAIL collectible fixture remained rooted after unload"); failed = true;
                } else Console.WriteLine("PASS collectible unload");
            }
            Console.WriteLine(failed ? "END FAIL" : "END PASS");
            if (Environment.GetEnvironmentVariable("CELESTE_HOOK_WAIT") == "1") {
                Console.WriteLine($"DUMP_PID {Environment.ProcessId}");
                System.Threading.Thread.Sleep(TimeSpan.FromMinutes(5));
            }
            return failed ? 1 : 0;
        } catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
