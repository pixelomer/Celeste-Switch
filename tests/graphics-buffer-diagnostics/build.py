#!/usr/bin/env python3
"""Replace one Mesa object in a copied archive using its recorded compile command.

Never edits the original Mesa source tree, objects, or Celeste64 archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--mesa-build', type=Path, required=True)
p.add_argument('--mesa-library', type=Path, required=True)
p.add_argument('--libnx', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
entries = json.loads((a.mesa_build / 'compile_commands.json').read_text())
entry, = [x for x in entries if x['file'].endswith('/util/u_transfer.c')]
cwd = Path(entry['directory'])
source = (cwd / entry['file']).resolve()
text = source.read_text()
needle = '   memcpy(map, data, size);'
if text.count(needle) != 1: raise SystemExit('Unexpected Mesa buffer upload source')
text = text.replace('void u_default_buffer_subdata(', '#include "check.h"\n\nvoid u_default_buffer_subdata(', 1)
text = text.replace(needle, '   check_buffer_mapping(pipe, resource, transfer, map, offset, size, usage, data);\n' + needle)
modified = out / 'u_transfer.c'; modified.write_text(text)
shutil.copy2(Path(__file__).with_name('check.h'), out / 'check.h')
object_file = out / 'util_u_transfer.c.o'
original = shlex.split(entry['command'])
command = []
skip = False
for item in original:
    if skip: skip = False; continue
    if item in ('-o', '-MF', '-MQ'): skip = True; continue
    if item in ('-MD', '-c', entry['file']): continue
    command.append(item)
command += ['-I' + str(a.libnx.resolve() / 'include'), '-g', '-fno-omit-frame-pointer', '-c', str(modified), '-o', str(object_file)]
subprocess.run(command, cwd=cwd, check=True)
archive = out / 'libEGL.a'; shutil.copy2(a.mesa_library, archive)
members = subprocess.check_output(['aarch64-none-elf-ar', 't', str(archive)], text=True).splitlines()
if members.count(object_file.name) != 1: raise SystemExit('Expected one target archive member')
subprocess.run(['aarch64-none-elf-ar', 'r', str(archive), str(object_file)], check=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
(out / 'manifest.json').write_text(json.dumps(dict(command=command, cwd=str(cwd),
    original_source_sha256=sha(source), modified_source_sha256=sha(modified),
    diagnostic_sha256=sha(out / 'check.h'), libnx_sha256=sha(a.libnx / 'lib/libnx.a'),
    original_archive_sha256=sha(a.mesa_library), archive_sha256=sha(archive)), indent=2) + '\n')
print(archive)
