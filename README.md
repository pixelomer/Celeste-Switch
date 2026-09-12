# Celeste with Everest for Nintendo Switch

Run the PC FNA version of Celeste and ordinary Everest mods as Horizon homebrew.
This port uses [CoreCLR/RyuJIT .NET 10](https://github.com/pixelomer/dotnet-runtime)
through [dotnet-switch](https://github.com/pixelomer/dotnet-switch). Mods load
normally from `Mods/`; they do not need to be compiled into the application.

Compatibility depends on the coordinated runtime, native libraries and mod set.
Use the [ordinary mod guide](tests/mods/README.md) and
[performance measurement method](docs/PERFORMANCE_INVESTIGATION.md) to assess
loading, gameplay and resource limits. Neither a successful build nor a selected
mod profile establishes compatibility with every mod or a frame-rate guarantee.

## Build your installation

Use Linux x86-64 and a supported, user-owned itch.io **Linux or Windows FNA PC
ZIP**. The supported PC assemblies internally report **1.4.0.0** and require exactly
**FMOD 1.10.14 Android ARM64**. You must supply the matching FMOD SDK archive
separately; the PC audio libraries do not supply the required ARM64 binaries.

From this repository checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
python3 build.py \
  --pc-zip /path/to/celeste-linux.zip \
  --fmod-android /path/to/fmodstudioapi11014android.tar.gz
```

Install the native/.NET build prerequisites in [BUILDING.md](docs/BUILDING.md)
first. The script fetches and builds pinned public source dependencies, prepares
your game locally using Everest's standard installer, and produces
`artifacts/build/package/sdcard/` plus a local installation ZIP. The ZIP contains
your game and FMOD files and must not be uploaded as a public release asset.
No separately built runtime folder or sibling checkout is required.

Follow [INSTALLING.md](docs/INSTALLING.md) to copy the installation to your SD
card, launch with full application memory, and add compatible mods.

## Components and compatibility

The source lock coordinates [Everest](https://github.com/pixelomer/Everest),
[MonoMod](https://github.com/pixelomer/MonoMod),
[FNA](https://github.com/pixelomer/FNA),
[FNA3D](https://github.com/pixelomer/FNA3D),
[MojoShader](https://github.com/pixelomer/MojoShader),
[SDL2](https://github.com/pixelomer/SDL), the runtime and
[libnx](https://github.com/pixelomer/libnx). Each fork has its own build entry
point and upstream history. Mesa, Lua and the narrow Android FMOD adapter are
assembled here from pinned sources and user-supplied inputs.

The removable [SwitchPerformance](src/SwitchPerformance/README.md) mod requests
larger buffers for scoped file checksums. New mod settings enable buffering and
disable diagnostics. The build's --without-performance-mod option omits the ZIP;
existing saved settings remain under the user's control. Buffering does not skip
hashes or imply a gameplay frame-rate improvement.

Everest/mod libraries target net8/net9 where appropriate while running on the
matching .NET 10 host; see [runtime compatibility](docs/RUNTIME_COMPATIBILITY.md).
Desktop/native-library mods, filesystem watchers, external process helpers,
Discord native integration and the external autosplitter have platform limits.
Keep the coordinated source pins when reproducing the
port; arbitrary Everest/runtime upgrades are not established as compatible.

See the [third-party notices](THIRD_PARTY.md). No commercial game implementation, FMOD
SDK, console keys or Nintendo SDK is supplied by this project.
[Focused fixtures](tests/README.md) retain original source and reproducible input
contracts. Generated builds, local inputs and observations belong outside Git.
