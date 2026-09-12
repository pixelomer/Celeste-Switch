# Legacy detour trampoline fixture

This original desktop fixture loads Everest's legacy MonoMod adapter from the
user's locally prepared Celeste.dll, then hooks only methods in the fixture.
It does not invoke the game's entry point. Loading an assembly and invoking
its adapter still executes code; use isolated, unprivileged inputs.

The six assertions cover the original method, redirection, an original-call
trampoline, undo, reapply with the existing original delegate, and disposal.
Failures throw; successful completion prints six PASS lines and exits normally.
Neither this desktop fixture nor a successful source build establishes
Horizon game/mod compatibility.

## Prepare the paired adapter

Use the [standard Everest preparation recipe](../../tools/prepare-everest/README.md)
with the following substitutions, keeping a fresh checkout and a separate
new prepared output:

| Recipe input | Fixture-specific value |
| --- | --- |
| Everest source revision | 3e41108ffc335329986a66a07dff4b7b97b1aef3 |
| Source checkout path | third_party/legacy-everest |
| Installer runner output | artifacts/legacy-everest-prepared |

The clone URL remains https://github.com/pixelomer/Everest.git.
Use the recipe's same recursive submodule initialization, two dotnet publish
commands, SDK/Roslyn properties, source-built FNA and user-owned PC ZIP.
Replace third_party/host-everest with third_party/legacy-everest in every
source/publish input path, and artifacts/everest-prepared with
artifacts/legacy-everest-prepared in the runner output. Publishing then running
the standard installer produces the paired Celeste.dll and dependencies under
artifacts/legacy-everest-prepared/install. Do not reuse a game assembly patched
against a different dependency set.

This source revision resolves NextTrampoline through the current internal
IHook interface with the older IDetour fallback. Its MonoMod gitlink remains
a57bbf1e45fe4e2cf4e94690f6687c51a1377136. Keep that paired dependency output,
not just Celeste.dll. No proprietary assembly or patched derivative belongs
in Git or a release asset.

## Build and run separately

Use .NET SDK 10.0.111 and a .NET 10 desktop runtime. From this repository root:

```sh
dotnet build tests/legacy-detour/LegacyDetourProbe.csproj -c Release \
  -p:ArtifactsPath="$(pwd)/artifacts/legacy-detour-build" \
  --output "$(pwd)/artifacts/legacy-detour"
```

The project targets net10.0 and uses no native apphost. The command only builds
the fixture; it does not load the game. Preserve existing generated outputs
before rebuilding.

For execution, use an unprivileged disposable Linux container/environment
without credentials or unrelated user data. Install bubblewrap and a dotnet
host at /usr/bin/dotnet with its runtime under /usr. The following gives the
process no network, read-only system/fixture/prepared-install mounts and
temporary writable /tmp. Run it as a non-root user with read/traverse access
to the dedicated inputs:

```sh
test "$(id -u)" -ne 0 && \
bwrap --die-with-parent --unshare-all \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 --symlink usr/lib /lib \
  --dev /dev --ro-bind /proc /proc --tmpfs /tmp \
  --ro-bind "$(pwd)/artifacts/legacy-detour" /fixture \
  --ro-bind "$(pwd)/artifacts/legacy-everest-prepared/install" /install \
  --chdir /fixture --clearenv --setenv PATH /usr/bin:/usr/sbin \
  /usr/bin/dotnet /fixture/LegacyDetourProbe.dll /install
```

Do not grant game/dependency code root privileges or access to other
installations and saves. The sole positional argument is the directory
containing the prepared Celeste.dll and matching dependency DLLs.
Keep any captured stdout/stderr outside source history. A native mapping or
framework-version failure must remain a failure; do not weaken an assertion
to match a particular run.
