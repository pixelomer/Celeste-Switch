# Installing and using the port

Build the local installation using [BUILDING.md](BUILDING.md). A supported
user-owned PC FNA game ZIP and exact FMOD 1.10.14 Android SDK are required.
The resulting ZIP includes those private inputs; do not redistribute it.

1. Back up any existing `switch/celeste-pc/` folder on your SD card, especially
   `Saves/`, `Mods/` and configuration files.
2. Copy the contents of `package/sdcard/` to the SD root. Keep game files under
   `switch/celeste-pc/`; this is the host's application/content/save path.
3. Launch `celeste-pc.nro` through a full-memory homebrew application context
   supported by your Atmosphere setup. Album/applet mode does not provide the
   required memory. This guide assumes working homebrew; it does not install CFW.
4. Let Everest finish loading. Large mod sets can take several minutes. Consult
   the log files in `switch/celeste-pc/` before treating a slow startup as a hang.
5. Add compatible, ordinary mod ZIPs to `switch/celeste-pc/Mods/`, including the
   dependencies listed by each mod. Restart the game after changing the mod set.

Install ZIPs individually or use your usual trusted PC mod download workflow;
the Switch port does not require a PC-precompiled or injected mod pack. Test a
small set before installing a large collection. Mods
requiring Windows APIs, desktop native libraries, external processes or other
unimplemented OS services may be incompatible. Use the
[ordinary mod guide](../tests/mods/README.md) for dependency and acceptance checks.

The included removable `000-SwitchPerformance.zip` enables checksum buffering
by default for new settings, with diagnostics off. Omit the mod at build time,
disable it through ordinary mod configuration, or set BufferChecksums=false to
opt out. Larger read requests are observable to other hooks; they do not
establish a throughput or gameplay frame-rate guarantee.

Controller labels originate from the PC/Xbox layout. Use the game's controller
binding menu to choose your preferred Switch buttons. Builds do not change
CPU/GPU clocks. Preserve existing settings and save slots during configuration.

If updating an existing installation, retain your saves and mod settings. The
packager never reads console saves and never overwrites an existing output
folder. Use matching NRO, runtime/framework and prepared assemblies from one
build; mixing versions can produce misleading loader/hook failures. Keep the
installation manifest and build logs when reporting an issue.
