# SD-backed PC Celeste host

The native host executes the user's converted Celeste.dll directly with
CoreCLR .NET 10. It selects /switch/celeste-pc as the working, managed-base
and preference directory, preserving the game's entry-assembly identity.
It links the paired FNA/FNA3D/SDL/OpenGL stack and exact FMOD 1.10.14 adapters.
It does not replace game logic or inject a mod collection.

## Source-built inputs

Use the Linux toolchain, Python packages, SDK and source-built native graphics
archives from the [graphics recipe](../tests/fna-graphics/README.md).
Build artifacts/fna-graphics and retain its original inputs at their generated
manifest paths; the host checks those archives before selecting its updated SDL.
Keep DEVKITPRO and ICU_NX_INSTALL_DIR set as described there.

Direct application entry requires the following additional pinned sources.
From this repository root, use fresh ignored directories:

```sh
git clone https://github.com/pixelomer/dotnet-runtime.git third_party/host-runtime
git -C third_party/host-runtime checkout --detach 39e3af33e119e59ae9a3737ec04b23db28af98f3
git clone https://github.com/pixelomer/FNA.git third_party/host-fna
git -C third_party/host-fna checkout --detach 2faf7f15f5622863348f64c057ef4b7dd2d9b839
git -C third_party/host-fna submodule update --init --recursive
git clone https://github.com/pixelomer/SDL.git third_party/host-sdl
git -C third_party/host-sdl checkout --detach 53c56198d88a2c4b2c72b88b8621b413f9260ab6
```

