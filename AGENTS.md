# Celeste-Switch development

Read README.md and the relevant technical guides before editing this project.
Keep source tools and instructions self-contained, with pinned public
dependencies and clearly identified user-owned game/audio inputs.

Original sources belong in src/ and focused fixtures in tests/. Keep generated
reports, binaries and local inputs in ignored directories. Do not commit game
implementations, decompiled or patched assemblies, assets, FMOD SDK material,
proprietary platform SDK files, keys or credentials. Retain third-party notices.

The PC input contract uses internal game version 1.4.0.0 and FMOD 1.10.14.
Never silently substitute FMOD 1.10.20 or FMOD 2. Metadata inspection must not
execute inspected binaries.

Keep runtime, BCL, framework and MonoMod versions coherent. Preserve mod-visible
APIs, dynamic loading and hook semantics; a fixed precompiled mod pack is not
general Everest support. Mods must load normally from Mods/. Windows/native-specific limitations and unsupported OS APIs must be explicit.
Use devkitA64 and libnx 4.10.0 or newer for Horizon 21+ TLS compatibility.
Source-build and packaging commands must not deploy to or control a console.
