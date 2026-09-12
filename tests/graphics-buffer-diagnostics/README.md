# Mesa buffer-upload diagnostic

This optional instrumented archive checks each buffer-upload destination
before Mesa copies data into it. It reports an inaccessible mapping and aborts
before that write. It adds per-upload overhead; it is a diagnostic, not a
performance optimization or a replacement for correcting an allocation failure.

## Source-built inputs

First follow the [graphics source recipe](../fna-graphics/README.md). Its pinned
standalone Mesa helper produces the complete, large-upload-capable libEGL.a
and the matching Meson compile database under
third_party/graphics-mesa/artifacts/mesa-renderer-build. It uses public,
checksum-pinned Mesa/package sources and requires no other application's
game or audio files.

Keep that entire generated source/build tree at its original path. The compile
database supplies the actual source path, working directory, compiler and
flags; the tool is not compatible with an unexplained copied database or an
archive from a different build. The devkitPro meson-cross wrapper generates
the cross-file named by the recipe. Install the documented compiler/portlibs
and use the same staged libnx SDK as the host.

From this repository root, with a new output directory:

```sh
python3 tests/graphics-buffer-diagnostics/build.py \
  --mesa-build third_party/graphics-mesa/artifacts/mesa-renderer-build/thread-build \
  --mesa-library third_party/graphics-mesa/artifacts/mesa-renderer-build/full-lib-large/libEGL.a \
  --libnx /path/to/staged/libnx \
  --output artifacts/graphics-buffer-diagnostics
```

The staged libnx path must contain include/ and lib/libnx.a. The builder
requires exactly one compile-database entry for util/u_transfer.c and exactly
one expected memcpy site. It copies that source, inserts check.h, and compiles
the instrumented copy using the recorded command with new output/include
arguments. It requires exactly one util_u_transfer.c.o member in the copied
archive before replacing that member. A mismatch must remain an error.

The original source, object tree and archive are not modified. The output
contains the copied source/header, replacement object, new libEGL.a and a
manifest with the compiler command and source/SDK/archive identities. These
are generated local outputs, not required checked-in files.

## Select the archive explicitly

Build the [application host](../../host/README.md) with its ordinary paired
inputs, adding --mesa-library artifacts/graphics-buffer-diagnostics/libEGL.a.
The host verifies its original graphics archive manifest first, requires a
single Mesa archive to replace, and records the explicit override path/hash
separately. Keep the original input files available at their recorded locations;
selecting an override does not bypass those checks.

## Diagnostic behavior and limits

The original check.h uses public libnx svcQueryMemory permissions. Writable
ranges pass through to the original memcpy unchanged. Invalid or zero-length
ranges report map/resource/transfer information and native allocator statistics,
dump readable words, flush stderr and abort. This is a failure-only diagnostic;
it neither repairs a mapping nor converts a failure into success.

Use ordinary host log handling or its optional nxlink stream, and preserve
existing logs before a run. The diagnostic does not deploy the host or change
console configuration. Keep captured addresses, heaps, logs, maps, generated
archives and any game data outside source history. A destination report locates
an invalid write; it does not by itself identify the underlying driver or
allocation defect.

## Optional allocator correction

Add --fix-allocator to the archive-building command above to apply the
[checked Nouveau patch](../../native/mesa/nouveau-mm-failure.patch) to a second
copied object. This requires exactly one matching allocator compile entry,
the expected slab-failure source text and one nouveau_mm.c.o archive member.
The builder preserves the upload check, adds a failure-only slab diagnostic,
and records the patch/source/compiler inputs with the resulting archive.

The compile entries must come from the same Mesa build working directory.
Use the [paired allocator control recipe](../../native/mesa/README.md) to build
original and fixed failure-injection NROs separately, and that guide's runtime
requirements for optional host NV wrappers. None of these commands deploys a
host, executes a fixture or demonstrates that a graphics workload will fit.

## Allocator-only archive

Use --fix-allocator --allocator-only to build an archive containing only the
allocator correction, leaving the original buffer-upload archive member in
place and omitting the added slab-failure log. --allocator-only without
--fix-allocator is rejected. For example, use the source/SDK inputs above with
a fresh --output artifacts/mesa-allocator-only directory and both flags.

The helper still reads/checks the upload source and archive member, writes the
source/header copies and records the proposed upload compile command. In this
mode it does not execute that command or replace the upload object.
buffer_diagnostic_compiled and allocator_only in the generated manifest
distinguish selected behavior from a merely recorded command.

Select the resulting libEGL.a explicitly through the host's --mesa-library.
The host's separate --nvmap-diagnostics flag is independent; leave it unset to
omit those driver wrappers. Neither archive selection nor an absence of
diagnostic overhead establishes adequate resource budgets or game compatibility.
