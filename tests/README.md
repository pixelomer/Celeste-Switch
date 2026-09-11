# Focused compatibility fixtures

Use original small managed/native fixtures with explicit expected behavior.
See [compatibility checks](../docs/ROADMAP.md) for runtime, hooking,
graphics, audio and storage contracts.

Document each fixture's input sources, build command, output ownership and
expected behavior. Keep generated reports and binaries in ignored artifacts/;
never commit game executables, banks or SDK material.

## Desktop runtime-hook fixture

The original net8/net9 assemblies exercise Hook chaining, original calls,
ILHook, exception propagation, compacting collections and collectible unloading.
CELESTE_HOOK_CONTROL=load-only skips hooks while retaining the unload check.
These are fixture assertions, not claims about completed runs.

Install Git, Python 3 and .NET SDK 10.0.111 (the builder disables SDK roll-forward).
NuGet access supplies the framework reference packs and locked dependencies.
From the repository root, obtain the SDK-compiler-capable MonoMod source:

```sh
git clone https://github.com/pixelomer/MonoMod.git third_party/hook-monomod
git -C third_party/hook-monomod checkout --detach 4f6b755bf59ec9f2d062821a87eec12bd5d678a8
git -C third_party/hook-monomod submodule update --init external/iced
(
  cd third_party/hook-monomod
  dotnet build src/MonoMod.RuntimeDetour/MonoMod.RuntimeDetour.csproj \
    -c Release -f net10.0 -p:RoslynVersion=5.0.0 -p:MMUseSdkCompiler=true \
    -p:UseSharedCompilation=false -p:ArtifactsPath="$(pwd)/artifacts/sdk-compiler-control"
)
python3 tests/runtime-hooks/build-host.py \
  --monomod third_party/hook-monomod/artifacts/sdk-compiler-control/bin/MonoMod.RuntimeDetour/release_net10.0 \
  --output artifacts/runtime-hooks-host
```

The helper builds and RUNS the host fixture, writes manifest.json and result.txt,
and returns its result. An explicit --output must be new; without it the default
directory is reused. --nuget-packages overrides NUGET_PACKAGES or the user's
standard package cache. Keep the cache from the MonoMod restore available: the
builder follows its deps.json and rejects missing or colliding dependencies.

The fixture requires the collectible context to die after forced collections;
it reports a failure rather than weakening that expectation. CELESTE_HOOK_WAIT=1
adds a five-minute diagnostic pause and prints the process ID. Keep generated
binaries and reports outside source history. This command does not deploy a console.
