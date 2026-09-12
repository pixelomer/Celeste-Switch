# Focused source fixtures

These original fixtures document their source inputs and assertions in individual
READMEs. Generated outputs and observations stay outside Git. Do not commit game
implementations, proprietary libraries or assets as fixture data.

Use the [automatic source pipeline](../docs/BUILDING.md) and sources.lock.json
for a complete installation. Lower-level fixture recipes select their own
explicit producer revisions and must keep paired assemblies/frameworks together.
Checks consuming game assemblies require the unprivileged isolation described
by their guides.

The Horizon source-fetch and content/output-boundary fixtures use miniature
original repositories and ZIPs. Build/package or desktop fixture success does
not establish target startup, rendering, audio, ordinary mod behavior or save
compatibility; assess those contracts separately.
