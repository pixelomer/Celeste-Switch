# PC Celeste and Everest hosting requirements

A Horizon host must preserve dynamic managed loading and runtime hooks, not
just execute a closed set of ahead-of-time compiled assemblies. A Mono
interpreter with a runtime-aware hook backend is an alternative execution model;
mixed AOT requires the same hook semantics. The primary CoreCLR .NET 10 source
and its version-specific MonoMod requirements are described in
[runtime compatibility](RUNTIME_COMPATIBILITY.md).
See [compatibility checks](ROADMAP.md) for the independent contracts.

## Input conversion

The [input contract](../research/BASELINE.json) identifies the PC FNA baseline:
internal game version 1.4.0.0, .NET Framework 4.5.2 and FMOD 1.10.14.
The game assembly identity 1.0.0.0 is not the internal game version.
Convert framework references for the selected runtime and clear Required32Bit
on IL-only inputs when targeting ARM64. Native desktop libraries require ports
or adapters; a .dll suffix alone does not identify managed code.

The inventory commands in [README](../README.md) reproduce PE, CIL,
bank-container and FMOD ELF/header metadata without executing game code.
Do not transplant desktop Mono/System assemblies into another runtime version.

## Everest and runtime hooks

The [Everest source reference](https://github.com/EverestAPI/Everest/tree/47d6a61fa918c17b8085b93b61ee59a7465968f8)
targets .NET 8. Installation uses NETCoreifier and MonoMod; runtime mod
discovery, relinking, collectible assembly contexts, reflection, generated
delegates, On hooks and IL hooks remain requirements after installation.
Moving conversion to a host machine does not remove those runtime requirements.

[VanillaCoreifier](https://github.com/Wartori54/VanillaCoreifier/tree/813454c4453a90f3b9dd882e40b814e6646d1c1d)
delegates conversion to Everest's NETCoreifier, but its desktop apphost and
native-library packaging are not Horizon deployment outputs. Use explicit
pinned conversion inputs on a separate copy and preserve FMOD version identity.

The [Mono source integration](https://github.com/exelix11/mono-nx/tree/fec057748af9121d5cf363e772e817908d57c191)
provides a .NET 9 Mono interpreter configuration. Runtime, CoreLib/BCL and
cross-AOT compiler must be a coherent set. An ARM64 branch emitter does not
by itself make interpreted methods individually detourable. Hook ordering,
original calls, disposal, generic/virtual dispatch and cross-assembly callers
require runtime-aware handling. AOT direct calls and inlining can bypass hooks.

The Everest-pinned [MonoMod platform selector](https://github.com/MonoMod/MonoMod/blob/dfc30a1506d37fb88a2c2be004f525205f46a24c/src/MonoMod.Core/Platforms/PlatformTriple.cs)
does not provide a Horizon system backend. Executable allocations and detour
patches must respect writable/executable aliases, instruction-cache coherency,
permissions and concurrent execution. A Linux ARM64 runtime is not a Horizon
binary. Static-only deployment does not satisfy arbitrary new IL loading and
runtime code generation.

## Graphics, input and storage

Preserve FNA and Monocle types visible to mods. The native graphics chain is
FNA, FNA3D/MojoShader, SDL2/OpenGL and libnx. Select a coherent managed/native
pair rather than independently combining library heads.
The [FNA reference](https://github.com/FNA-XNA/FNA/tree/76b1aef1fd0fa913ac53726fab9d230291c15327)
supports SDL2 selection with FNA_PLATFORM_BACKEND=SDL2; the
[FNA3D reference](https://github.com/FNA-XNA/FNA3D/tree/77c8b26ad1d1576444e258b0d92fe10b7c975f95)
also requires explicit SDL2 build selection. These comparison revisions do not
constitute an application build recipe.

Cover render targets, SpriteBatch ordering, blend/scissor state, effect
translation, texture formats, device reset and presentation timing. Determine
whether FAudio and video imports are required by initialization or mods;
silent no-op exports do not preserve those APIs.

Define controller mappings, rumble, dead zones, reconnect and text input.
Provide explicit content/save/mod/cache paths and preserve Unicode names,
localization, atomic saves, zip streams and useful disk-full errors. Retain
reflection-visible game/mod metadata and avoid premature trimming.

## Exact FMOD 1.10.14 ABI

Use user-owned original banks and exact FMOD 1.10.14 runtime. Its output plugin
interface is API 3. FMOD 2 output structs and callbacks are not replacements.
Audit relocations, imports, TLS, allocator ownership, pthread/time/file
interfaces and JNI initialization for an Android ARM64 loader. Matching export
names alone is not an ABI or execution proof.

Preserve the FMOD API surface visible to game code and mods: event parameters,
buses, snapshots, streaming, timeline callbacks and bank lifetime. Keep callback
threading and buffer ownership correct through suspend/resume and shutdown.
Bank filenames and RIFF headers do not prove codec or event compatibility.
Local SDK access does not grant redistribution rights.

## Optional OS services

Keep unsupported process launch, browser, Discord, updater, filesystem watcher
and debug-server behavior explicit. HTTP/TLS, native plugins and desktop OS
dependencies require separate implementations; ordinary managed loading does
not imply support.
