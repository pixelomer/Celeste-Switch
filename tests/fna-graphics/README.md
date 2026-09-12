# FNA graphics and lifecycle fixture

This original pattern/triangle fixture exercises paired FNA/FNA3D 24.01 with
Horizon CoreCLR .NET 10. It contains no game data, FMOD bytes or mod code.
Keep the managed and native dependency revisions together.

## Source prerequisites

Use Linux with Git, CMake, Ninja, Meson, GNU patch, Make, Python 3.12+,
Python Mako, dnfile, pyelftools and pefile, .NET SDK 10.0.111, and devkitPro's
devkitA64, switch-tools, libnx 4.10.0 or newer, SDL2, Mesa and libdrm/nouveau
portlibs. Mesa also needs devkitPro's meson-cross.sh/toolchain files
(dkp-meson-scripts), Bison and Flex. Set DEVKITPRO to the installation root;
the examples use /opt/devkitpro. Put its tools and devkitA64/bin on PATH.

From this repository root, use fresh ignored source directories:

```sh
git clone https://github.com/pixelomer/dotnet-runtime.git third_party/graphics-runtime
git -C third_party/graphics-runtime checkout --detach cc7840c0a34d73ec3badb1344da207be557b509d
git clone https://github.com/pixelomer/FNA.git third_party/graphics-fna
git -C third_party/graphics-fna checkout --detach fca2f21fa04fc5e066c47f26a0815c03569ab9fc
git -C third_party/graphics-fna submodule update --init --recursive
git clone https://github.com/pixelomer/SDL.git third_party/graphics-sdl
git -C third_party/graphics-sdl checkout --detach 667efdc462a4b993f79fccc58f786e72080b4fe3
git clone https://github.com/pixelomer/Celeste64-Switch.git third_party/graphics-mesa
git -C third_party/graphics-mesa checkout --detach 36848976a39ec97ffebcb303ea1428f1a727f980
```

