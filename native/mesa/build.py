#!/usr/bin/env python3
"""Build the complete Celeste Mesa archive from checksum-pinned public sources."""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'eng/horizon'))
from support import digest, download, extract_tar, run
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', required=True, type=Path)
p.add_argument('--libnx', required=True, type=Path)
p.add_argument('--jobs', type=int, default=min(os.cpu_count() or 2, 8))
a = p.parse_args()
if a.jobs < 1: p.error('--jobs must be positive')
out = a.output.resolve(); sdk = a.libnx.resolve()
if out.exists(): p.error('Choose a new output directory')
out.mkdir(parents=True)
dkp = Path(os.environ.get('DEVKITPRO', '/opt/devkitpro')).resolve()
inputs = json.loads((HERE / 'sources.json').read_text())
for name, spec in inputs.items(): download(spec, out / name)
extract_tar(out / 'mesa-20.1.0-rc3.tar.xz', out)
source = out / 'mesa-20.1.0-rc3'
for name in list(inputs)[1:]: run(['patch', '--batch', '--fuzz=0', '-p1', '-i', out / name], cwd=source)
run([sys.executable, HERE / 'patch-mesa-thread.py', source])
run(['patch', '--batch', '--fuzz=0', '-p1', '-i', HERE / 'nouveau-mm-failure.patch'], cwd=source)
cross = subprocess.check_output([dkp / 'meson-toolchain.sh', 'switch'], text=True)
# Use the same headers as the linked runtime rather than a second installed libnx.
cross = cross.replace(str(dkp / 'libnx'), str(sdk))
(out / 'cross.ini').write_text(cross)
run(['meson', 'setup', '--buildtype=plain', '--cross-file=' + str(out / 'cross.ini'),
     '--default-library=static', '--prefix=' + str(out / 'install'), '--libdir=lib',
     out / 'build', source, '-Db_ndebug=true'])
run(['ninja', '-C', out / 'build', '-j' + str(a.jobs), 'src/egl/libEGL.a'])
shutil.copy2(out / 'build/src/egl/libEGL.a', out / 'libEGL.a')
(out / 'manifest.json').write_text(json.dumps({'inputs': inputs, 'libnx_sha256': digest(sdk / 'lib/libnx.a'),
    'archive_sha256': digest(out / 'libEGL.a'),
    'scripts': {f.name: digest(f) for f in HERE.iterdir() if f.is_file()}}, indent=2) + '\n')
print(out / 'libEGL.a')
