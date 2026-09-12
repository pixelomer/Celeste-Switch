# FNA and asynchronous FMOD binding fixture

This original fixture calls the FMOD bindings in a user-owned, converted
Celeste assembly without invoking the game's entry point. It renders a small
FNA scene while native FMOD plays UI-bank events asynchronously. Event callbacks
and the main loop request collections; assertions cover graphics progress,
mixer/buffer counters, callback failures and output release/reinitialization.
The scene is not a game-performance benchmark or proof of mod compatibility.

## Build dependencies from source

Use the [graphics source recipe](../fna-graphics/README.md) to obtain its
pinned runtime/FNA/FNA3D/MojoShader/SDL/Mesa sources and build artifacts/fna-graphics.
Keep those outputs in place: their generated manifest records absolute archive
locations, and this builder verifies the archives and FNA assembly before use.
These are newly produced local inputs, not downloadable prebuilt packages.
The runtime checkout at third_party/graphics-runtime must have its native
CoreCLR, source SDK, IL CoreLib and libs.sfx framework outputs in the documented
layout. Preserve the recipe's ICU_NX_INSTALL_DIR environment setting.

Use the [conversion recipe](../../tools/coreify/README.md) to produce
artifacts/coreified/Celeste.dll from a copy of the supported user-owned PC
assembly. That assembly supplies the FMOD binding types; the SDK's managed
binding source is neither copied nor recreated here. Do not redistribute the
converted assembly. Coreification alone does not prove that its referenced
framework identities work with the selected CoreCLR/BCL.

Follow the [native FMOD input recipe](../fmod-11014/README.md) for the exact
licensed 1.10.14 Android/Linux SDK archives, pinned public loader, JDK 21 and
complete staged libnx SDK. Set JAVA_HOME to that JDK's root and put devkitA64
and switch-tools on PATH. The include paths must supply jni.h and Linux
jni_md.h; the builder uses devkitPro portlibs under /opt/devkitpro.

Copy only Master Bank.bank, Master Bank.strings.bank and ui.bank from your
matching PC distribution into ignored local/fmod-banks. This fixture uses
event:/ui/main/button_select through the game's existing FMOD bindings.
Create a new native build with those user-owned banks:

```sh
python3 tests/fmod-11014/build.py \
  --archives local/fmod-archives --loader third_party/fmod-loader \
  --libnx /path/to/staged/libnx --banks local/fmod-banks \
  --event event:/ui/main/button_select --output artifacts/fmod-11014
python3 tests/fmod-managed/build.py \
  --runtime third_party/graphics-runtime \
  --runtime-baseline third_party/graphics-runtime \
  --graphics-build artifacts/fna-graphics --fmod-build artifacts/fmod-11014 \
  --celeste artifacts/coreified/Celeste.dll --output artifacts/fmod-managed
```

Use the same staged libnx SDK as the graphics runtime. Both output directories
must be new; choose corresponding new paths throughout if either already exists.
Building the native input does not require running its Linux or Horizon fixture.

The managed builder checks the FMOD version/output API and each SDK file against
the native input manifest. It snapshots the shared [native adapter](../../native/fmod/README.md),
probe and pinned/generated loader/import sources, compiles six native objects,
then invokes the runtime's host builder with the paired FNA/game references,
resident graphics exports and native archives. Adapter callback threads use a
1536 KiB minimum stack. Symbols, source copies and manifests stay in the new
ignored output. These commands do not deploy or execute either fixture.

## Workload and file ownership

Install artifacts/fmod-11014/payload under /switch/celeste-fmod-11014 on SD:
the two Android libraries belong in lib/ and the three banks in banks/.
Install artifacts/fmod-managed/host/managed under /switch/celeste-audio-managed.
Preserve existing destination files first. Run celeste-audio-managed.nro from
the managed build in full application mode; no controller input is required.

The fixture runs a changing rectangle for 20 seconds and requests up to 60
UI events. It requires exact native FMOD version 0x11014, more than 600 frames,
1000 mixed blocks, 20 nonzero blocks, 500 released buffers and 60 callbacks,
including callbacks off the main managed thread. Callback failures and native
output errors must be zero. Releasing the system must stop mixer progress;
a subsequent initialization must produce more blocks and release cleanly.
These are source assertions, not prior measurements.

