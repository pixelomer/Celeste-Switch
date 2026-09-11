using System;
using System.Runtime.CompilerServices;

public static class OwnedHookFixture
{
    // A mod-like handler: the mod assembly owns the callback, while the host
    // owns the method being hooked. No MonoMod dependency is needed here.
    public static int WrapCompute(Func<int, int> original, int value) => original(value) + 100;

    [MethodImpl(MethodImplOptions.NoInlining)]
    public static int Compute(int value)
    {
        if (value < 0) throw new ArgumentOutOfRangeException(nameof(value));
        return value + 7;
    }
}
