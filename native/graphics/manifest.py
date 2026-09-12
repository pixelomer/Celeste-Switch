#!/usr/bin/env python3
"""Validate and describe source-built graphics inputs for the Celeste host."""
import argparse, json, os, subprocess, sys
from pathlib import Path
import dnfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'eng/horizon'))
from support import digest
p = argparse.ArgumentParser(description=__doc__)
for name in ['fna', 'fna3d-build', 'sdl-build', 'mesa-library', 'output']: p.add_argument('--' + name, required=True, type=Path)
a = p.parse_args()
port = Path(os.environ.get('DEVKITPRO', '/opt/devkitpro')) / 'portlibs/switch'
archives = [a.fna3d_build / 'libFNA3D.a', a.fna3d_build / 'libmojoshader.a',
            a.sdl_build / 'libSDL2.a', a.mesa_library, port / 'lib/libglapi.a', port / 'lib/libdrm_nouveau.a']
provided = set()
for archive in archives[:3]:
    for line in subprocess.check_output(['aarch64-none-elf-nm', '-g', '--defined-only', archive], text=True).splitlines():
        if len(line.split()) == 3: provided.add(line.split()[-1])
pe = dnfile.dnPE(str(a.fna)); imports = {}
for row in pe.net.mdtables.ImplMap.rows: imports.setdefault(str(row.ImportScope.row.Name), set()).add(str(row.ImportName))
pe.close()
requested = set.union(*(v for k, v in imports.items() if k in ['SDL2', 'FNA3D']))
# FNA declares optional desktop/newer SDL calls too; record those explicitly.
out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
(out / 'imports.json').write_text(json.dumps({'declared': {k: sorted(v) for k, v in imports.items()},
    'resident_exports': sorted(requested & provided), 'unavailable_graphics_imports': sorted(requested - provided)}, indent=2) + '\n')
(out / 'manifest.json').write_text(json.dumps({'fna_sha256': digest(a.fna),
    'native_libraries': {str(f.resolve()): digest(f) for f in archives}}, indent=2) + '\n')
