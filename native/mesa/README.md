# Mesa allocation failure handling and diagnostics

nouveau-mm-failure.patch applies to the Nouveau allocator in the pinned
Mesa 20.1.0-rc3 source. It propagates slab-creation failure before treating a
free-list head as a slab, allocates bookkeeping before consuming a slot, and
rejects a negative slot before shifting it into an offset. Preserve the
upstream Mesa source notices when building copied sources.

## Build from paired public sources

Use the [graphics source recipe](../../tests/fna-graphics/README.md) to obtain
the checksum-pinned Mesa/package sources and produce a complete archive and
compile database. The [buffer diagnostic builder](../../tests/graphics-buffer-diagnostics/README.md)
accepts --fix-allocator to apply this patch to a copied nouveau_mm.c and replace
its archive member. It requires exact source matches and uses --fuzz=0.

By default that builder retains the upload-destination diagnostic. Add
--allocator-only together with --fix-allocator to keep only the allocator
correction, without replacing the upload member or adding the slab-failure log.
The host's NV wrappers remain a separate optional selection. See the buffer
builder guide for manifest fields that distinguish compiled instrumentation.
Original source, objects and archive remain unchanged. Select the new archive
through the host's --mesa-library argument only after keeping the original
manifest-checked graphics inputs available.

## Paired allocator controls

The [original allocator fixture](../../tests/graphics-buffer-diagnostics/allocator-test.c)
compiles the real Nouveau allocator with controlled BO creation/reference
functions. It does not create GPU workloads or load game code. Build separate
original and fixed variants from this repository root:

```sh
python3 tests/graphics-buffer-diagnostics/build-allocator-test.py \
  --mesa-build third_party/graphics-mesa/artifacts/mesa-renderer-build/thread-build \
  --libnx /path/to/staged/libnx --output artifacts/mesa-allocator-original
python3 tests/graphics-buffer-diagnostics/build-allocator-test.py --fixed \
  --mesa-build third_party/graphics-mesa/artifacts/mesa-renderer-build/thread-build \
  --libnx /path/to/staged/libnx --output artifacts/mesa-allocator-fixed
```

Both output directories must be new. Keep the compile database's complete
source/build tree and compiler inputs in place, using the same staged libnx
as the host. The helper selects exactly one Nouveau allocator compile entry,
copies source and fixture, builds an ELF/map/NRO and records generated inputs.
The fixed variant applies the checked patch; the original variant does not.

Execution is separate from compilation. The original variant checks that a
forced BO creation failure exposes the invalid allocation/reference; process
teardown owns its deliberately corrupted state. The fixed variant requires a
null allocation/reference, zero offset and unchanged empty bucket lists. It
then checks aligned allocations and valid BO references over 256 lifetimes.
These are fixture expectations, not recorded results or full driver coverage.

The NROs write /switch/mesa-allocator-original.txt and
/switch/mesa-allocator-fixed.txt respectively, replacing existing files.
Preserve prior logs before running. No original/fixed NRO, map, generated
manifest or captured output belongs in source history.

## Optional NV failure diagnostics

nv-diagnostics.c wraps the public libnx nvioctlNvmap_Create,
nvioctlNvmap_Alloc and nvAddressSpaceMap APIs. It forwards each call and returns
its unchanged Result, logging failures with call counters, native malloc usage
and bounded kernel-memory-record enumeration. The wrappers neither retry nor
fabricate success and do not make an insufficient resource budget sufficient.

Select --nvmap-diagnostics in host/build.py only with a runtime whose host
builder supports --wrap-symbol:
[28f11cbde60e84568575f069f53280b25d7b71ca](https://github.com/pixelomer/dotnet-runtime/tree/28f11cbde60e84568575f069f53280b25d7b71ca).
Acquire that revision through the runtime URL in the
[host source guide](../../host/README.md), build its complete native/managed
inputs using its [pinned build instructions](https://github.com/pixelomer/dotnet-runtime/blob/28f11cbde60e84568575f069f53280b25d7b71ca/src/coreclr/pal/tests/libnx/host/README.md),
and supply the coherent tree to both --runtime and --runtime-baseline.
This revision also contains the protected data-pool API.

The application builder compiles the wrapper source, selects exactly those
three linker wraps and records the flag in its manifest. Normal builds omit
the wrappers. Use the same target SDK/ABI for all native objects, and retain
failures and generated diagnostics outside source history.
