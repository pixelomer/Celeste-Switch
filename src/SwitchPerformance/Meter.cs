using System.Diagnostics;

namespace SwitchPerformance;

// Counters are safe for loader-thread hooks too. No per-call allocation or I/O.
internal sealed class Meter(string name) {
    private long count, ticks, maximum;
    private readonly long[] histogram = new long[128];
    internal bool HasSamples => Volatile.Read(ref count) != 0;
    internal long Start() => Stopwatch.GetTimestamp();
    internal void Stop(long start) {
        long elapsed = Stopwatch.GetTimestamp() - start;
        Interlocked.Increment(ref count);
        Interlocked.Add(ref ticks, elapsed);
        long old = Volatile.Read(ref maximum);
        while (elapsed > old) {
            long found = Interlocked.CompareExchange(ref maximum, elapsed, old);
            if (found == old) break;
            old = found;
        }
        // Quarter-millisecond bins, final bin includes all values >=31.75ms.
        int bin = (int)Math.Min(127, elapsed * 4000 / Stopwatch.Frequency);
        Interlocked.Increment(ref histogram[bin]);
    }
    internal object Snapshot() {
        var bins = new long[histogram.Length];
        for (int i = 0; i < bins.Length; ++i) bins[i] = Interlocked.Exchange(ref histogram[i], 0);
        return new {
            name, count = Interlocked.Exchange(ref count, 0),
            ticks = Interlocked.Exchange(ref ticks, 0),
            maximumTicks = Interlocked.Exchange(ref maximum, 0), histogram = bins
        };
    }
}
