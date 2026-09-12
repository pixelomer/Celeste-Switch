# Stage user-owned PC content

From this repository root, use Python 3.11 or newer and your supported
PC Linux distribution ZIP with Content/ at its archive root:

```sh
python3 tools/stage-content/stage.py local/celeste-linux.zip artifacts/pc-content
```

The output directory must be new. Only Content/ files are extracted.
The helper rejects traversal, symlinks, case collisions, oversized inputs
and truncated extraction. It creates content-manifest.json with the input
archive identity, per-file SHA-256 values, sizes and counts.
It does not execute archive contents, deploy files or modify the original ZIP.

Keep the ZIP, extracted copyrighted assets and generated manifest under
ignored local/ or artifacts/ directories. Do not distribute them in Git or
release assets. This helper supplies content for later application packaging;
it does not prepare managed assemblies, native audio libraries or saves.
See the [input contract](../../research/BASELINE.json) and
[assembly conversion recipe](../coreify/README.md).