Build the runtime's matching native CoreCLR, IL CoreLib, libs.sfx framework,
source SDK and source-built ICU using its pinned
[host recipe](https://github.com/pixelomer/dotnet-runtime/blob/39e3af33e119e59ae9a3737ec04b23db28af98f3/src/coreclr/pal/tests/libnx/host/README.md)
and linked thread/SDK instructions. --runtime and --runtime-baseline below
both name that coherent source/build tree. The host requires the
--application-entry option and HostConfigureApplication integration.
Do not substitute an unspecified runtime archive or foreign CoreLib.

This FNA revision selects AppDomain's managed base directory for Nintendo
Switch. Its FNA3D/MojoShader gitlinks retain the graphics recipe's paired
native revisions. SDL enables its Switch filesystem backend and returns
the application's selected SD preference directory without a device prefix.
Build SDL with the same complete staged libnx SDK used by the host runtime:

```sh
python3 third_party/host-sdl/build-scripts/build-libnx.py \
  --libnx /path/to/staged/libnx --output artifacts/host-sdl
```

The output directory must be new. Keep the older graphics build intact;
host/build.py verifies its native inputs, replaces only its selected SDL archive
with this manifest-checked build, and rebuilds managed FNA from host-fna.

Use the [Everest source-publication commands](../tools/prepare-everest/README.md#source-built-everest-and-installer-inputs)
to obtain third_party/host-everest at
7f6e694f7466b330d8bb0de4715926e11dc84a58 and publish its projects.
For the vanilla host, only the source-publication step is required; do not
substitute the standard installer's patched game output for vanilla input.
The resulting artifacts/pc-preparation/everest directory supplies NETCoreifier
and its managed dependency closure. Its external/MonoMod gitlink is
a57bbf1e45fe4e2cf4e94690f6687c51a1377136, supplying the source-owned ARM64
exception helper and matching embedded-JIT interface.

## User-owned game and audio inputs

Follow the [assembly conversion recipe](../tools/coreify/README.md) to build
the NETCoreifier command-line tool and produce artifacts/coreified/Celeste.dll
from the supported PC game's copied Celeste.exe. Also convert the copied
content assembly to a new output file:

```sh
dotnet artifacts/coreify-tool/CelesteSwitch.Coreify.dll \
  local/coreify-input/Celeste.Content.dll artifacts/coreified/Celeste.Content.dll \
  > artifacts/coreified/content-conversion.json
```

The assembly output must not exist; preserve an existing redirected JSON first.
Stage matching user-owned Content/ with the
[content tool](../tools/stage-content/README.md), producing artifacts/pc-content.
The original distribution, converted assemblies, content, banks and saves
remain user-owned and must not be redistributed.

Follow the [native FMOD recipe](../tests/fmod-11014/README.md) to obtain its
public pinned loader and licensed 1.10.14 Android/Linux SDK archives and build
artifacts/fmod-11014 with the same staged libnx SDK. Running that fixture is
not required to produce the host's inputs. The complete game's banks come from
its staged Content/ tree, not the small fixture's optional bank subset.
FMOD 1.10.20 and FMOD 2 are not supported substitutes.

Set JAVA_HOME to the Linux JDK 21 supplying jni.h and linux/jni_md.h.
The native build uses devkitA64 and switch-tools on PATH, devkitPro portlibs
under /opt/devkitpro and the staged SDK recorded in the runtime CMakeCache.
It does not assume a particular JDK installation path.

## Build the host

With those inputs present, from this repository root:

```sh
python3 host/build.py \
  --runtime third_party/host-runtime --runtime-baseline third_party/host-runtime \
  --graphics-build artifacts/fna-graphics --fmod-build artifacts/fmod-11014 \
  --celeste artifacts/coreified/Celeste.dll \
  --content-assembly artifacts/coreified/Celeste.Content.dll \
  --fna third_party/host-fna --sdl-build artifacts/host-sdl \
  --monomod third_party/host-everest/external/MonoMod \
  --dependency-directory third_party/host-everest/artifacts/pc-preparation/everest \
  --output artifacts/vanilla-host
```

The output directory must be new. The builder retains native source snapshots,
ELF/map, input hashes and an IL-only deployment check. It validates SDK files,
graphics archives and the updated SDL archive against the selected generated
manifests. It compiles the shared audio adapters and MonoMod exception helper,
retaining the public sources' notices.

Managed AssemblyRef metadata is traversed transitively from the selected FNA,
game and content assemblies. The matching Horizon framework takes precedence;
other references must be supplied by --dependency-directory or the build fails.
This includes NETCoreifier's runtime shims, not merely the conversion tool.
Reference closure and IL-format checks do not prove API or framework-identity
compatibility at runtime.

The runtime host receives Celeste.dll as the actual application entry, no
application arguments, and a zero BCL watchdog timeout for interactive use.
The native integration resolves embedded-JIT/exception-helper exports, FMOD,
and resident SDL2/FNA3D symbols. The FMOD library directory is selected at
compile time as sdmc:/switch/celeste-pc/lib; the independent fixtures keep
their own default directory. This command does not deploy or execute the game.

## Installation boundaries and logs

Copy the complete artifacts/vanilla-host/host/managed directory, including its
lib/ with the two Android FMOD libraries, under /switch/celeste-pc on SD.
Copy artifacts/pc-content/Content alongside those assemblies. Use the same
supported distribution for assemblies and content. Preserve existing files,
saves and logs before changing that application directory, and independently
compare installed file hashes with the generated build/content manifests.
Do not deploy desktop installer support libraries as Horizon libraries.

Run celeste-pc.nro in full application mode. Native setup requires the expected
preference directory, forces OpenGL, disables FNA's separate sound path
(the game uses FMOD) and disables late-swap tear. Native FMOD mappings live
until process exit; dynamic module unloading is not supplied.

The runtime overwrites /switch/celeste-pc-probe.txt,
 /switch/celeste-pc-stdout.txt and /switch/celeste-pc-stderr.txt, and clears its
shared coreclr-jit-disasm.txt and coreclr-soak-progress.txt scratch logs
under /switch. The game can also write its own error log and saves.
Check game state and error logs: a zero native exit alone does not prove
successful startup because the game can catch errors internally.

Use a separate local copy for [standard Everest preparation](../tools/prepare-everest/README.md).
Full game/mod compatibility, unsupported desktop services and lifecycle
behavior must be assessed independently. Normal Mods/ loading remains the
interface. Keep generated logs, binaries, game data
and source-build manifests outside Git and release assets.

## Standard Everest inputs

First run the [standard preparation tool](../tools/prepare-everest/README.md)
to produce artifacts/everest-prepared/install with paired patched Celeste/FNA,
MMHOOK_Celeste.dll, Celeste.Mod.mm.dll and the remaining managed dependencies.
Then build the [paired Lua archive](../native/lua/README.md) as artifacts/lua.

Use the same native/runtime, converted content assembly, source FNA, SDL and
MonoMod inputs described above, but select the standard installer's outputs:

```sh
python3 host/build.py \
  --runtime third_party/host-runtime --runtime-baseline third_party/host-runtime \
  --graphics-build artifacts/fna-graphics --fmod-build artifacts/fmod-11014 \
  --celeste artifacts/everest-prepared/install/Celeste.dll \
  --content-assembly artifacts/coreified/Celeste.Content.dll \
  --prepared-fna artifacts/everest-prepared/install/FNA.dll \
  --fna third_party/host-fna --sdl-build artifacts/host-sdl \
  --monomod third_party/host-everest/external/MonoMod \
  --dependency-directory artifacts/everest-prepared/install \
  --lua-build artifacts/lua --output artifacts/everest-host
```

The output directory must be new. --prepared-fna bypasses rebuilding FNA,
but --fna remains required to record its source revision. The selected patched
FNA must come from the same ordinary installer invocation as Celeste.dll.

The host explicitly stages MMHOOK_Celeste.dll and Celeste.Mod.mm.dll.
MMHOOK participates in managed dependency traversal. Celeste.Mod.mm is Cecil
input for runtime rule extraction; its unused Steam build-reference graph is
not staged as executable dependencies. This does not supply a Steam SDK or
make unsupported native services available.

--lua-build adds the archive only after its digest matches manifest.json and
retains the recorded Lua exports. The native resolver recognizes lua54.
The asynchronous FMOD output reports its current counters on close without
changing mixer ownership, timing or error handling.

Keep vanilla and modded local outputs separate. Both host variants currently
use /switch/celeste-pc, so back up its existing files and saves before switching
the selected installation. Install the complete generated managed directory,
not a mixture of framework or game assemblies from different builds.
Additional ordinary mod compatibility and unsupported OS/native services
remain subject to the project input and compatibility contracts.

## Application-local temporary files

Native setup creates /switch/celeste-pc/tmp and verifies that it is a directory
before initializing CoreCLR. It sets TMPDIR to that application-local path;
creation or directory-check failures abort setup. This supplies ordinary
temporary-file storage, not shared-memory IPC support.

The host sets Everest's existing EVEREST_NO_ERRORLOG_ON_CRASH option to 1,
suppressing an external desktop error-log viewer while retaining the error log.
Do not treat that option as a successful game exit or suppress the underlying
exception. Desktop process launching remains unsupported.
