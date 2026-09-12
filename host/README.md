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

## Ordinary mod compatibility inputs and checks

This profile pairs the host with reservation-wide executable mapping and
Everest's legacy-hook trampoline adapter. It defines source inputs and
compatibility criteria, not recorded execution results or a general mod
compatibility guarantee. Use unchanged ZIPs through ordinary Mods/ loading.

### Pinned source inputs

| Component | Source revision |
| --- | --- |
| CoreCLR runtime | [0eb1db137241efc858865dc1cc1ec7ea1136cf44](https://github.com/pixelomer/dotnet-runtime/tree/0eb1db137241efc858865dc1cc1ec7ea1136cf44) |
| Compatible earlier managed-library baseline | [0159e182f138395199d3dc113171276563a57e57](https://github.com/pixelomer/dotnet-runtime/tree/0159e182f138395199d3dc113171276563a57e57) |
| Everest | [3e41108ffc335329986a66a07dff4b7b97b1aef3](https://github.com/pixelomer/Everest/tree/3e41108ffc335329986a66a07dff4b7b97b1aef3) |
| MonoMod | [a57bbf1e45fe4e2cf4e94690f6687c51a1377136](https://github.com/pixelomer/MonoMod/tree/a57bbf1e45fe4e2cf4e94690f6687c51a1377136) |
| FNA | [2faf7f15f5622863348f64c057ef4b7dd2d9b839](https://github.com/pixelomer/FNA/tree/2faf7f15f5622863348f64c057ef4b7dd2d9b839) |
| SDL2 | [53c56198d88a2c4b2c72b88b8621b413f9260ab6](https://github.com/pixelomer/SDL/tree/53c56198d88a2c4b2c72b88b8621b413f9260ab6) |
| libnx | [1ad156340a015986ceaedaaf8fba602d7fea2730](https://github.com/pixelomer/libnx/tree/1ad156340a015986ceaedaaf8fba602d7fea2730) |

Follow this guide's source-built input and standard Everest instructions above
with these substitutions:

- Select runtime 0eb1db137241efc858865dc1cc1ec7ea1136cf44 when cloning
  third_party/host-runtime, instead of the earlier direct-entry revision.
  Follow the [runtime host guide at that revision](https://github.com/pixelomer/dotnet-runtime/blob/0eb1db137241efc858865dc1cc1ec7ea1136cf44/src/coreclr/pal/tests/libnx/host/README.md)
  and its linked thread/context instructions to stage libnx, build native
  CoreCLR, IL CoreLib, libs.sfx, the source SDK and ICU.
- For a fresh build, both --runtime and --runtime-baseline name that same
  complete third_party/host-runtime source/build tree. The earlier baseline
  above identifies the same src/libraries and src/coreclr/System.Private.CoreLib
  source trees; it is not an unexplained prebuilt BCL requirement. Build the
  complete matching framework from source rather than mixing deployed DLLs.
- In the [standard Everest preparation recipe](../tools/prepare-everest/README.md),
  select Everest 3e41108ffc335329986a66a07dff4b7b97b1aef3 instead of
  7f6e694f7466b330d8bb0de4715926e11dc84a58. Keep its recursive submodules,
  paired MonoMod, SDK 10.0.111/Roslyn build properties and both source publish
  commands. Run the standard installer only on the dedicated user-owned copy.
- FNA and SDL retain the host recipe's pins. Use the staged libnx revision
  above for the runtime, SDL and other native inputs. The runtime's linked
  thread recipe already selects it. Preserve the graphics recipe's separately
  pinned FNA3D/MojoShader/Mesa inputs and the exact FMOD 1.10.14 adapters.
- Build Lua and the host using the complete new standard-installer output,
  including its patched Celeste/FNA and matching dependencies. The host's
  standard-Everest command remains applicable; no fixed mod set is injected.

Use fresh ignored source/output directories, or preserve existing generated
outputs before rebuilding. Keep original game data, converted assemblies,
FMOD SDKs/banks, build products and logs out of source history and release
assets. Preparation and compilation do not establish gameplay compatibility.

### Integration contracts

The runtime maps an executable reservation once, initially inaccessible, and
enables its committed pages. Its [executable-memory fixture](https://github.com/pixelomer/dotnet-runtime/blob/0eb1db137241efc858865dc1cc1ec7ea1136cf44/src/coreclr/pal/tests/libnx/executable-memory/README.md)
covers page commitment, permissions, release and rollback without turning
finite mapping capacity into a claim of unlimited mod headroom.

Everest resolves NextTrampoline through IHook with the older IDetour fallback.
The [legacy-detour fixture](../tests/legacy-detour/README.md) checks redirection,
original calls, undo, reapply and disposal without invoking the game entry.
The shared adapter is the integration boundary; do not patch individual mod
ZIPs to work around its interface.

The selected Everest disables the external shared-memory autosplitter on
Horizon. The host supplies application-local TMPDIR and suppresses the external
desktop crash viewer, not error logging. Unsupported OS/native services must
remain explicit failures; these settings do not add IPC or desktop process
support.

### Observable criteria and limits

Select packages using the [mod compatibility guide](../tests/mods/README.md).
Check packages individually before assessing combinations:

Check hook-driven behavior, rendering, settings persistence after restart,
and restoration of changed options without losing unrelated game state.

Preserve saves and unrelated mod settings before changing them. Inspect module
loading, visible behavior, settings and errors together. Everest's entry
implementation calls Environment.Exit(0), including after handled boot errors:
a zero native exit is neither proof of compatibility nor a return through
coreclr_shutdown.

These criteria do not establish hot-unload support, full chapter coverage,
stable frame timing, large-pack memory capacity, acoustic output correctness,
arbitrary native dependencies or online/TLS support. Assess those separately
using the [broader compatibility criteria](../docs/ROADMAP.md). Keep captured
observations outside Git; do not present a source inventory as an execution
result.

## Managed data-pool budget

--managed-pool-mib selects the shared GC/PAL physical data-backing budget at
host build time. It accepts integer MiB values from 64 through 2048 and defaults
to 512; invalid values fail argument parsing. Append this option to the host
build command when selecting a different budget. The builder records the
chosen value and the selected runtime's nxvm.h identity in its generated
integration manifest.

Use the runtime revision in the ordinary-mod source profile above: its GC
memory heuristics read the actual shared-pool capacity. The builder includes
that runtime's src/native/libs/Common header and defines the selected budget
for the native host. Before CoreCLR initialization, native setup calls
nxvm_ensure_initialized and requires the resulting capacity to equal the
requested budget. Initialization failure or a differently sized existing pool
aborts setup; the host does not silently fall back to another allocation.

This pool is separate from native graphics, audio and executable-code backing.
Increasing it consumes process memory and does not make all of that memory
available to managed objects. Assess the combined memory budget and workload
instead of interpreting the upper argument limit as a guaranteed allocation.
The option does not change mod ZIPs or replace the ordinary loader.

## Optional live stdout and stderr

Add --nxlink-stdio to the host build command to select libnx's existing nxlink
output connection. The builder records the option in the integration manifest
and defines CELESTE_NXLINK_STDIO for the native host. Compilation still does
not deploy or launch the application.

For this optional mode, launch through the nxlink utility supplied with the
devkitPro Switch tools, with its stdio server enabled. The launcher supplies
the callback address consumed by libnx; a direct launch without that callback
is not equivalent. Socket initialization or connection failure aborts host
setup. Keep network output and any local capture confined to a trusted
development environment.

The default remains SD stdout/stderr. The selected mode connects and redirects
both streams before managed-pool and application setup, keeping socket/BSD
lifetime through process exit. The native probe log remains on SD. Earlier
runtime log initialization and its documented overwrite behavior still apply;
the option is not a log backup mechanism and does not rotate Everest's own
logs or history. Preserve existing logs before a run and keep captures outside
source history.

## GC region reservation

--gc-region-mib optionally selects the upstream DOTNET_GCRegionRange setting
in MiB. Zero, the default, leaves the runtime's existing configuration alone.
A nonzero value must be at least 64 MiB, a multiple of 64 MiB and no larger
than --managed-pool-mib; the builder rejects invalid values. The selection is
compiled into CELESTE_GC_REGION_MIB and recorded in the generated manifest.

Before setting the environment option, native setup additionally requires
at least 64 MiB of the actual nxvm virtual arena to remain outside the selected
GC region. It aborts if that guard or setenv fails. The byte value is formatted
as hexadecimal for the upstream configuration parser, then reported at startup.

Physical backing and virtual reservation are separate limits. With no explicit
region override, the selected runtime caps its computed default region range
at half the shared virtual arena; other GC settings also affect that default.
Increasing physical backing alone does not enlarge the virtual arena or
automatically remove that cap. Leave room for GC bookkeeping and other shared
PAL/BCL users, and assess total native/managed usage rather than treating an
accepted option value as proof that a workload will fit. This option does not
change allocator reservation semantics or mod behavior.
