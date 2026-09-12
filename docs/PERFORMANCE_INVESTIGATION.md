# Performance measurement method

Use the removable [SwitchPerformance mod](../src/SwitchPerformance/README.md)
to distinguish application update, draw, presentation, loading and collector
costs. It observes the existing game and mod hook chains; it does not patch
third-party mod archives or replace their implementations.

Keep the original mod profile, saves and settings intact. Compare equivalent
scene, camera, player and pause states after settling, and assess movement
separately from a stationary window. Startup, first-use texture/JIT work, cold
relinking, warm relinking and cached audio are different workloads.

Record the selected source inputs and generated identities outside Git when
comparing runs. Hold the runtime options, input set and operating conditions
constant. Explicit minopts or tracing flags are only specific configuration
checks, not proof that all compiler/runtime overhead is absent.

The coarse meters cover engine and level update/render, entity-list update,
presentation, frame intervals, texture reload, archive loading and full-file
checksum calls. Window records also include scene/room/pause context, collector
counts, heap/allocation totals and pause duration. Consult hook-failure,
snapshot-failure and dropped-record fields before interpreting a run.

Parent and child meters overlap: do not sum their inclusive times. Frame
intervals include pacing and observer work; presentation waits are not GPU
execution time. A matching context label at the two window boundaries does
not prove that the scene remained unchanged throughout the interval.
Exclude transitions explicitly and measure instrumentation overhead against
the same host and inputs with the diagnostic ZIP disabled.

Full-file checksum I/O, log volume, entity work, deferred texture loading and
allocation/collection are measurable categories, not established bottlenecks.
Do not skip integrity checks or introduce stale-cache behavior to improve a
measurement. Any later optimization must preserve arguments, results, exception
behavior, ordering and the existing mod hooks, and be assessed independently
with detailed instrumentation disabled.

Successful compilation or a summary file does not establish compatibility or
a speedup. Assess ordinary mod loading, actual affected scenes and save/reload
separately. Generated records and observations remain outside source history.
