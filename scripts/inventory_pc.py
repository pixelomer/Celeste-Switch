#!/usr/bin/env python3
"""Inspect PC ZIP metadata without executing or extracting game code.

Writes JSON to stdout. Requires dnfile. Member references are candidates, not a
reachability analysis. Native PE files are explicitly distinguished from CIL.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import zipfile

import dnfile


def version(row):
    return '.'.join(str(getattr(row, k)) for k in
                    ('MajorVersion', 'MinorVersion', 'BuildNumber', 'RevisionNumber'))


def assembly(data):
    pe = dnfile.dnPE(data=data)
    try:
        if not pe.net:
            return {'kind': 'native PE', 'machine': hex(pe.FILE_HEADER.Machine)}
        tables = pe.net.mdtables
        rows = lambda name: getattr(tables, name).rows if getattr(tables, name) else []
        imports = [{'library': str(r.ImportScope.row.Name), 'entry': str(r.ImportName)}
                   for r in rows('ImplMap')]
        fmod_version = None
        for row in rows('TypeDef'):
            if str(row.TypeNamespace) == 'FMOD' and str(row.TypeName) == 'VERSION':
                fields = [f.row for f in row.FieldList if str(f.row.Name) == 'number']
                for constant in rows('Constant'):
                    if any(constant.Parent.row is f for f in fields):
                        fmod_version = f'0x{int.from_bytes(constant.Value.value, "little"):08x}'
        candidates = []
        namespaces = ('System.Reflection', 'System.Linq.Expressions', 'System.Threading',
                      'System.IO', 'System.Net', 'System.Runtime.InteropServices')
        for r in rows('MemberRef'):
            owner = r.Class.row
            ns = str(getattr(owner, 'TypeNamespace', ''))
            if ns.startswith(namespaces):
                candidates.append(f'{ns}.{getattr(owner, "TypeName", "?")}::{r.Name}')
        return {
            'kind': 'CIL', 'machine': hex(pe.FILE_HEADER.Machine),
            'clr_flags': hex(pe.net.struct.Flags),
            'fmod_binding_version': fmod_version,
            'identities': [{'name': str(r.Name), 'version': version(r)} for r in rows('Assembly')],
            'references': [{'name': str(r.Name), 'version': version(r)} for r in rows('AssemblyRef')],
            'pinvoke_counts': dict(sorted(collections.Counter(r['library'] for r in imports).items())),
            'pinvokes': imports, 'platform_member_candidates': sorted(set(candidates)),
        }
    finally:
        pe.close()


def inspect(path):
    result = {'archive': path.name, 'assemblies': {}, 'banks': {}, 'native_files': []}
    with zipfile.ZipFile(path) as archive:
        entries = [i for i in archive.infolist() if not i.is_dir()]
        names = [i.filename for i in entries]
        if len(names) != len(set(names)):
            raise ValueError(f'duplicate ZIP members: {path.name}')
        if 'Celeste.exe' not in names:
            raise ValueError('Expected a PC Celeste ZIP with a root Celeste.exe')
        result['file_count'] = len(entries)
        result['uncompressed_bytes'] = sum(i.file_size for i in entries)
        for info in entries:
            name = info.filename
            if name.lower().endswith(('.dll', '.exe')):
                if info.file_size > 64 * 1024 * 1024:
                    raise ValueError(f'Unexpectedly large PE: {name}')
                data = archive.read(info)
                result['assemblies'][name] = {
                    'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), **assembly(data)}
            elif name.endswith('.bank'):
                digest = hashlib.sha256()
                with archive.open(info) as stream:
                    header = stream.read(12)
                    digest.update(header)
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                bank = {'bytes': info.file_size, 'sha256': digest.hexdigest()}
                if header[:4] == b'RIFF' and len(header) == 12:
                    bank.update(container='RIFF', form=header[8:12].decode('ascii', errors='replace'),
                                declared_container_bytes=int.from_bytes(header[4:8], 'little') + 8)
                result['banks'][name] = bank
            elif '.so' in Path(name).name:
                result['native_files'].append({'path': name, 'bytes': info.file_size})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', type=Path, nargs='+')
    args = parser.parse_args()
    reports = [inspect(path) for path in args.archives]
    output = {'schema': 1, 'method': 'static metadata; no execution; no extraction', 'archives': reports}
    if len(reports) == 2:
        a, b = reports
        output['comparison'] = {}
        for group in ('assemblies', 'banks'):
            common = sorted(a[group].keys() & b[group].keys())
            output['comparison'][group] = {
                'identical_sha256': [n for n in common if a[group][n]['sha256'] == b[group][n]['sha256']],
                'different_sha256': [n for n in common if a[group][n]['sha256'] != b[group][n]['sha256']],
            }
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
