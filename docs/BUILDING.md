# Building Celeste-Switch

## Host prerequisites

Use Linux x86-64 with Python 3.12+, Git, Bash, GCC/G++, Clang/LLVM, CMake, Ninja,
GNU make, patch, pkg-config, Meson, Bison, Flex, binutils, a JDK (JNI headers),
bubblewrap and util-linux. Use .NET SDK 10.0.111 under /usr for the managed
dependency builds and isolated installer. The runtime also
bootstraps its own source-pinned SDK and matching framework. NuGet and source
archive access are needed on the first build.

Install devkitPro's `switch-dev` and `switch-portlibs`, set `DEVKITPRO` to the
installation root (normally `/opt/devkitpro`), and add its `devkitA64/bin` and
`tools/bin` to PATH. Use devkitA64 GCC 15.2.0 for the selected native build inputs.
Pinned libnx is based on 4.12.0, satisfying the Horizon 21+ TLS ABI requirement.
The build creates a local SDK overlay and preserves the installed toolchain.

Use a Python virtual environment and `scripts/requirements.txt`. Install Mako
for the Python interpreter used by your Meson installation as well. A system
Meson may use system Python even when invoked from a virtual environment.
Set `JAVA_HOME` if `javac` is not on PATH. Normal users can build the port;
root is not required. User namespaces must be available for bubblewrap's
networkless game-preparation step. Root invocation drops installer privileges.

Plan for a large .NET source/build tree and a sustained native/managed build.
`--jobs N` controls native build concurrency; default is at most eight jobs.

## Inputs and command

Supply either supported itch.io Linux or Windows FNA ZIP, with `Celeste.exe`,
`Celeste.Content.dll`, `FNA.dll` and `Content/` at the archive root. Do not use a
Nintendo Switch NSP/XCI or an XNA/Steam build. The supported managed input hashes
are in `research/BASELINE.json`; unfamiliar game builds are rejected before
patching rather than silently treated as compatible.

Supply **fmodstudioapi11014android.tar.gz**, the exact Android ARM64 FMOD
1.10.14 SDK archive. Obtain it through your authorized FMOD access; if that
version is unavailable, contact Firelight Technologies. This repository does
not automate account authentication or provide the SDK. Neither FMOD 1.10.20
nor any FMOD 2 version is a compatible replacement. The Linux SDK is unnecessary
for this installation build.

```sh
python3 build.py \
  --pc-zip /absolute/path/to/celeste-linux.zip \
  --fmod-android /absolute/path/to/fmodstudioapi11014android.tar.gz \
  --jobs 8
```

`--output PATH` selects a new build directory. `--resume` verifies the recorded
inputs, recipes and completed outputs before continuing an interrupted build.
Incomplete outputs from stages requiring a fresh directory are preserved under
`incomplete/`. Changed source locks or recipes require a new output directory.
`--runtime-root PATH` is an optional expert override for an already built runtime
at the exact lock revision; it is not needed for a normal build.

--source-mirrors FILE.json is an optional mapping of canonical Git URLs to source
mirrors. It supplies Git objects, not built dependencies, and is unnecessary for
the normal source path. The build uses sources.lock.json and the forks' exact
gitlinks. Keep local mirror configuration outside source history.

## Build stages and outputs

The automatic build compiles CoreCLR/RyuJIT and its matching IL-only framework,
FNA, SDL2, paired FNA3D/MojoShader, Everest/MiniInstaller, full Mesa, Lua and the
native host. The standard Everest installer prepares only a new local game copy;
the game is not launched on the host. The FMOD loader source is fetched at its
reviewed public homebrew revision. No fixed mod pack is injected.

The automatic build explicitly selects:
1536 MiB protected managed backing, 1280 MiB GC region and 32 MiB NV transfer
memory. These are application memory allocations, not clock settings.

Outputs under the selected build directory include:

- `application/celeste-pc.nro`, with ELF/map and managed files under `application/host/`.
- `package/sdcard/switch/celeste-pc/`, the ready-to-copy local installation.
- `package/installation.json`, per-file sizes/hashes and source-lock identity.
- `package/celeste-switch-local.zip`, a local installation archive containing game/FMOD data.
- `build-state.json` and per-component manifests, recording reproducible inputs and outputs.

Only distribute original source, patch/build tools and dependencies whose
licenses permit it. The installation ZIP is not a publishable release asset.
See [THIRD_PARTY.md](../THIRD_PARTY.md). No build step deploys to or controls a console.

## Independent components

Each dependency fork supplies `build-horizon.py` and `README.horizon.md`
(MonoMod uses `README.libnx.md`). FNA's default build also builds its native
graphics dependencies; `--managed-only` produces just FNA.dll. SDL2, FNA3D and
MojoShader fetch and assemble complete libnx SDKs automatically, or accept
`--libnx PATH`. Everest builds its patcher and installer from the pinned sources.
The runtime's reusable source-build entry point is
[dotnet-switch](https://github.com/pixelomer/dotnet-switch).

## Focused host checks

```sh
python3 tests/horizon/test_sources.py
python3 tests/horizon/test_content.py
```

These use original small fixtures to verify pinned dependency fetching,
refusal to overwrite edited repositories, ZIP path/case boundaries and
preservation of existing output folders. They do not run Celeste or exercise the target platform.
The original checksum and runtime-hook fixtures have their own READMEs under
`tests/`; their scopes and target integration checks remain distinct.

Resume checks the recorded stage-output subset, not every file in dependency
trees or the installation directory. Preserve unchanged generated trees and
inspect their manifests; do not interpret a resumed stage as a new build/test
pass. The package validates its NRO, listed Content hashes and required file
presence, rejects deployment symlinks and checks ZIP CRCs. Those checks do not
establish runtime behavior or audit every managed binary against its producer.

Keep compiled runtime, framework, ICU, headers and libnx overlay together.
The optional --runtime-root path must be the exact locked source revision with
its completed source-build outputs and artifacts/horizon/environment.json;
the ordinary command constructs those inputs through dotnet-switch.
