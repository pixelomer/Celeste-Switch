# Compatibility checks

These are acceptance criteria, not captured results. Use original small
fixtures with explicit expected values before introducing user-owned game
input. Keep generated logs and inventories in ignored artifacts/.

## Managed execution and hooks

Use a coherent runtime/BCL and pinned hook dependency set.

- Load a second assembly from files and bytes; exercise generic and virtual
  calls, exceptions and collections under allocation pressure.
- Check shared dependency identity, version isolation, useful resolution errors
  and collectible unload/reload without retaining rooted state.
- Execute DynamicMethod and generated types/delegates across collections.
- Round-trip scalar, struct, string, array and pointer interop; attach native
  callback threads correctly and preserve callback lifetime.
- Exercise writable/executable aliases, cache flush and repeated allocation.
- Chain ordered Hook handlers with original calls; undo/dispose must restore
  behavior. ILHook must alter and restore constants and control flow.
- Cover delegates, generic/virtual and cross-assembly calls, coroutine state
  machines and concurrent execution during hook creation/disposal.
- Compare interpreted and AOT dispatch before using mixed compilation.

## Native libraries and storage

For FNA/FNA3D, use a coherent SDL2/OpenGL build and a known SpriteBatch scene
with render targets, alpha blending, scissor, effects and texture readback.
Cover controller changes, suspend/resume and display transitions. Exercise
imports through the selected managed runtime; declare unsupported audio/video
APIs rather than silently replacing their effects.

For FMOD 1.10.14 output API 3, start with a synthetic tone, then user-owned
banks. Reject unsupported imports by name and retain exact version checks.
Cover streaming, event parameters, buses, snapshots, timeline callbacks,
strings banks, unload/reload, headphones and suspend/resume. Copyrighted
audio output remains outside source history.

For filesystem/runtime services, cover zip mod streaming, Unicode and path
case/separators, serializers, atomic save recovery, cache invalidation,
disk exhaustion and thread cancellation. Reflective serialization requires
mod-like types; trimming must preserve required metadata.

## Application compatibility

Preserve vanilla gameplay timing, controls, chapter transitions, save/load,
localization and audio. Cover content-only mods, helper entities/triggers,
On/IL hooks, reflection, custom banks and shaders through normal Mods/ loading.
Document dependencies and unsupported native/OS features. A fixed injected mod
collection is not general mod discovery.

Assess managed/native memory, collections, storage, rendering and audio together;
a frame cap alone does not demonstrate execution headroom.
Installation must keep original and converted files separate, protect saves
and use pinned source inputs with clear redistribution requirements.
