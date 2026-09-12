#!/usr/bin/env python3
"""Build an Everest-enabled Celeste SD installation from source and user-owned inputs."""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'eng/horizon'))
from support import digest, git_source, read_mirrors, run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pc-zip', required=True, type=Path, help='Supported itch.io Linux or Windows FNA ZIP')
    p.add_argument('--fmod-android', required=True, type=Path, help='User-supplied fmodstudioapi11014android.tar.gz')
    p.add_argument('--output', type=Path, default=ROOT / 'artifacts/build')
    p.add_argument('--jobs', type=int, default=min(os.cpu_count() or 2, 8))
    p.add_argument('--source-mirrors', type=Path)
    p.add_argument('--runtime-root', type=Path, help='Optional already built matching Horizon runtime source tree')
    p.add_argument('--without-performance-mod', action='store_true')
    p.add_argument('--resume', action='store_true', help='Verify completed stages and resume an interrupted build')
    a = p.parse_args()
    if a.jobs < 1: p.error('--jobs must be positive')
    for key in ['pc_zip', 'fmod_android', 'output', 'runtime_root', 'source_mirrors']:
        if getattr(a, key) is not None: setattr(a, key, getattr(a, key).resolve())
    out = a.output
    if out.exists() and not a.resume: p.error('Output exists; choose a new directory or use --resume')
    lock = json.loads((ROOT / 'sources.lock.json').read_text())
    mirrors = read_mirrors(a.source_mirrors)
    # Fingerprint build code too: changed recipes must use a fresh output.
    recipe_files = [ROOT / 'build.py', ROOT / 'sources.lock.json']
    for folder in ['eng/horizon', 'host', 'native', 'tools', 'scripts', 'src/SwitchPerformance']:
        recipe_files += [f for f in (ROOT / folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix in ['.py', '.cs', '.csproj', '.c', '.h', '.json', '.patch', '.yaml']]
    identity = {'pc_sha256': digest(a.pc_zip), 'fmod_sha256': digest(a.fmod_android),
                'runtime_override': str(a.runtime_root) if a.runtime_root else None,
                'performance_mod': not a.without_performance_mod,
                'recipes': {str(f.relative_to(ROOT)): digest(f) for f in recipe_files}}
    out.mkdir(parents=True, exist_ok=True)
    record = out / 'build-state.json'
    if record.exists():
        state = json.loads(record.read_text())
        if state['identity'] != identity: p.error('Inputs or recipes changed; choose a new output directory')
    else:
        if a.resume: p.error('No build-state.json to resume')
        state = {'identity': identity, 'stages': {}}
        record.write_text(json.dumps(state, indent=2) + '\n')
    def stage(name, command, outputs, env=None):
        outputs = [Path(f) for f in outputs]
        if name in state['stages']:
            if any(not f.is_file() or digest(f) != state['stages'][name].get(str(f)) for f in outputs):
                raise SystemExit('Changed or missing completed output: ' + name)
            print('Verified completed stage: ' + name, flush=True)
            return
        fresh = {'prepare-game': 'prepared', 'mesa': 'mesa', 'fmod': 'fmod', 'lua': 'lua',
                 'graphics': 'graphics', 'host': 'application', 'content': 'content',
                 'performance-mod': 'performance', 'package': 'package'}.get(name)
        if fresh and (out / fresh).exists():
            import time
            saved = out / 'incomplete' / (name + '-' + str(time.time_ns()))
            saved.parent.mkdir(exist_ok=True)
            (out / fresh).rename(saved)
            print('Preserved incomplete stage at ' + str(saved), flush=True)
        print('Building stage: ' + name, flush=True)
        run(command, env=env)
        state['stages'][name] = {str(f): digest(f) for f in outputs}
        record.write_text(json.dumps(state, indent=2) + '\n')
    extra = ['--source-mirrors', a.source_mirrors] if a.source_mirrors else []
    sources = {name: git_source(spec, out / 'sources' / name, mirrors) for name, spec in lock['repositories'].items()}
    runtime = a.runtime_root
    if runtime is None:
        sdk = sources['dotnet-switch']
        stage('runtime', [sys.executable, sdk / 'build.py', '--profile', 'net10-coreclr', '--jobs', a.jobs, *extra],
              [sdk / 'artifacts/net10-coreclr/build.json'])
        runtime = Path(json.loads((sdk / 'artifacts/net10-coreclr/build.json').read_text())['runtime'])
    runtime = runtime.resolve()
    if subprocess.check_output(['git', '-C', runtime, 'rev-parse', 'HEAD'], text=True).strip() != lock['runtime_revision']:
        raise SystemExit('Runtime does not match the coordinated source lock')
    environment = os.environ | json.loads((runtime / 'artifacts/horizon/environment.json').read_text())
    sdk = Path(environment['DEVKITPRO']) / 'libnx'
    # All host/native builds inherit the same complete libnx SDK overlay.
    os.environ.update(environment)
    fna = sources['FNA']; everest = sources['Everest']; sdl = sources['SDL']
    fna_dll = out / 'fna/bin/FNA.Core/release_net8.0/FNA.dll'
    stage('fna', [sys.executable, fna / 'build-horizon.py', '--managed-only', '--output', out / 'fna', *extra], [fna_dll])
    stage('sdl', [sys.executable, sdl / 'build-horizon.py', '--libnx', sdk, '--output', out / 'sdl', '--jobs', a.jobs, *extra],
          [out / 'sdl/libSDL2.a', out / 'sdl/manifest.json'])
    stage('fna3d', [sys.executable, fna / 'lib/FNA3D/build-horizon.py', '--libnx', sdk, '--output', out / 'fna3d', '--jobs', a.jobs, *extra],
          [out / 'fna3d/libFNA3D.a', out / 'fna3d/libmojoshader.a'])
    stage('everest', [sys.executable, everest / 'build-horizon.py', '--output', out / 'everest', *extra],
          [out / 'everest/manifest.json'])
    install = out / 'prepared/install'
    stage('prepare-game', [sys.executable, ROOT / 'tools/prepare-everest/run.py', '--pc-zip', a.pc_zip,
          '--everest-publish', out / 'everest/everest', '--installer-build', out / 'everest/installer',
          '--fna', fna_dll, '--output', out / 'prepared'],
          [install / 'Celeste.dll', install / 'FNA.dll', install / 'MMHOOK_Celeste.dll', out / 'prepared/outputs.json'])
    stage('mesa', [sys.executable, ROOT / 'native/mesa/build.py', '--libnx', sdk, '--output', out / 'mesa', '--jobs', a.jobs],
          [out / 'mesa/libEGL.a', out / 'mesa/manifest.json'])
    stage('fmod', [sys.executable, ROOT / 'native/fmod/prepare.py', '--archive', a.fmod_android, '--output', out / 'fmod', *extra],
          [out / 'fmod/build-manifest.json'])
    stage('lua', [sys.executable, ROOT / 'native/lua/build.py', '--source', sources['lua'], '--keralua', install / 'KeraLua.dll',
          '--libnx', sdk, '--output', out / 'lua'], [out / 'lua/liblua54.a', out / 'lua/manifest.json'])
    stage('graphics', [sys.executable, ROOT / 'native/graphics/manifest.py', '--fna', fna_dll,
          '--fna3d-build', out / 'fna3d', '--sdl-build', out / 'sdl', '--mesa-library', out / 'mesa/libEGL.a', '--output', out / 'graphics'],
          [out / 'graphics/manifest.json', out / 'graphics/imports.json'])
    stage('host', [sys.executable, ROOT / 'host/build.py', '--runtime', runtime, '--runtime-baseline', runtime,
          '--graphics-build', out / 'graphics', '--fmod-build', out / 'fmod', '--celeste', install / 'Celeste.dll',
          '--content-assembly', install / 'Celeste.Content.dll', '--fna', fna, '--prepared-fna', install / 'FNA.dll',
          '--sdl-build', out / 'sdl', '--monomod', everest / 'external/MonoMod', '--dependency-directory', install,
          '--lua-build', out / 'lua', '--output', out / 'application', '--managed-pool-mib', '1536',
          '--gc-region-mib', '1280', '--nv-transfer-mib', '32', '--protected-managed-pool'],
          [out / 'application/celeste-pc.nro', out / 'application/integration-manifest.json'])
    stage('content', [sys.executable, ROOT / 'tools/stage-content/stage.py', a.pc_zip, out / 'content'], [out / 'content/content-manifest.json'])
    mod = None
    if not a.without_performance_mod:
        mod = out / 'performance/deploy/000-SwitchPerformance.zip'
        stage('performance-mod', [sys.executable, ROOT / 'scripts/build-performance-mod.py', '--install', install, '--output', out / 'performance'], [mod])
    cmd = [sys.executable, ROOT / 'tools/package/package.py', '--application', out / 'application', '--content', out / 'content',
           '--sources-lock', ROOT / 'sources.lock.json', '--output', out / 'package']
    if mod: cmd += ['--performance-mod', mod]
    stage('package', cmd, [out / 'package/installation.json', out / 'package/celeste-switch-local.zip'])
    print('Local installation: ' + str(out / 'package/sdcard'))
    print('Contains your game and FMOD files; keep this installation ZIP private.')

if __name__ == '__main__':
    main()
