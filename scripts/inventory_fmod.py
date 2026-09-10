#!/usr/bin/env python3
"""Read native ABI metadata from local FMOD 1.10.x SDKs; never load their code.

No headers, library bytes, bank data, or credentials are written to the report.
Requires pyelftools. FMOD 2 archives are deliberately rejected.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

from elftools.elf.elffile import ELFFile


def inspect(path):
    match = re.fullmatch(r'fmodstudioapi(110\d\d)(android|linux)\.tar\.gz', path.name)
    if not match:
        raise ValueError('Only FMOD 1.10.x Linux/Android SDK filenames are accepted')
    platform = match[2]
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'archive': path.name, 'sha256': digest, 'platform': platform,
              'header_constants': {}, 'libraries': {}}
    with tarfile.open(path) as archive:
        for member in archive:
            if not member.isfile():
                continue
            name = member.name
            header = name.endswith(('fmod_common.h', 'fmod_output.h'))
            native = ('/arm64-v8a/' in name if platform == 'android' else '/x86_64/' in name)
            native = native and re.search(r'/libfmod(?:studio)?\.so(?:\.\d+)*$', name)
            if not header and not native:
                continue
            if member.size > 32 * 1024 * 1024:
                raise ValueError(f'Unexpectedly large SDK member: {name}')
            data = archive.extractfile(member).read()
            if header:
                result['header_constants'][Path(name).name] = dict(re.findall(
                    r'^\s*#define\s+(FMOD_(?:VERSION|OUTPUT_PLUGIN_VERSION))\s+(\w+)',
                    data.decode(), re.MULTILINE))
                continue
            elf = ELFFile(io.BytesIO(data))
            dynamic = elf.get_section_by_name('.dynamic')
            symbols = list(elf.get_section_by_name('.dynsym').iter_symbols())
            result['libraries'][Path(name).name] = {
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                'machine': elf.header['e_machine'],
                'needed': [t.needed for t in dynamic.iter_tags() if t.entry.d_tag == 'DT_NEEDED'],
                'undefined': sorted({s.name for s in symbols if s.name and s.entry.st_shndx == 'SHN_UNDEF'}),
                'fmod_exports': sorted({s.name for s in symbols if s.name.startswith('FMOD_') and s.entry.st_shndx != 'SHN_UNDEF'}),
                'has_jni_onload': any(s.name == 'JNI_OnLoad' and s.entry.st_shndx != 'SHN_UNDEF' for s in symbols),
            }
    expected = '0x000' + match[1]
    if result['header_constants'].get('fmod_common.h', {}).get('FMOD_VERSION') != expected:
        raise ValueError('SDK filename and header version disagree')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', nargs='+', type=Path)
    args = parser.parse_args()
    print(json.dumps({'schema': 1, 'method': 'static ELF/header inspection; no execution',
                      'archives': [inspect(path) for path in args.archives]}, indent=2))


if __name__ == '__main__':
    main()
