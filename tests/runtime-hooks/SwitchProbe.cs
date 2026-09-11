#nullable enable
using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using Mono.Cecil.Cil;
using MonoMod.Cil;
using MonoMod.Core.Platforms;
using MonoMod.RuntimeDetour;
using MonoMod.Utils;

// Original fixture, no game code or assets. A first integration gate only;
// ordinary mod discovery, collectible assemblies and concurrent patching are
// separate tests. This process does not call a method concurrently with patching.
internal static unsafe class SwitchProbe
{
    [DllImport("__Internal", EntryPoint = "ProbeInvokeCallback")]
    private static extern int InvokeCallback(IntPtr callback, int value);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate int Callback(int value);
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_get_jit")]
    private static extern IntPtr GetJit();
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_jit_get_compile_callback")]
    private static extern IntPtr GetCompileCallback();
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_jit_set_compile_callback")]
    private static extern int SetCompileCallback(IntPtr expected, IntPtr callback);
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_memory_granularity")]
    private static extern nuint Granularity();
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_memory_allocate")]
    private static extern int Allocate(nuint size, int executable, IntPtr low, IntPtr high, IntPtr* handle, IntPtr* address);
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_memory_free")]
    private static extern void Free(IntPtr handle);
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_memory_readable")]
    private static extern nuint Readable(IntPtr address, nuint size);
    [DllImport("__Internal", EntryPoint = "coreclr_libnx_memory_patch")]
    private static extern int Patch(IntPtr address, void* data, void* backup, nuint size);

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
        Console.WriteLine("PASS " + message);
    }

    private static void Memory()
    {
        nuint size = Granularity();
        Require(size >= 4096 && (size & (size - 1)) == 0, "host allocation granularity");
        IntPtr handle, address;
        Require(Allocate(0, 1, IntPtr.Zero, IntPtr.Zero, &handle, &address) == 0 && handle == IntPtr.Zero && address == IntPtr.Zero, "reject empty allocation");
        Require(Readable((IntPtr)1, 16) == 0, "unmapped read rejected");
        uint* code = stackalloc uint[] { 0x52800540, 0xd65f03c0 }; // mov w0,#42; ret
        Require(Patch((IntPtr)1, code, null, 8) == 0, "unmapped patch rejected");
        Require(Allocate(size, 1, IntPtr.Zero, IntPtr.Zero, &handle, &address) == 1, "allocate runtime code");
        try
        {
            Require(Readable(address, size) == size, "allocated RX readable");
            Require(Patch(address, code, null, 8) == 1, "publish through RW alias");
            var function = (delegate* unmanaged[Cdecl]<int>)(void*)address;
            Require(function() == 42, "execute published code");
            uint* backup = stackalloc uint[2];
            code[0] = 0x52800a80; // mov w0,#84
            Require(Patch(address, code, backup, 8) == 1 && backup[0] == 0x52800540, "patch and backup RX");
            Require(function() == 84, "execute republished code");
            Require(Patch(address, backup, null, 8) == 1 && function() == 42, "restore executable code");
        }
        finally { Free(handle); }
        Require(Readable(address, size) == 0, "released code unreadable");
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int Compute(int value)
    {
        if (value < 0) throw new ArgumentOutOfRangeException(nameof(value));
        return value + 7;
    }

    private static int finalized, finalizerValue;
    private sealed class FinalizerFixture
    {
        ~FinalizerFixture()
        {
            finalizerValue = Compute(6);
            Interlocked.Increment(ref finalized);
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static void QueueFinalizer() { _ = new FinalizerFixture(); }

    private static void WorkerAndFinalizerChecks()
    {
        Exception? failure = null;
        var worker = new Thread(() => {
            try
            {
                RuntimeHelpers.EnsureSufficientExecutionStack();
                var method = new System.Reflection.Emit.DynamicMethod("WorkerGenerated", typeof(int), Type.EmptyTypes);
                var il = method.GetILGenerator();
                il.Emit(System.Reflection.Emit.OpCodes.Ldc_I4, 37);
                il.Emit(System.Reflection.Emit.OpCodes.Ret);
                if (method.CreateDelegate<Func<int>>()() != 37 || Compute(6) != 113)
                    throw new Exception("Worker JIT/hook mismatch");
            }
            catch (Exception error) { failure = error; }
        });
        worker.Start();
        Require(worker.Join(10000), "default-stack worker completed");
        if (failure is not null) throw new Exception("Worker failed", failure);
        Require(true, "worker JIT and Hook with sufficient stack");
        QueueFinalizer();
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        GC.WaitForPendingFinalizers();
        Require(Volatile.Read(ref finalized) == 1 && finalizerValue == 113, "finalizer JIT and active Hook");
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int CallbackWork(int value) => value + 11;

    [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
    private static int UnmanagedEntry(int value)
    {
        int total = 0;
        for (int i = 0; i < value; ++i) total += CallbackWork(i);
        return total;
    }

    private static void ReverseTransitionChecks()
    {
        // Exercise plain reverse P/Invoke before MonoMod installs any hooks.
        // An entry poll before REVERSE_PINVOKE_ENTER executes in the wrong GC
        // mode; both callback shapes must tolerate a concurrent collector.
        Callback callback = value => CallbackWork(value);
        IntPtr thunk = Marshal.GetFunctionPointerForDelegate(callback);
        IntPtr unmanaged = (IntPtr)(delegate* unmanaged[Cdecl]<int, int>)&UnmanagedEntry;
        int completed = 0;
        var collector = new Thread(() => {
            for (int i = 0; i < 64; ++i)
            {
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                Thread.Sleep(1);
            }
            Volatile.Write(ref completed, 1);
        });
        collector.Start();
        int calls = 0;
        do
        {
            if (InvokeCallback(thunk, 6) != 17 || InvokeCallback(unmanaged, 64) != 2720)
                throw new Exception("Reverse callback result mismatch");
            ++calls;
        } while (calls < 4096 || Volatile.Read(ref completed) == 0);
        Require(collector.Join(10000), "reverse callback collector completed");
        GC.KeepAlive(callback);
        Require(true, "delegate and UnmanagedCallersOnly callbacks under 64 compacting GCs");
    }

    public static int Main(string[] args)
    {
        try
        {
            Console.WriteLine("BEGIN Horizon MonoMod host " + RuntimeInformation.FrameworkDescription);
            // Log each deployed assembly's length and deterministic checksum.
            // The verifier compares every line against local build inputs;
            // this is an integrity comparison, not third-party authentication.
            foreach (var file in System.IO.Directory.GetFiles("/switch/celeste-hook-probe", "*.dll"))
            {
                ulong hash = 14695981039346656037UL;
                long length = 0;
                using var stream = System.IO.File.OpenRead(file);
                byte[] buffer = new byte[32768];
                int count;
                while ((count = stream.Read(buffer, 0, buffer.Length)) != 0)
                {
                    length += count;
                    for (int i = 0; i < count; ++i) hash = unchecked((hash ^ buffer[i]) * 1099511628211UL);
                }
                Console.WriteLine($"INPUT {System.IO.Path.GetFileName(file)} {length} {hash:x16}");
            }
            ReverseTransitionChecks();
            Memory();
            var compile = GetCompileCallback();
            Require(compile != IntPtr.Zero, "embedded compiler available");
            Require(SetCompileCallback(compile, compile) == 1, "callback compare-exchange accepts current owner");
            Require(SetCompileCallback((IntPtr)1, compile) == 0 && GetCompileCallback() == compile, "callback rejects stale owner");
            Require(SetCompileCallback(compile, IntPtr.Zero) == 0 && GetCompileCallback() == compile, "callback rejects null replacement");
            var vtable = *(IntPtr**)GetJit();
            var originalSlot = *vtable;
            Require(Patch((IntPtr)vtable, &originalSlot, null, (nuint)sizeof(IntPtr)) == 0 && *vtable == originalSlot, "JIT RELRO remains protected");
            Console.WriteLine("STAGE initialize platform/JIT hook");
            var triple = PlatformTriple.Current;
            Require(triple.System.Target == OSKind.Libnx && triple.Architecture.Target == ArchitectureKind.Arm64, "Horizon ARM64 selected");
            Require(Compute(6) == 13, "original method");
            var method = typeof(SwitchProbe).GetMethod("Compute", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!;
            using (var first = new Hook(method, (Func<Func<int, int>, int, int>)((original, value) => original(value) + 100)))
            {
                Require(Compute(6) == 113, "Hook original call");
                using (var second = new Hook(method, (Func<Func<int, int>, int, int>)((original, value) => original(value) + 1000)))
                    Require(Compute(6) == 1113, "Hook chain");
                Require(Compute(6) == 113, "remove nested Hook");
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                Require(Compute(6) == 113, "Hook survives compacting GC");
                WorkerAndFinalizerChecks();
            }
            Require(Compute(6) == 13, "Hook restored");
            using (var hook = new ILHook(method, il => {
                var cursor = new ILCursor(il);
                if (!cursor.TryGotoNext(instruction => instruction.MatchLdcI4(7))) throw new Exception("Fixture IL not found");
                cursor.Remove(); cursor.Emit(OpCodes.Ldc_I4, 11);
            }))
            {
                Require(Compute(6) == 17, "ILHook");
                for (int i = 0; i < 16; ++i)
                {
                    GC.Collect(2, GCCollectionMode.Forced, true, true);
                    if (Compute(6) != 17) throw new Exception("ILHook lost across GC");
                }
                Require(true, "ILHook survives compacting GC");
                bool caught = false;
                try { Compute(-1); } catch (ArgumentOutOfRangeException) { caught = true; }
                Require(caught, "ILHook managed exception");
            }
            Require(Compute(6) == 13, "ILHook restored");
            GC.Collect(2, GCCollectionMode.Forced, true, true);
            GC.WaitForPendingFinalizers();
            Require(true, "pending finalizers drained after hook disposal");
            Console.WriteLine("END PASS Horizon hook gate");
            return 100;
        }
        catch (Exception error) { Console.WriteLine("END FAIL " + error); return 101; }
    }
}