The FNA gitlinks select FNA3D 036b4183d9cad8a75e8e011589dca09f13f0ff90 and its
MojoShader 2f7dda5f4e65423f546a9836139bcc418f2c5d33, including paired source
patches and the optional Vulkan build switch.
For the runtime, follow the pinned
[hosting profile](https://github.com/pixelomer/dotnet-runtime/blob/cc7840c0a34d73ec3badb1344da207be557b509d/docs/workflow/libnx-supported-profile.md)
and linked thread/host recipes. Build and stage its pinned libnx, native
CoreCLR, IL CoreLib, libs.sfx framework and source SDK, with source-built ICU.
Its native-library host option is required by this fixture.

The SDL helper needs the same staged libnx SDK identified by LIBNX_ROOT in
the runtime's CMakeCache.txt. After the runtime recipe, replace the SDK argument
below with that absolute staged directory (the one containing switch.specs):

```sh
python3 third_party/graphics-sdl/build-scripts/build-libnx.py \
  --libnx /path/to/staged/libnx --output artifacts/graphics-sdl
export DEVKITPRO=/opt/devkitpro
CELESTE64_MESA_LARGE_UPLOADS=1 python3 \
  third_party/graphics-mesa/src/celeste64-switch/renderer/build-mesa-thread.py --ensure
```

Use your actual DEVKITPRO value if different. The Mesa helper is standalone:
it downloads checksum-pinned Mesa/package patches and rebuilds the complete
archive with worker/newlib compatibility and large-upload support. It does
not fetch/build the other application or require its game/audio inputs.
It replaces its generated Mesa source and outputs under
third_party/graphics-mesa/artifacts/mesa-renderer-build, not the installed Mesa.
Preserve needed generated data before rebuilding; do not mix individual archive
members from different builds. The optional Mesa GL worker is not enabled by
this graphics fixture.

## Build the fixture

```sh
python3 tests/fna-graphics/build.py \
  --runtime third_party/graphics-runtime \
  --runtime-baseline third_party/graphics-runtime \
  --fna third_party/graphics-fna \
  --mesa-library third_party/graphics-mesa/artifacts/mesa-renderer-build/full-lib-large/libEGL.a \
  --sdl-library artifacts/graphics-sdl/libSDL2.a \
  --output artifacts/fna-graphics
```

The output directory must be new. The helper builds net8 FNA and static
FNA3D/MojoShader, inventories declared native imports and links the SDL2,
Mesa, glapi and nouveau archives into the runtime host. SDL2 headers and CMake
discovery still use devkitPro portlibs; install the matching SDL2 package even
when providing an explicit archive. It requires the runtime SDK/BCL/native
outputs in their documented build layouts. It does not deploy or run anything.

Only available resident SDL2/FNA3D symbols are exported. Android, Windows and
iOS imports are not thereby supported; no FAudio, Theorafile or FMOD is linked
by this graphics-only fixture. Missing runtime imports return failure, not
success stubs.

## Workload and log ownership

Install host/managed from the build under /switch/celeste-fna-probe on the
SD card and run celeste-fna-probe.nro in full application mode. Preserve any
existing destination files and logs first. The 75-second fixture requires
controller discovery, the south face button (XNA logical A), HOME and resume.
It draws colored quadrants, a magenta triangle and a bar that becomes green
after input. It also asserts texture/render-target pixel values, SpriteBatch
orientation, alpha/scissor behavior, BasicEffect and GL error state, and
requests collections while drawing. These are workload constants, not results.

The native adapter requests SuspendHomeSleepNotify and Resume messages.
Native Resume is a separate assertion from FNA Activated/Deactivated: focus
events depend on the state actually reported by Horizon. Do not synthesize
focus changes or interpret a frame count as a game benchmark.

The application writes /switch/celeste-fna-probe.txt,
 /switch/celeste-fna-stdout.txt and /switch/celeste-fna-stderr.txt.
Store them under an ignored log directory as runtime.txt, stdout.txt and
stderr.txt. Success requires all 21 assertions, the OpenGL backend, controller
input and Resume, empty stderr, and successful execute/shutdown exit 100.
This does not cover arbitrary mod effects, audio or full game/mod compatibility.

## Optional file-integrity report

verify.py additionally accepts a JSON manifest with an id and files entries
containing destination and sha256, and a matching per-file readback transcript.
The transcript records BEGIN payload deployment manifest=ID, one
VERIFIED existing HASH DESTINATION line per existing file, and an END summary.
It is a checksum data format; it does not require a particular transfer utility.
Only report hashes independently read from the installed files.

For example, with the SD card safely removed from the powered-off console
and mounted read-only on the host, the following reads its files and creates
a new ignored report directory. It never modifies the SD card. Replace the
mount path; keep this card's files unchanged between the run and readback.

```sh
python3 - /path/to/mounted-sd <<'PY'
import hashlib, json, sys
from pathlib import Path
sd = Path(sys.argv[1]).resolve()
build = Path("artifacts/fna-graphics")
out = Path("artifacts/fna-graphics-readback")
out.mkdir(parents=True, exist_ok=False)
manifest = json.loads((build / "host/build-manifest.json").read_text())
directory = manifest["managed_directory"]
if directory != "/switch/celeste-fna-probe":
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
python3 tests/fna-graphics/verify.py --lifecycle \
  --build artifacts/fna-graphics --logs artifacts/fna-graphics-logs \
  --deployment-manifest artifacts/fna-graphics-readback/manifest.json \
  --deployment-log artifacts/fna-graphics-readback/readback.txt \
  --output artifacts/fna-graphics-verified.json
```

The verifier compares every installed digest against the build manifest as
well as checking the runtime logs. It replaces its --output JSON if present.
A checksum match is not authentication or proof of arbitrary runtime behavior;
host-side card readback does not attest to where code executed. Keep all
reports, screenshots and binaries outside source history.
