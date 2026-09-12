# Source and distribution notices

Third-party source keeps its own notices and licenses. This repository
does not grant rights to the commercial Celeste game or FMOD SDK/libraries.

| Component | Source and license |
| --- | --- |
| Horizon runtime | [dotnet-runtime](https://github.com/pixelomer/dotnet-runtime); dotnet/runtime MIT and third-party notices |
| Runtime build integration | [dotnet-switch](https://github.com/pixelomer/dotnet-switch) |
| libnx | [libnx](https://github.com/pixelomer/libnx), public switchbrew/libnx lineage, ISC |
| Everest / NETCoreifier / MiniInstaller | [Everest](https://github.com/pixelomer/Everest), EverestAPI upstream MIT |
| MonoMod and iced | [MonoMod](https://github.com/pixelomer/MonoMod); MonoMod and icedland upstream MIT |
| FNA | [FNA](https://github.com/pixelomer/FNA), upstream FNA-XNA licenses/LICENSE and bundled notices |
| FNA3D and MojoShader | [FNA3D](https://github.com/pixelomer/FNA3D) and [MojoShader](https://github.com/pixelomer/MojoShader), zlib |
| SDL2 | [SDL](https://github.com/pixelomer/SDL), devkitPro/SDL homebrew fork, zlib |
| Mesa | archive.mesa3d.org 20.1.0-rc3, upstream per-file MIT/other notices; checksum-pinned devkitPro package patches |
| Mesa GL worker patch | Original homebrew work retained from [Celeste64-Switch](https://github.com/pixelomer/Celeste64-Switch); see native/mesa/README.md |
| Lua | NLua/lua source pin matching KeraLua, MIT; native/lua/README.md |
| Android ELF loader | NaGaa95/hl2_nx at 41e045ea275fcfae906009f165a6635725e9a08f, MIT; source/so_util.c and .h only |
| FMOD | User-supplied Android ARM64 SDK 1.10.14, proprietary Firelight Technologies license; no SDK bytes included here |
| Celeste PC FNA | User-owned supported PC distribution; no game implementation/asset distribution license is provided |

Exact Git pins are in sources.lock.json and dependency submodules/manifests.
Native libraries supplied by devkitPro portlibs retain their installed package
licenses. Preserve corresponding dependency license files and source offers when
redistributing binaries. NuGet dependency notices remain with their packages.
Upstream Everest retains stripped compilation references and its desktop support
submodule. Do not replace stripped references in Git with original game binaries.

The locally generated SD ZIP includes the user's game content, patched game
assemblies and FMOD libraries. It is an installation output, not a public release
asset. Preserve the notices for any third-party dependencies distributed separately. No leaked Nintendo SDK, proprietary decompilation
or repackaged derivative is a source input to this port.
