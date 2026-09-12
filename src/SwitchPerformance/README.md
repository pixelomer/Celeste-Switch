# SwitchPerformance

A removable diagnostic mod for the .NET 10 host. Its wrappers call the next
hook/original once with the original arguments; timing is recorded in finally
blocks. Checksum buffering is enabled by default for new mod settings; it is removable. Disable the diagnostic ZIP through
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
references Private=false, including MonoMod.Utils and Mono.Cecil for IL hooks. It packages only SwitchPerformance.dll and everest.yaml
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

## Startup modes

Diagnostics defaults false and is read at startup. With it disabled, Load installs
only the scoped checksum hooks: no frame/sampling hooks, profile writer or profile
files. BufferChecksums is a separate true-by-default setting for new settings;
existing saved values remain under the user's control. Diagnostics does not
select that value. Detailed sampling requires Diagnostics.

Settings use Everest's ordinary mod options and
Saves/modsettings-SwitchPerformance.celeste. Change startup settings while the
game is closed, or save them through the normal menu and restart.

Without Diagnostics there are no structured profile records. The checksum IL
installer now separately logs success with the BufferChecksums setting or failure
with the exception through Everest's normal Logger.Log. The startup message
reports only that frame/file diagnostics are disabled, not that installation
succeeded. Logger.Log uses Verbose level in the selected Everest source, so the
configured tag threshold can hide these messages; absence is not proof of success.

## Records and interpretation

The following records are produced only when Diagnostics is enabled.

Records are closed JSON arrays in performance/RUN/ under the game directory.
The writer batches up to 64 records or a two-second deadline, with timed queue
polling, before closing a file. The summarizer accepts arrays and earlier
individual-object records.
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

## Sparse entity sampling

One in 120 Engine update/draw calls samples the existing EntityList virtual
Update/Render call site. Other calls retain the original virtual call after a
conditional branch. Sampling still invokes the entity method once, preserving
its hook chain; it does not skip entity work. Missing or ambiguous IL patterns
produce a failed-hook record instead of a guessed insertion.

Samples group inclusive cost by concrete entity type. Parent/child calls can
overlap, and observer/JIT costs require separate consideration. The profiler
also measures gameplay, lighting and backdrop renderer stages. Unload disposes
the sampling IL hooks as well as the ordinary timing hooks.

## Summarize one run

Copy a complete run's JSON records to an ignored directory, preserving the
originals, then use the standard-library-only metadata reader:

```sh
python3 scripts/summarize-performance.py artifacts/performance-records
```

The input must contain exactly one start record. The tool groups windows whose
start/end context labels match, aggregates inclusive meters and histogram
percentile bounds, and lists individual checksum/archive durations. It reports
hook/snapshot failures and the maximum dropped count; it does not automatically
reject every incomplete or transitional run. Output goes to stdout. Keep any
redirected summary outside Git and preserve an existing file before redirection.

The summary also accumulates collector/allocation deltas only where the prior
window index exists and its end timestamp equals the current start. It reports
the covered duration; a missing predecessor is not treated as a zero baseline.
Collector pause ticks use TimeSpan units, separately from Stopwatch durations.
Entity costs are normalized by the recorded sampled update or draw count, not
by all frames; absent sampled frames yield a null per-frame estimate.

## Scoped checksum buffering

BufferChecksums defaults true for new settings. A guarded IL hook requests 128 KiB instead of
4 KiB from HashAlgorithm.ComputeHash(Stream)'s ArrayPool only for exact
FileStream objects and Everest's XXHash64, synchronously inside GetChecksum(path).
Other stream types, algorithms and unrelated calls retain the original request.
The hook requires exactly one matching rent-size instruction sequence; failures
are reported explicitly. Unload disposes it. The original checksum call and
stream, complete file bytes, algorithm and cache semantics remain in place.
Actual read lengths still depend on the pooled buffer and stream.

Read/HashCore chunk boundaries are observable to other hooks. Do not infer
compatibility with every mod or arbitrary short-read pattern from an equivalent
digest on one file. The source algorithm's nonstandard short-input result must
remain unchanged. The [checksum fixture](../../tests/performance-checksum/README.md)
checks aligned chunk-boundary behavior without loading the game.

DetailedEntities defaults true and is read when installing entity sampling;
false omits those IL hooks. Sampling flags are thread-local. Coarse timing also
includes SpriteBatch.FlushBatch. On entering a Level, the profiler records the
existing detour/IL-hook chains for selected entity and movement methods once;
that inspection does not replace or disable those hooks.

Use --first-window and --last-window for inclusive scene-window index bounds.
Only scene aggregation is bounded: failure and loading records
still cover the full supplied run. A collector delta can use the immediately
preceding record outside the selected bounds if its timestamps are contiguous.
Choose bounds from the actual run; the tool does not determine stable workload
conditions or validate the ordering of the two requested bounds.

## Sprite-batch diagnostic stages

With Diagnostics enabled, the profiler adds PrepRenderState, UpdateVertexBuffer
and DrawPrimitives timers to the existing FlushBatch meter. The wrappers forward
the same texture, start and count arguments and retain the upload method's return
value. These private FNA hook signatures correspond to the paired source-built
FNA input, not arbitrary future framework versions.

The timers distinguish state setup, vertex upload and texture-run submission,
but remain inclusive method durations with observer overhead. They do not
measure isolated GPU execution, change sorting/batching, skip simulation updates
or prune other mods' hooks. Preserve sprite order, texture lifetime and effect
semantics when assessing any future rendering change.

## Checksum-only configuration and rollback

For checksum buffering without frame instrumentation, an explicit example is:

```yaml
Diagnostics: false
DetailedEntities: false
BufferChecksums: true
```

DetailedEntities defaults true in source but is inactive while Diagnostics is
false. The example is not a compatibility certification. The root build includes
this ordinary mod unless --without-performance-mod is selected; it does not
rewrite existing user settings. Keep the original mod profile and saves intact.
Disabling BufferChecksums restores the original requested read size. Disabling
the diagnostic ZIP while the game is closed removes its hooks on the next launch.
Neither action requires clearing relink/audio caches or restoring saves.
Preserve the selected ZIP/settings when comparing behavior.

To diagnose installation messages, set Everest's SwitchPerformance log-tag
threshold to Verbose through its normal logging configuration. Keep detailed
per-submission timers disabled outside deliberate measurement. Additional maps,
mod/helper features, relink and audio-cache states need separate assessment;
checksum behavior alone does not establish a frame-rate improvement.
