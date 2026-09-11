# Source-built assembly conversion

This thin command-line host calls Everest NETCoreifier on one copied assembly
and writes a new output. It checks that the input stays unchanged and that
Required32Bit/Preferred32Bit are cleared, and reports input/output metadata.
It does not invoke the game entry point, copy native libraries or inject mods.
Conversion alone does not establish runtime or game compatibility.

## Source dependencies

Use Git, .NET SDK 10.0.111, a .NET 8 runtime for the resulting command-line tool,
and NuGet access. Obtain MonoMod revision
a57bbf1e45fe4e2cf4e94690f6687c51a1377136 using the
[fixture source recipe](../../tests/README.md), including its iced submodule.
The following commands expect that checkout at third_party/hook-monomod.

From this repository root, obtain the exact public Everest source:

```sh
git clone https://github.com/EverestAPI/Everest.git third_party/coreify-everest
git -C third_party/coreify-everest checkout --detach 47d6a61fa918c17b8085b93b61ee59a7465968f8
(
  cd third_party/hook-monomod
  dotnet build src/MonoMod.Patcher/MonoMod.Patcher.csproj \
    -c Release -f net8.0 -p:RoslynVersion=5.0.0 -p:MMUseSdkCompiler=true \
    -p:UseSharedCompilation=false -p:UseAppHost=false \
    -p:ArtifactsPath="$(pwd)/artifacts/sdk-compiler-control"
)
dotnet build tools/coreify/Coreify.csproj -c Release \
  -p:EverestRoot="$(pwd)/third_party/coreify-everest" \
  -p:MonoModBinaries="$(pwd)/third_party/hook-monomod/artifacts/sdk-compiler-control/bin/MonoMod.Patcher/release_net8.0" \
  -p:ArtifactsPath="$(pwd)/artifacts/coreify-build" \
  --output "$(pwd)/artifacts/coreify-tool"
```

The projects compile NETCoreifier source directly and reference the paired
net8 MonoMod.Patcher, Utils and Cecil binaries. UseAppHost=false avoids
unnecessary native apphost inputs for the dotnet-invoked tool.
These dependencies retain their original MIT notices.

## User-owned input and output

Copy Celeste.exe, Celeste.Content.dll and FNA.dll from your supported PC FNA
distribution into a separate ignored local/coreify-input directory. Omit native
PDBs from that copy and preserve the original distribution and saves.
See the [project input contract](../../research/BASELINE.json).
Create an ignored output directory and choose a new output file:

```sh
mkdir -p artifacts/coreified
dotnet artifacts/coreify-tool/CelesteSwitch.Coreify.dll \
  local/coreify-input/Celeste.exe artifacts/coreified/Celeste.dll \
  > artifacts/coreified/conversion.json
```

The tool rejects an existing output assembly or the same input/output path.
The shell redirection replaces an existing conversion.json; preserve it first
if needed. Producer/build commands replace their generated outputs as usual.
Run conversion unprivileged. If using a privileged container, first isolate
the tool and input with read-only mounts, no network, and a dedicated writable
output directory; do not grant the transformation access to unrelated files.

The input contract requires FMOD 1.10.14. Conversion does not replace its native
audio libraries or supply a Horizon FNA build. Keep generated game assemblies,
reports, banks and SDK material outside Git; do not distribute proprietary
inputs or converted derivatives.
