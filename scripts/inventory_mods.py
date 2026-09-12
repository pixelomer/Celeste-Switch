#!/usr/bin/env python3
"""Read unchanged Everest ZIPs without extracting or executing their contents.

Requires PyYAML and dnfile. Reports required dependency/version gaps and static
PE/platform references; this is not a claim that every referenced API executes.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

import yaml
from inventory_pc import assembly


def inspect(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = dict(archive=path.name, bytes=path.stat().st_size, sha256=digest,
                  assemblies={}, native_files=[], case_collisions=[])
    with zipfile.ZipFile(path) as archive:
        names = set()
        folded = {}
        entries = archive.infolist()
        for item in entries:
            name = item.filename
            parts = PurePosixPath(name).parts
            if (name.startswith('/') or '..' in parts or '\\' in name or
                    ':' in name or '\x00' in name or name in names or
                    stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError(f'Unsafe or duplicate ZIP entry: {path.name}: {name!r}')
            names.add(name)
            if name.casefold() in folded and not item.is_dir():
                result['case_collisions'].append([folded[name.casefold()], name])
            folded[name.casefold()] = name
            if name.lower().endswith(('.dll', '.exe')):
                if item.file_size > 64 * 1024 * 1024:
                    raise ValueError(f'Oversized PE: {name}')
                result['assemblies'][name] = assembly(archive.read(item))
            elif name.lower().endswith(('.so', '.dylib', '.nro')):
                result['native_files'].append(name)
        manifests = [n for n in names if n.lower() in ('everest.yaml', 'everest.yml')]
        if len(manifests) != 1:
            raise ValueError(f'Expected one root Everest manifest: {path}')
        if archive.getinfo(manifests[0]).file_size > 1024 * 1024:
            raise ValueError('Oversized manifest')
        result['modules'] = yaml.safe_load(archive.read(manifests[0]).decode('utf-8-sig'))
        result['files'] = sum(not i.is_dir() for i in entries)
        result['uncompressed_bytes'] = sum(i.file_size for i in entries)
    return result


def version(value):
    parts = tuple(map(int, str(value).split('.')))
    return parts + (0,) * (4 - len(parts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    archives = [inspect(p) for p in sorted(args.directory.glob('*.zip'))]
    modules = {}
    for archive in archives:
        for module in archive['modules']:
            name = module['Name']
            if name in modules:
                raise ValueError(f'Duplicate module: {name}')
            modules[name] = module
    gaps, builtins = [], []
    for name, module in modules.items():
        for dep in module.get('Dependencies', []):
            required = dict(parent=name, **dep)
            if dep['Name'] in ('Everest', 'EverestCore', 'Celeste'):
                builtins.append(required)
            elif dep['Name'] not in modules:
                gaps.append(dict(required, reason='missing'))
            elif version(modules[dep['Name']]['Version']) < version(dep['Version']):
                gaps.append(dict(required, reason='version too old'))
    result = dict(schema=1, method='Static ZIP/PE metadata; no extraction or execution',
                  archives=archives, dependency_gaps=gaps, builtin_requirements=builtins)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(archives)} archives, {len(modules)} modules, {len(gaps)} dependency gaps')
    if gaps:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
