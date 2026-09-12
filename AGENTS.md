# Celeste-Switch development

Read README.md and docs/BUILDING.md before changing the build.
Document source inputs and implementation contracts; keep work journals and
captured validation records outside source history.
Keep this repository self-contained; use the pinned public dependency sources
and user-supplied local game/audio inputs. Generated data belongs in ignored
artifacts/. Do not modify unrelated working trees to build this project.

The primary runtime is the coordinated .NET 10 CoreCLR/RyuJIT port. Mods must
load normally from Mods/, without a fixed injected mod pack. Preserve mod-visible APIs and explicitly record unsupported OS APIs.

The supported PC baseline internally reports 1.4.0.0 and uses FMOD 1.10.14.
Never substitute FMOD 2 or 1.10.20. Do not commit game implementations/assets,
FMOD SDK material, keys, credentials, Nintendo SDK files or proprietary
repackaged/decompiled derivatives. Retain third-party source origins/licenses.

Keep validation scopes distinct: desktop checks do not establish target behavior.
Retain symbols, maps, source pins and runtime/framework identity when testing.
Use libnx 4.10.0 or newer for Horizon 21+ TLS compatibility. Do not deploy to or
control a console as part of a source-build or packaging command.
