using System;
using System.Runtime.CompilerServices;

public static class OwnedHookFixture
{
    [MethodImpl(MethodImplOptions.NoInlining)]
    public static int Compute(int value)
    {
        if (value < 0) throw new ArgumentOutOfRangeException(nameof(value));
        return value + 7;
    }
}
