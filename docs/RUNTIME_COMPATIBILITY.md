# .NET 10 hosting and mod compatibility

The primary runtime source is the
[Horizon CoreCLR port](https://github.com/pixelomer/dotnet-runtime/tree/0159e182f138395199d3dc113171276563a57e57),
based on public .NET 10.0.12 revision
4271d88e0aebf3d04f188f1334c2220d80555ef6.
Its [supported profile and build guide](https://github.com/pixelomer/dotnet-runtime/blob/0159e182f138395199d3dc113171276563a57e57/docs/workflow/libnx-supported-profile.md)
defines source acquisition, build inputs, embedding and limitations.
Keep the runtime and CoreLib/BCL paired. FNA/FNA3D and exact FMOD 1.10.14
are separate integration requirements.

## Target framework and runtime version

The [Everest reference](https://github.com/EverestAPI/Everest/blob/47d6a61fa918c17b8085b93b61ee59a7465968f8/Celeste.Mod.mm/Celeste.Mod.mm.csproj)
targets net8.0. A library's target framework describes its build API contract;
it does not select a separate CLR inside an embedding host. Compatible net8
and net9 IL libraries can use a .NET 10 host, but removed APIs, native inputs,
changed behavior and private runtime dependencies need individual checking.

This host embeds one selected CoreCLR. AssemblyLoadContext isolates assembly
loading, not CLR versions. Preserve shared Celeste/FNA/Everest type identity,
dependency resolution, relinking and collectible lifetime. Do not mix .NET 8
runtime internals with the .NET 10 BCL. Desktop host roll-forward configuration
is a separate concern from embedded-host compatibility.

The original .NET Framework 4.5.2 input requires Coreification and correction
of Required32Bit flags; older mods may need Everest's relinker. Runtime and
application inputs must follow the port's IL-only contract: foreign ReadyToRun
fallback is unsupported. Native desktop dependencies still require Horizon
builds or adapters.

## MonoMod's version-specific ABI

Everest pins MonoMod dfc30a1506d37fb88a2c2be004f525205f46a24c.
Its [CoreBaseRuntime selection](https://github.com/MonoMod/MonoMod/blob/dfc30a1506d37fb88a2c2be004f525205f46a24c/src/MonoMod.Core/Platforms/Runtimes/CoreBaseRuntime.cs)
has cases through .NET 9 and rejects .NET 10.

The separate reference 14b9f28a04f9281fb032cb1d1e2339305b734869 has a
[Core100Runtime adapter](https://github.com/MonoMod/MonoMod/blob/14b9f28a04f9281fb032cb1d1e2339305b734869/src/MonoMod.Core/Platforms/Runtimes/Core100Runtime.cs)
with expected JIT GUID 7a8cbc56-9e19-4321-80b9-a0d2c578c945.
GUID agreement is necessary, not sufficient: private fields and JIT vtable
layouts must also match. Both comparison references lack a Horizon system
backend, and shared-library discovery of clrjit must account for the embedded
static JIT.

Use a compatible MonoMod dependency set or port the needed adapter while
preserving HookGen, Utils, RuntimeDetour and patcher API compatibility.
Hooking additionally requires executable allocation, cache coherency, method
patching, recompilation notifications, ordered original calls and disposal.
See [focused compatibility checks](ROADMAP.md) for generated delegates,
generic/virtual dispatch, concurrent hooks, collections and unload/reload.
