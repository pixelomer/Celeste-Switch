# Prepare a separate game copy with standard Everest

run.py combines a supported user-owned Linux or Windows FNA PC ZIP,
source-built Everest publish output,
source-built MiniInstaller and paired source-built FNA in a new staging copy.
It invokes the ordinary MiniInstaller with no application arguments.
No fixed mod set is injected and the game entry point is not invoked.
The resulting Mods/ directory remains the ordinary installation interface.

The [automatic installation build](../../docs/BUILDING.md) supplies these inputs
from its current source lock. The explicit recipe below is also used by focused
embedding/compatibility fixtures, whose guides substitute their paired revisions.

## Source-built Everest and installer inputs

Use Linux x86-64, Git, .NET SDK 10.0.111 and NuGet access. From this repository
root, obtain the exact source and recursively pinned dependencies:

```sh
git clone https://github.com/pixelomer/Everest.git third_party/host-everest
git -C third_party/host-everest checkout --detach 7f6e694f7466b330d8bb0de4715926e11dc84a58
git -C third_party/host-everest submodule update --init --recursive
(
  cd third_party/host-everest
  dotnet publish Celeste.Mod.mm/Celeste.Mod.mm.csproj -c Release \
    -o artifacts/pc-preparation/everest \
    -p:ArtifactsPath="$(pwd)/artifacts/pc-preparation/build" \
    -p:RoslynVersion=5.0.0 -p:MMUseSdkCompiler=true \
    -p:UseSharedCompilation=false -p:NuGetLockFilePath=packages.horizon.lock.json
  dotnet publish MiniInstaller/MiniInstaller.csproj -c Release \
    -o artifacts/pc-preparation/installer \
    -p:ArtifactsPath="$(pwd)/artifacts/pc-preparation/build" \
    -p:RoslynVersion=5.0.0 -p:MMUseSdkCompiler=true \
    -p:UseSharedCompilation=false -p:NuGetLockFilePath=packages.horizon.lock.json
)
```

The source revision retains upstream Everest 47d6a61fa918c17b8085b93b61ee59a7465968f8
with MonoMod a57bbf1e45fe4e2cf4e94690f6687c51a1377136 for the embedded JIT.
Its gitlinks also pin public NLua b3524288712743fb2394dcf615d14d0dac3276e2
and Everest-libs 591f7c12fcb4e8fda9ef5ef1b331b5ed40d3fb1f.
Keep submodules and their licenses together. Use the public upstream stripped
references in lib-stripped; do not replace them with original game binaries.

Publish, rather than only build, both projects so their managed dependency
closure is copied. The Everest output supplies NETCoreifier runtime shims
as well as the patcher/mod loader. The lib-ext submodule provides the upstream
desktop installer/apphost support; its desktop native libraries are not
Horizon libraries. Publishing can replace generated outputs; keep user game
inputs elsewhere.

Build the paired FNA source using the [host recipe](../../host/README.md).
For a standalone FNA build after that recipe's source acquisition:

```sh
dotnet build third_party/host-fna/FNA.Core.csproj -c Release \
  -p:TargetFrameworks=net8.0 -p:ArtifactsPath="$(pwd)/artifacts/installer-fna"
```

This produces artifacts/installer-fna/bin/FNA.Core/release_net8.0/FNA.dll.
It supplies the installer's FNA patch step, not a copied SDK binding implementation.

## Isolated local preparation

Install bubblewrap and util-linux setpriv. Ordinary users run directly; root
invocation assigns the new install tree to UID/GID 65534 and drops to that
identity with cleared groups and no-new-privileges before MiniInstaller runs.
Preparation has no network. Use a Linux build environment supporting the required
namespaces and exposes its dotnet host at /usr/bin/dotnet, with runtime files
under /usr. The sandbox mounts /usr and /proc read-only, supplies /dev and
temporary /tmp, and gives write access to the separate /install tree.
The runner sets DOTNET_ROLL_FORWARD=LatestMajor; the installed compatible
desktop runtime may be newer than the projects' net8.0 target.

For root invocation, ensure UID/GID 65534 can traverse the dedicated output
parent. Do not broaden unrelated directory permissions. Inputs are copied into
the new tree before installation; do not execute proprietary inputs as root.

In that environment, from this repository root:

```sh
python3 tools/prepare-everest/run.py \
  --pc-zip local/celeste-linux.zip \
  --everest-publish third_party/host-everest/artifacts/pc-preparation/everest \
  --installer-build third_party/host-everest/artifacts/pc-preparation/installer \
  --fna artifacts/installer-fna/bin/FNA.Core/release_net8.0/FNA.dll \
  --output artifacts/everest-prepared
```

The output directory must be new. The runner reads exactly Celeste.exe,
Celeste.Content.dll and FNA.dll from the ZIP, plus their optional supported
.config files; it does not extract the full game Content/ tree.
It rejects duplicate or oversized selected members and checks all three managed
assembly digests against the supported [PC input contract](../../research/BASELINE.json)
before invoking the installer. It is not a full Content archive validator.
It installs into output/install, with an empty Content/ directory for
preparation, and supplies the selected source-built FNA in everest-lib/.
The isolated directory is named /install, not the upstream updater directory,
so ordinary installation does not auto-launch the game.

The command enforces a 300-second installer timeout and requires resulting
Celeste.dll, FNA.dll and MMHOOK_Celeste.dll files. inputs.json, outputs.json
and stdout.txt describe this invocation; they are generated outputs, not
download prerequisites. Prepared assemblies alone do not establish native
imports, complete application startup or normal mod compatibility.

Do not copy desktop apphosts/native libraries onto the SD card as Horizon
dependencies. The [native host](../../host/README.md) has its own runtime,
framework and FMOD inputs. Keep all original and transformed game files,
dependency binaries and logs outside Git and release assets; preserve saves.
