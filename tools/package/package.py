#!/usr/bin/env python3
"""Assemble a local SD installation; never overwrite an existing game or saves."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['application', 'content', 'sources-lock', 'output']: p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--performance-mod', type=Path)
    a = p.parse_args()
    out = a.output.resolve()
    if out.exists(): p.error('Choose a new output directory; existing saves/installations are never replaced')
    app = a.application.resolve(); content = a.content.resolve()
    integration = json.loads((app / 'integration-manifest.json').read_text())
    if sha(app / 'celeste-pc.nro') != integration['nro_sha256']: raise SystemExit('Changed NRO')
    cm = json.loads((content / 'content-manifest.json').read_text())
    for record in cm['files']:
        path = content / record['path']
        if not path.resolve().is_relative_to(content) or path.is_symlink() or sha(path) != record['sha256']:
            raise SystemExit('Changed or unsafe Content input')
    managed = app / 'host/managed'
    for required in ['Celeste.dll', 'FNA.dll', 'MMHOOK_Celeste.dll', 'Celeste.Mod.mm.dll', 'System.Private.CoreLib.dll', 'lib/libfmod.so', 'lib/libfmodstudio.so']:
        if not (managed / required).is_file(): raise SystemExit('Missing deployment input: ' + required)
    for source in [managed, content / 'Content']:
        if any(f.is_symlink() for f in source.rglob('*')): raise SystemExit('Symlink deployment input rejected')
    out.mkdir(parents=True)
    game = out / 'sdcard/switch/celeste-pc'
    shutil.copytree(managed, game)
    shutil.copytree(content / 'Content', game / 'Content')
    shutil.copy2(app / 'celeste-pc.nro', game / 'celeste-pc.nro')
    (game / 'Mods').mkdir(exist_ok=True)
    if a.performance_mod:
        shutil.copy2(a.performance_mod, game / 'Mods/000-SwitchPerformance.zip')
        # Default changes belong to this original removable mod, not user save files.
    for name in ['THIRD_PARTY.md']:
        shutil.copy2(ROOT / name, out / name)
    shutil.copy2(a.sources_lock, out / 'sources.lock.json')
    files = {str(f.relative_to(out / 'sdcard')): {'bytes': f.stat().st_size, 'sha256': sha(f)}
             for f in sorted((out / 'sdcard').rglob('*')) if f.is_file()}
    manifest = {'format': 1, 'distribution': 'Local installation only; contains user-owned Celeste and FMOD files',
                'game_version': '1.4.0.0', 'fmod_version': '1.10.14', 'runtime': '.NET 10 Horizon CoreCLR/RyuJIT',
                'files': files, 'sources_lock_sha256': sha(a.sources_lock)}
    (out / 'installation.json').write_text(json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(out / 'celeste-switch-local.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for f in sorted((out / 'sdcard').rglob('*')):
            if f.is_file(): archive.write(f, str(f.relative_to(out / 'sdcard')))
    with zipfile.ZipFile(out / 'celeste-switch-local.zip') as archive:
        bad = archive.testzip()
        if bad: raise SystemExit('ZIP CRC failure: ' + bad)
    print(out)

if __name__ == '__main__': main()
