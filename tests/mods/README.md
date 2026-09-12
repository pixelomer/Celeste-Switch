# Ordinary mod compatibility

Use unchanged mod ZIPs through normal Everest loading. Mods are optional inputs,
not required built-in game content. Do not inject, rewrite or source-port a fixed
package collection as part of host preparation.

## Obtain and inspect packages

Obtain packages from their original sources. Review each package's declared
dependencies, version requirements, native components and redistribution terms.
Keep downloaded archives, inventories and generated output outside source
history. Public availability alone does not establish redistribution rights.

Package metadata inspection is not the loader's complete compatibility
decision; optional dependencies and installed built-in versions need separate
review. An archive checksum or absence of native imports does not establish
safety or runtime compatibility.

## Ordinary loading and observable behavior

Prepare the [standard Everest host](../../host/README.md#standard-everest-inputs)
and preserve its existing Mods/, settings and saves before changing inputs.
Install packages through ordinary ZIP loading, including their required
dependencies. Assess packages individually before checking combinations.

Inspect module loading, visible behavior, hooks, rendering, settings persistence,
save/reload and restoration of changed options. Preserve unrelated packages and
settings; use the loader's ordinary configuration when isolation is necessary.
A title screen, successful build or zero native exit does not establish complete
gameplay compatibility.

For ordinary release versions, Everest requires the same major dependency
version and at least the requested remaining version components. An installed
0.0.* version is treated as a development build for comparison; this is not
proof that every requested API is present. Review optional integrations and
unsupported native/OS services separately.

Keep logs, screenshots, runtime observations and inventories outside source
history.
