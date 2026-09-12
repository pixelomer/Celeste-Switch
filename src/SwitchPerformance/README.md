# SwitchPerformance

A removable diagnostic mod for the .NET 10 host. Its wrappers call the next
hook/original once with the original arguments; timing is recorded in finally
blocks. This version has no optimization. Disable the diagnostic ZIP through
ordinary mod configuration to remove its measurements.

## Build from paired inputs

Use .NET SDK 10.0.111 and the source-built Everest preparation documented by
the [lazy-loading fixture](../../tests/lazy-loading/README.md#prepare-matching-assemblies).
Only its source/installer preparation is required, not fixture execution.
The pinned Everest and recursive MonoMod sources, source-built FNA and supported
user-owned PC distribution produce artifacts/lazy-everest-prepared/install.
Keep the complete prepared assembly set together; do not supply an unexplained
or differently patched game assembly.

From this repository root, with a new output directory:

```sh
python3 scripts/build-performance-mod.py \
  --install artifacts/lazy-everest-prepared/install \
  --output artifacts/performance-mod
```

The helper invokes dotnet build with an absolute PreparedInstall and isolated
artifacts path. The project targets net10.0 and marks its game/framework/hook
references Private=false. It packages only SwitchPerformance.dll and everest.yaml
as artifacts/performance-mod/deploy/000-SwitchPerformance.zip, with fixed ZIP
entry timestamps. Its generated package.json records input/source/output
identities for local inspection; neither that file nor its binaries belong in Git.
No game or mod is run, installed or deployed by this build command.

The leading filename sorts before other ordinary code-mod ZIPs; this is not a
claim that every loader task happens after initialization. Install through the
normal Mods directory when choosing to use the profiler. Its manifest requires
Everest 1.0.0; the selected 0.0.0 development loader has a version-check exception.
Do not redistribute the proprietary game or referenced loader assemblies with
the diagnostic package.

## Records and interpretation

Records are closed JSON objects in performance/RUN/ under the game directory.
A background writer consumes a bounded queue; enqueue failure increments the
dropped counter instead of waiting for capacity. Logging, snapshots and hooks
still have overhead. Hook failures, snapshot failures and dropped records are
explicit. The writer closes each record file and stops on a write error.

Windows cover approximately ten seconds. Parent/child timing is inclusive and
overlapping. Loader-thread counters can race with a reset; a snapshot is not
one atomic cross-counter transaction. Use individual checksum/load records for
startup and treat aggregate windows as approximate. First and boundary-mismatched
contexts are transitional; matching labels alone cannot exclude intervening changes.

FrameInterval includes frame pacing, collector and observer work.
Game.EndDraw includes presentation waits, not isolated GPU execution.
Histograms have 128 quarter-millisecond bins with overflow at 31.75 ms.
Count, total and maximum are recorded separately; do not infer sub-bin precision
or an exact percentile from the histogram. See the
[measurement method](../../docs/PERFORMANCE_INVESTIGATION.md) for comparison scope.
