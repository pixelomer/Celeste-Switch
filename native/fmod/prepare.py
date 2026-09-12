#!/usr/bin/env python3
"""Prepare the exact user-supplied FMOD 1.10.14 Android ARM64 SDK and loader sources."""
import argparse, hashlib, json, re, shutil, subprocess, sys, tarfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'eng/horizon'))
from support import digest, git_source, read_mirrors
from fmod_imports import generate_imports
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
p.add_argument('--source-mirrors', type=Path)
a = p.parse_args()
expected = 'e374d9d4e189281d3a24b6459614df48a24b9816c829fded449ec14b7b0baccb'
if digest(a.archive) != expected: p.error('Expected the exact FMOD 1.10.14 Android SDK archive; other versions are incompatible')
out = a.output.resolve()
if out.exists(): p.error('Choose a new output directory')
out.mkdir(parents=True)
sdk = out / 'sdk'; sdk.mkdir()
with tarfile.open(a.archive) as archive:
    for member in archive:
        if not member.isfile(): continue
        header = ('/api/lowlevel/inc/' in member.name or '/api/studio/inc/' in member.name) and member.name.endswith('.h')
        library = '/arm64-v8a/' in member.name and re.search(r'/libfmod(?:studio)?\.so$', member.name)
        if not (header or library): continue
        if member.size > 32 * 1024 * 1024: raise SystemExit('Oversized SDK member')
        dest = sdk / ('inc' if header else 'android') / Path(member.name).name
        dest.parent.mkdir(exist_ok=True)
        with dest.open('xb') as stream: shutil.copyfileobj(archive.extractfile(member), stream)
if not re.search(r'#define\s+FMOD_VERSION\s+0x00011014\b', (sdk / 'inc/fmod_common.h').read_text()): raise SystemExit('Wrong FMOD header version')
if not re.search(r'#define\s+FMOD_OUTPUT_PLUGIN_VERSION\s+3\b', (sdk / 'inc/fmod_output.h').read_text()): raise SystemExit('Wrong output ABI')
spec = {'url': 'https://github.com/NaGaa95/hl2_nx.git', 'revision': '41e045ea275fcfae906009f165a6635725e9a08f'}
loader = git_source(spec, out / 'loader', read_mirrors(a.source_mirrors))
s = (loader / 'source/so_util.c').read_text().replace('#include "config.h"', '').replace('#include "util.h"', 'int debugPrintf(const char*,...);').replace('#include "error.h"', 'void fatal_error(const char*,...) __attribute__((noreturn));')
s = s.replace('envGetOwnProcessHandle()', 'probeProcessHandle()').replace('#include <switch.h>', '#include <switch.h>\nHandle probeProcessHandle(void);')
needle = '  return 0;\n}\n\nvoid so_execute_init_array'
if s.count(needle) != 1: raise SystemExit('Loader fail-fast patch mismatch')
s = s.replace(needle, '  return missing;\n}\n\nvoid so_execute_init_array')
(out / 'so_util.c').write_text(s)
shutil.copy2(loader / 'source/so_util.h', out / 'so_util.h')
unknown = generate_imports(sdk, out, True)
(out / 'build-manifest.json').write_text(json.dumps({'fmod_version': '1.10.14', 'output_api': 3,
    'archive_sha256': expected, 'loader': spec, 'unsupported_android_imports': unknown,
    'sdk_files': {str(f.relative_to(sdk)): digest(f) for f in sdk.rglob('*') if f.is_file()}}, indent=2) + '\n')
print(out)
