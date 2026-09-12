# Exact FMOD 1.10.14 native fixture

This source-owned fixture uses FMOD 1.10.14 and output-plugin API 3. It checks
native initialization, synchronous mixing, a synthetic tone, optional bank
events and Horizon audout completion. It does not contain game code, SDK
headers/libraries, banks or recorded audio. Keep all such inputs and generated
outputs outside Git. Do not substitute FMOD 1.10.20 or FMOD 2.

## Obtain source and SDK inputs

Use Linux x86-64, Python 3, host GCC/binutils (including readelf), devkitPro's
devkitA64/switch-tools/libnx and portlibs, plus a Linux JDK 21 supplying
include/jni.h and include/linux/jni_md.h. This builder uses devkitPro portlibs
under /opt/devkitpro; place devkitA64/bin and tools/bin on PATH.
Set JAVA_HOME to the actual JDK root; no particular JDK installation path
is required.

Use the pinned [libnx source](https://github.com/pixelomer/libnx/tree/1ad156340a015986ceaedaaf8fba602d7fea2730)
and SDK-staging commands in the [runtime source recipe](../runtime-hooks/README.md).
The --libnx argument must identify the resulting complete SDK directory with
switch.specs, include/ and lib/libnx.a, not just a source include directory.
libnx 4.10.0 or newer is required for Horizon 21+ TLS.

Obtain the MIT loader source without changing its two input files:

```sh
git clone https://github.com/NaGaa95/hl2_nx.git third_party/fmod-loader
git -C third_party/fmod-loader checkout --detach 41e045ea275fcfae906009f165a6635725e9a08f
```

The builder checks that revision and source/so_util.c and source/so_util.h,
then adapts a generated copy for explicit host imports and fail-fast resolution.
Keep the loader's copyright and MIT notices with derived source.

Obtain the exact licensed FMOD Studio API 1.10.14 Android and Linux archives
from FMOD's authorized download service or support. Put the original
fmodstudioapi11014android.tar.gz and fmodstudioapi11014linux.tar.gz files
in an ignored local/fmod-archives directory. The builder checks their fixed
SHA-256 identities, the FMOD_VERSION header and output API 3 before compilation.
Those digests identify required external SDK inputs, not prior generated builds.
Local SDK access does not grant redistribution rights.

## Build

From the repository root, replacing JDK and staged-SDK paths:

```sh
export JAVA_HOME=/path/to/jdk-21
python3 tests/fmod-11014/build.py \
  --archives local/fmod-archives --loader third_party/fmod-loader \
  --libnx /path/to/staged/libnx --output artifacts/fmod-11014
```

The output directory must be new. The helper snapshots original sources,
extracts selected SDK members into sdk/, generates the bounded import table,
and builds celeste-fmod-11014.nro plus linux-probe. It leaves the input SDK
archives and loader checkout unchanged and performs no deployment or execution.

For bank events, supply --banks local/fmod-banks and --event event:/your/event
together. Use a separate new build output. Supply the matching user-owned banks
and strings bank needed by that event; only explicit .bank files are copied,
with strings banks ordered first. The fixture's output named music.f32 contains
the selected event, which need not be a music track. No timeline marker/beat
count is required.

## Isolated Linux reference

Install bubblewrap and util-linux's setpriv in a Linux environment supporting
user namespaces and the /usr library layout used by run-linux.py.
The helper requires root initially to create its new output directory and
switch to UID/GID 65534; the probe runs unprivileged, with no network, read-only
SDK/probe mounts and one writable output. Ensure that UID 65534 can traverse
the dedicated input/build paths and read those inputs. Do not broaden access
to unrelated private directories.

From such a build container, run:

```sh
python3 tests/fmod-11014/run-linux.py artifacts/fmod-11014 artifacts/fmod-linux
```

The output directory must be new and becomes owned by UID/GID 65534. The runner
records stdout.txt and enforces a 90-second timeout. Linux uses /sdk, /banks
and /output inside the namespace; these are runtime mount points, not
undeclared host prerequisites. The reference executable is linked with an
executable stack for this old Linux SDK; SDK bytes are not patched.
This is not a general desktop game launcher.

## Horizon workload and output ownership

Install the build's payload/ contents under /switch/celeste-fmod-11014 on SD,
then run celeste-fmod-11014.nro in full application mode. Preserve existing
files first. The fixture replaces probe.log, tone.f32 and, when banks are
selected, music.f32 in that directory. It does not read or modify saves.

The source requires exact runtime version 0x00011014, silent Studio
initialization/release, a stereo 48 kHz 440 Hz tone, finite nonzero PCM and
successful audout buffer completion. Bank mode additionally loads sample data,
resolves the selected event and records its PCM. These are fixture parameters,
not captured results. Buffer completion and PCM checks are not an acoustic test.

The Android ABI adapter maps only supported imports, implements current-thread
affinity and ordered priority changes through Horizon services, and fails
unsupported calls by name. It does not supply a general Bionic or Java VM;
JNI implements only the library's bounded initialization surface. Networking,
arbitrary Android services and broad filesystem/errno compatibility are outside
this fixture's contract.

Native mappings stay alive until process exit. The host selects libnx's
application process-exit mode instead of returning mapped-away source heap
pages to hbloader; dynamic native-module unloading is not implemented.
Check application exit separately: a DONE log marker alone is not an exit proof.

## Optional PCM and file-integrity checks

Copy the run's probe.log and float32 recordings into ignored artifacts/fmod-switch.
Keep them paired with their build and Linux reference. analyze-pcm.py checks
finite/nonzero PCM and the tone frequency; compare-pcm.py requires matching
sample counts and correlation above 0.9999. These thresholds stay in source;
do not replace them with assertions derived from a particular captured run.

verify.py combines these checks with exact version/API, NRO identity, expected
frame markers, buffer completion and an independent payload checksum report.
It accepts the [generic readback format](../fna-graphics/README.md#optional-file-integrity-report);
no particular transfer tool is required. For FMOD, the destinations are the
two payload/lib libraries and the selected payload/banks files.

For a read-only SD mount from a powered-off console, the following creates
that report from actual installed files. Replace the mount path; it never
modifies the card or performs deployment. Keep the card's payload unchanged
between the run and readback.

```sh
python3 - /path/to/mounted-sd <<'PY'
import hashlib, json, sys
from pathlib import Path
sd = Path(sys.argv[1]).resolve()
build = Path("artifacts/fmod-11014")
out = Path("artifacts/fmod-readback")
out.mkdir(parents=True, exist_ok=False)
manifest = json.loads((build / "build-manifest.json").read_text())
inputs = {"lib/" + name: manifest["sdk_files"]["android/" + name]
          for name in ("libfmod.so", "libfmodstudio.so")}
inputs.update({"banks/" + name: digest for name, digest in manifest["bank_sha256"].items()})
files, records = [], []
for relative, expected in sorted(inputs.items()):
    if len(Path(relative).parts) != 2 or ".." in Path(relative).parts:
        raise SystemExit("Unexpected payload path")
    local = build / "payload" / relative
    if hashlib.sha256(local.read_bytes()).hexdigest() != expected:
        raise SystemExit("Changed local payload: " + relative)
    installed = sd / "switch/celeste-fmod-11014" / relative
    observed = hashlib.sha256(installed.read_bytes()).hexdigest()
    if observed != expected:
        raise SystemExit("Installed file differs: " + relative)
    destination = "sdmc:/switch/celeste-fmod-11014/" + relative
    files.append({"destination": destination, "sha256": expected})
    records.append("VERIFIED existing " + observed + " " + destination)
identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
(out / "manifest.json").write_text(json.dumps({"id": identity, "files": files}, indent=2) + "\n")
lines = ["BEGIN payload deployment manifest=" + identity] + records
lines.append(f"END deployment verified={len(files)} copied=0 failures=0")
(out / "readback.txt").write_text("\n".join(lines) + "\n")
PY
python3 tests/fmod-11014/verify.py --build artifacts/fmod-11014 \
  --deployment-manifest artifacts/fmod-readback/manifest.json \
  --deployment-log artifacts/fmod-readback/readback.txt \
  --switch-log artifacts/fmod-switch/probe.log \
  --switch-pcm artifacts/fmod-switch --linux-pcm artifacts/fmod-linux \
  --output artifacts/fmod-verified.json
```

The readback report directory must be new. The verifier replaces --output if
present and runs the PCM analyzers; preserve needed output first.
File identity is not authentication or proof of where code executed.
Keep logs, SDK files, recordings, manifests and binaries outside source history.
This synchronous native fixture does not establish asynchronous game mixing,
managed callback integration or normal Everest Mods/ compatibility.

The Bionic/JNI/import implementation is shared from
[the native integration sources](../../native/fmod/README.md).
The standalone native fixture retains a 256 KiB minimum adapter-thread stack;
the [managed fixture](../fmod-managed/README.md) selects 1536 KiB for
CoreCLR callback threads and uses a separate asynchronous output plugin.
