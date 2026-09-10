# PC Celeste and Everest on Horizon

This repository contains source tools and compatibility requirements for an
independent homebrew host of the PC FNA version of Celeste and Everest.
The metadata tools do not implement a playable port.

See [hosting requirements](docs/FEASIBILITY.md) and
[compatibility checks](docs/ROADMAP.md).
The [input contract](research/BASELINE.json) identifies supported PC assemblies;
[source references](research/upstreams.lock.json) pin comparison sources,
not a complete application build.

## User-owned inputs and read-only inventories

Use the PC FNA distribution with internal game version 1.4.0.0 and its
FMOD 1.10.14 bindings. Supply your own Linux or Windows OpenGL game ZIP from
your licensed game distribution. Obtain exact FMOD 1.10.14 Linux/Android SDKs
through FMOD's authorized download service or support. SDK access and
redistribution permission are separate requirements. Do not substitute
FMOD 1.10.20 or FMOD 2.

Install Python 3.11+ and the pinned Python dependencies. From the repository
root, replacing the example paths with your own inputs:

```sh
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
mkdir -p artifacts
.venv/bin/python scripts/inventory_pc.py \
  /path/to/celeste-linux.zip /path/to/celeste-win-opengl.zip \
  > artifacts/pc-inventory.json
.venv/bin/python scripts/inventory_fmod.py \
  /path/to/fmodstudioapi11014android.tar.gz \
  /path/to/fmodstudioapi11014linux.tar.gz > artifacts/fmod-inventory.json
```

The tools read archive members in memory without extracting or executing their
code. They distinguish native PE files from managed assemblies and report
binding/import metadata. Declarations are not a reachability proof. The FMOD
tool accepts 1.10.x filenames and verifies their header version; select exactly
1.10.14 for this input contract. Generated reports belong in ignored artifacts/.

## Obtain pinned comparison sources

With Git and Python installed, run this from the repository root. It creates a
new ignored source directory and refuses to reuse an existing one. It checks
out exact revisions without initializing unrelated submodules.

```sh
python3 - <<'PY'
import json
from pathlib import Path
import subprocess
root = Path("third_party/upstream")
root.mkdir(parents=True, exist_ok=False)
for entry in json.loads(Path("research/upstreams.lock.json").read_text())["repositories"]:
    target = root / entry["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--no-checkout", entry["url"], str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "checkout", "--detach", entry["commit"]], check=True)
PY
python3 scripts/check_sources.py third_party/upstream
```

The checker reports missing trees, revision drift and tracked changes; it does
not fetch, reset, build or execute the referenced projects. These comparison
sources are not a substitute for a matched runtime, BCL and native-library build.

## Source and output ownership

Original implementation belongs in src/, fixtures in tests/, portable tools in
scripts/, input contracts and source pins in research/, and guides in docs/.
Generated outputs belong in ignored artifacts/ or local/.

Preparation of a user's game must use a separate copy and preserve saves.
Do not commit or distribute game implementations, decompiled/patched assemblies,
assets, banks, FMOD SDK files, proprietary platform SDK material or credentials.
Preserve third-party licenses and source origins.