The host replaces /switch/celeste-audio-managed-stdout.txt,
 /switch/celeste-audio-managed-stderr.txt and
 /switch/celeste-audio-managed-probe.txt. It also clears its shared
/switch/coreclr-jit-disasm.txt and /switch/coreclr-soak-progress.txt scratch logs.
Save needed logs before launching. Copy the three application logs to ignored
artifacts/fmod-managed-logs as stdout.txt, stderr.txt and runtime.txt.
Require all 11 checks, END PASS, empty stderr and successful CoreCLR
execute/shutdown with exit 100. Check application exit separately.

## Optional file-integrity checks

The verifier checks the NRO against integration-manifest.json, all host managed
assemblies against their build manifest, separate installed managed/audio
checksum reports and the three runtime logs. Use the generic checksum report
format documented by the [graphics fixture](../fna-graphics/README.md#optional-file-integrity-report);
no private transfer utility is needed.

For managed files, with the powered-off console's SD card mounted read-only
and its payload unchanged since the run, this creates a new ignored report
directory by reading actual local and installed bytes. Replace the mount path.
It does not write to the card or perform deployment:

```sh
python3 - /path/to/mounted-sd <<'PY'
import hashlib, json, sys
from pathlib import Path
sd = Path(sys.argv[1]).resolve()
build = Path("artifacts/fmod-managed")
out = Path("artifacts/fmod-managed-readback")
out.mkdir(parents=True, exist_ok=False)
manifest = json.loads((build / "host/build-manifest.json").read_text())
directory = manifest["managed_directory"]
if directory != "/switch/celeste-audio-managed":
    raise SystemExit("Unexpected managed directory")
files, records = [], []
for file in sorted((build / "host/managed").glob("*.dll")):
    expected = hashlib.sha256(file.read_bytes()).hexdigest()
    if expected != manifest["managed_sha256"].get(file.name):
        raise SystemExit("Changed build input: " + file.name)
    installed = sd / directory.lstrip("/") / file.name
    observed = hashlib.sha256(installed.read_bytes()).hexdigest()
    if observed != expected:
        raise SystemExit("Installed file differs: " + file.name)
    destination = "sdmc:" + directory + "/" + file.name
    files.append({"destination": destination, "sha256": expected})
    records.append("VERIFIED existing " + observed + " " + destination)
if len(files) != len(manifest["managed_sha256"]):
    raise SystemExit("Incomplete local managed directory")
identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
(out / "manifest.json").write_text(json.dumps({"id": identity, "files": files}, indent=2) + "\n")
lines = ["BEGIN payload deployment manifest=" + identity] + records
lines.append(f"END deployment verified={len(files)} copied=0 failures=0")
(out / "readback.txt").write_text("\n".join(lines) + "\n")
PY
```

For the native libraries and banks, use the Python readback snippet in the
[native FMOD guide](../fmod-11014/README.md#optional-pcm-and-file-integrity-checks)
with the same artifacts/fmod-11014 build. That snippet creates
artifacts/fmod-readback/manifest.json and readback.txt; the native guide's
separate PCM-verifier command is not required by this managed fixture.

Then check the paired reports and logs:

```sh
python3 tests/fmod-managed/verify.py \
  --build artifacts/fmod-managed --audio-build artifacts/fmod-11014 \
  --logs artifacts/fmod-managed-logs \
  --managed-manifest artifacts/fmod-managed-readback/manifest.json \
  --managed-log artifacts/fmod-managed-readback/readback.txt \
  --audio-manifest artifacts/fmod-readback/manifest.json \
  --audio-log artifacts/fmod-readback/readback.txt \
  --output artifacts/fmod-managed-verified.json
```

The verifier replaces --output if present; preserve needed output first.
A checksum match is not authentication or proof of where code executed.
Keep all captured logs, images, manifests, native SDK material and game assets
outside source history. Live update, arbitrary native modules, extended
suspend/dock/audio-device behavior, full game entry and ordinary Everest Mods/
loading are outside this fixture's demonstrated scope.
