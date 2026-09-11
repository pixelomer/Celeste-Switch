# Original runtime-hook fixtures

These original sources check hosting prerequisites, not full game compatibility
or normal Mods/ discovery. See the [desktop fixture recipe](../README.md) for
the exact SDK, MonoMod checkout/build, package cache and output requirements.

## Horizon source inputs

Use MonoMod revision a57bbf1e45fe4e2cf4e94690f6687c51a1377136 from that recipe.
Its source includes the Horizon system/embedded-JIT backend and ARM64 exception
helper. Build net10.0 with ArtifactsPath set to the source checkout's
artifacts/sdk-compiler-control, as required by build-switch.py.

Obtain the runtime with embedded callback ownership and reverse-transition
poll handling from the source in this publication set:

```sh
git clone https://github.com/pixelomer/dotnet-runtime.git third_party/hook-runtime
git -C third_party/hook-runtime checkout --detach 2cca9644463dc97ebcf0680326df5fbf729fc6ab
```

Follow that revision's
[hosting profile](https://github.com/pixelomer/dotnet-runtime/blob/2cca9644463dc97ebcf0680326df5fbf729fc6ab/docs/workflow/libnx-supported-profile.md)
and linked host/thread build recipes to build native CoreCLR and matching
IL CoreLib/BCL, stage the required libnx source build and ICU, and install
the SDK/Python prerequisites. Use devkitA64 with DEVKITA64 pointing at its
installation when it is not under /opt/devkitpro/devkitA64.
The source tree must contain these source-built inputs:

- artifacts/bin/coreclr/libnx.arm64.Release/IL/System.Private.CoreLib.dll;
- artifacts/bin/runtime/net10.0-libnx-Release-arm64;
- the selected source SDK in .dotnet;
- native runtime archives in the host recipe's build layout.

From this repository root, after those producer builds:

```sh
python3 tests/runtime-hooks/build-switch.py \
  --runtime third_party/hook-runtime \
  --runtime-baseline third_party/hook-runtime \
  --monomod third_party/hook-monomod \
  --output artifacts/runtime-hooks-switch
```

Both runtime arguments may use the same coherently built source tree.
The helper compiles the native callback table and MonoMod exception bridge,
resolves managed dependencies from deps.json and delegates NRO/IL preparation
to the runtime's host builder. It requires a new output directory and does not
deploy or run the NRO.

## Fixture contract and output ownership

The managed fixture checks code allocation/publication, RX backup/restoration,
callback compare-exchange ownership, protected JIT RELRO, ordered hooks,
ILHook, compacting GC, exceptions, worker JIT and finalizers. Plain delegate
and UnmanagedCallersOnly callbacks execute with a collector before MonoMod
initialization; reverse-transition entry must precede managed GC polls.
It does not patch a method concurrently with another thread executing it.

For a run, host/managed supplies /switch/celeste-hook-probe and the NRO is
host/coreclr-host-probe.nro. The application writes
/switch/celeste-hook-probe.txt, /switch/celeste-hook-stdout.txt and
/switch/celeste-hook-stderr.txt. Preserve existing destination files and logs
before installing or running it. Store the resulting logs under an ignored
directory as runtime.txt, stdout.txt and stderr.txt.

```sh
python3 tests/runtime-hooks/verify-switch.py \
  --build artifacts/runtime-hooks-switch \
  --logs artifacts/runtime-hooks-logs \
  --output artifacts/runtime-hooks-verified.json
```

The verifier checks every assembly's length/FNV against the local SHA-256
manifest, empty stderr, managed success and successful execute/shutdown markers.
FNV is an integrity comparison, not authentication. The output JSON is replaced
if it exists; preserve needed output first. Logs, manifests and binaries are
generated data and must remain outside source history.
