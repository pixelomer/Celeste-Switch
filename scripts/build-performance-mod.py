#!/usr/bin/env python3
"""Build only the original diagnostic mod; game references remain local inputs."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--install', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
source = root/'src/SwitchPerformance'
install = a.install.resolve()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
command = ['dotnet', 'build', str(source/'SwitchPerformance.csproj'), '-c', 'Release',
           '-p:PreparedInstall='+str(install), '--artifacts-path', str(out)]
subprocess.run(command, check=True)
files = {'SwitchPerformance.dll': out/'bin/SwitchPerformance/release/SwitchPerformance.dll',
         'everest.yaml': source/'everest.yaml'}
deploy = out/'deploy'; deploy.mkdir()
archive = deploy/'000-SwitchPerformance.zip'
with zipfile.ZipFile(archive, 'w') as z:
    for name, path in files.items():
        entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(entry, path.read_bytes())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {'command': command, 'zip_sha256': digest(archive),
            'files': {name: digest(path) for name, path in files.items()},
            'references': {name: digest(install/name) for name in
                           ['Celeste.dll', 'FNA.dll', 'MonoMod.RuntimeDetour.dll']},
            'source_sha256': {path.name: digest(path) for path in source.iterdir() if path.is_file()}}
(out/'package.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(archive)
