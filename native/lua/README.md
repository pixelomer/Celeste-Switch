# Lua native dependency for KeraLua

This helper builds Lua 5.4.8 from the source revision paired with KeraLua 1.4.7.
It reads native import metadata from the selected managed KeraLua assembly and
requires every declared import to exist in the resulting static archive.
Import coverage alone does not establish runtime or managed-interop safety.

## Sources and toolchain

Use Linux, Git, Python 3 with dnfile, devkitPro devkitA64 tools on PATH and
the complete staged libnx SDK from the [host recipe](../../host/README.md).
Obtain a fresh source checkout from this repository root:

```sh
git clone https://github.com/NLua/KeraLua.git third_party/keralua
git -C third_party/keralua checkout --detach 20113b5267f18fdf9f153ba4acaed2c6c8d1d3e1
git -C third_party/keralua submodule update --init --recursive
```

The external/lua gitlink selects
995a493cbbcaadceab6b080cd23d8555e7747efa from
[NLua/lua](https://github.com/NLua/lua/tree/995a493cbbcaadceab6b080cd23d8555e7747efa).
Keep that source tree clean. Its include/lua.h identifies Lua 5.4.8 and
contains the copyright/MIT notice; retain notices with the copied source
and any distribution. KeraLua retains its own MIT license.

Use KeraLua.dll from the matching
[standard Everest preparation](../../tools/prepare-everest/README.md).
The pinned NLua project restores KeraLua package 1.4.7 through NuGet during
Everest publication; it is copied into the prepared install tree. The builder
inspects that actual assembly, not a hard-coded list of assumed imports.

## Build and integrate

After producing artifacts/everest-prepared/install, run from this repository root:

```sh
python3 native/lua/build.py \
  --source third_party/keralua/external/lua \
  --keralua artifacts/everest-prepared/install/KeraLua.dll \
  --libnx /path/to/staged/libnx --output artifacts/lua
```

The output directory must be new. The helper rejects another source revision
or a modified source tree, snapshots src/ and include/, and compiles library
translation units with the soft libnx TLS ABI. It excludes the Lua/luac
executables and the Android-specific source helper. The generic C configuration
does not enable Lua's POSIX process or dynamic-native-library backends.
It does not install over a system Lua or run any Lua code.

The output contains liblua54.a, sources, objects and manifest.json, including
the actual archive identity, source identities, supplied assembly imports,
exported symbols and compiler commands. These are generated artifacts.
The [application host](../../host/README.md#standard-everest-inputs)
accepts --lua-build artifacts/lua, verifies the archive digest, retains its
exports and resolves the ordinary lua54 P/Invoke name from the resident image.
Keep this archive paired with the managed KeraLua input used to check it.
Native Lua modules and unsupported OS services are not supplied by this link.

The root `build.py` fetches the exact NLua/lua source revision from
`sources.lock.json` and supplies the prepared KeraLua assembly automatically.
Independent use of this lower-level builder still accepts explicit source,
KeraLua, libnx SDK and output paths. The builder compares the selected assembly's
imports against native exports; that check does not establish runtime safety.
