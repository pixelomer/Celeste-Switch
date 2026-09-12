# Lazy-loading event compatibility fixture

This original desktop fixture exercises the prepared VirtualTexture.Preload
and Texture_Safe implementations. It replaces only Engine.ContentDirectory
and GPU Reload, writes its own two-integer size header in isolated /tmp and
does not construct Engine, invoke the game entry or create a graphics device.
It still loads and calls assembly code; use an unprivileged isolated environment.

The selected Everest implementation adopts the additive ShouldForceLazyLoad
and OnLazyLoad interfaces from [upstream PR 1160](https://github.com/EverestAPI/Everest/pull/1160),
whose source revision is 22ecab9646292294e7328070a7514f191d044061.
It preserves the existing texture loader rather than adopting the full FTL
rewrite. No mod ZIP is changed by this fixture or by standard preparation.

## Prepare matching assemblies

Follow the [standard Everest preparation recipe](../../tools/prepare-everest/README.md)
with these substitutions, using a new source checkout and prepared output:

| Recipe input | Fixture value |
| --- | --- |
| Everest source revision | cc8aaba288009879dc12482ceb43b4f536281e6e |
| Source checkout path | third_party/lazy-everest |
| Installer runner output | artifacts/lazy-everest-prepared |

The clone URL remains https://github.com/pixelomer/Everest.git. Substitute
third_party/lazy-everest for every third_party/host-everest path in the source
publish and installer commands, and artifacts/lazy-everest-prepared for the
runner's artifacts/everest-prepared output. Keep its recursive submodules,
SDK 10.0.111/Roslyn properties, source-built FNA and user-owned PC ZIP.
The resulting install/ directory must contain paired Celeste.dll, FNA.dll,
MonoMod.RuntimeDetour.dll and their remaining dependencies. MonoMod remains
pinned to a57bbf1e45fe4e2cf4e94690f6687c51a1377136.

Do not reuse a game assembly patched against different dependencies. Original
and patched proprietary assemblies remain local inputs, never repository
contents or release assets.

## Build separately from execution

From this repository root, with .NET SDK 10.0.111 and a .NET 10 desktop runtime:

```sh
dotnet build tests/lazy-loading/LazyLoadingProbe.csproj -c Release \
  -p:PreparedInstall="$(pwd)/artifacts/lazy-everest-prepared/install" \
  -p:ArtifactsPath="$(pwd)/artifacts/lazy-loading-build" \
  --output "$(pwd)/artifacts/lazy-loading"
```

The project targets net10.0 without a native apphost. PreparedInstall supplies
three compilation references with Private=false; execution must use the full
same prepared installation, not just the fixture output. Preserve existing
generated outputs before rebuilding.

For execution, use a disposable Linux environment without credentials or
unrelated data. Install bubblewrap and /usr/bin/dotnet with its runtime under
/usr. Run as an unprivileged user with read/traverse access to both input trees:

```sh
test "$(id -u)" -ne 0 && \
bwrap --die-with-parent --unshare-all \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 --symlink usr/lib /lib \
  --dev /dev --ro-bind /proc /proc --tmpfs /tmp \
  --ro-bind "$(pwd)/artifacts/lazy-loading" /fixture \
  --ro-bind "$(pwd)/artifacts/lazy-everest-prepared/install" /install \
  --chdir /fixture --clearenv --setenv PATH /usr/bin:/usr/sbin \
  /usr/bin/dotnet /fixture/LazyLoadingProbe.dll /install
```

The sole positional argument is the prepared installation directory. The
fixture's /tmp/lazy-probe.data is created only in this disposable writable
mount. Do not run proprietary inputs as root or expose unrelated saves.

## Assertions and scope

Ten assertions cover eager defaults, mod-forced deferral and dimensions,
preserved force decisions during size reads, deferred getter reload/notification,
no late-load notification on explicit Reload, global-setting precedence with
subscriber side effects, eager getter behavior and unsubscribe restoration.
Failures throw; completion prints the assertion count.

These CPU-level adapter checks do not establish rendering behavior, texture
budget, stutter-free loading, actual mod compatibility or full gameplay.
Keep captured output outside source history and assess those broader contracts
separately through ordinary game/mod loading.
