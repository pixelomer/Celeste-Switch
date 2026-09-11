#!/usr/bin/env python3
"""Build the Horizon hook fixture from explicit runtime and MonoMod source trees."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime', type=Path, required=True)
p.add_argument('--runtime-baseline', type=Path, required=True, help='Source tree containing matching .NET 10 BCL/CoreLib/SDK outputs')
p.add_argument('--monomod', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
here = Path(__file__).resolve().parent
out = a.output.resolve()
if out.exists(): p.error('Choose a new --output directory to preserve existing outputs')
out.mkdir(parents=True)
runtime, baseline, monomod = a.runtime.resolve(), a.runtime_baseline.resolve(), a.monomod.resolve()
compiler = Path(os.environ.get('DEVKITA64', '/opt/devkitpro/devkitA64'))/'bin/aarch64-none-elf-gcc'
sources = [monomod/'native/libnx/exception-helper.c', monomod/'src/MonoMod.Core/Platforms/Architectures/arm64/exhelper_linux_macos_arm64.S', here/'imports.c']
objects = []
for source in sources:
    obj = out/(source.stem+'.o')
    subprocess.run([str(compiler), '-march=armv8-a+crc+crypto', '-mtune=cortex-a57', '-mtp=soft', '-fPIE', '-O2', '-g', '-fexceptions', '-fno-omit-frame-pointer', '-I'+str(runtime/'src/coreclr/hosts/inc'), '-c', str(source), '-o', str(obj)], check=True)
    objects.append(obj)
bin = monomod/'artifacts/sdk-compiler-control/bin/MonoMod.RuntimeDetour/release_net10.0'
deps = json.loads((bin/'MonoMod.RuntimeDetour.deps.json').read_text())
packages = Path(os.environ.get('NUGET_PACKAGES', str(Path.home()/'.nuget/packages')))
closure = {}
for identity, details in deps['targets'][deps['runtimeTarget']['name']].items():
    library = deps['libraries'][identity]
    for asset in details.get('runtime', {}):
        if not asset.endswith('.dll'): continue
        dll = packages/library['path']/asset if library['type'] == 'package' else bin/Path(asset).name
        if not dll.is_file(): raise SystemExit('Missing runtime dependency: '+str(dll))
        if dll.name in closure and closure[dll.name].read_bytes() != dll.read_bytes(): raise SystemExit('Assembly collision: '+dll.name)
        closure[dll.name] = dll
symbols = ['coreclr_libnx_get_jit', 'coreclr_libnx_memory_granularity', 'coreclr_libnx_memory_allocate', 'coreclr_libnx_memory_free', 'coreclr_libnx_memory_readable', 'coreclr_libnx_memory_patch', 'monomod_libnx_exception_helper']
symbols += ['coreclr_libnx_jit_get_compile_callback', 'coreclr_libnx_jit_set_compile_callback']
command = ['python3', str(runtime/'src/coreclr/pal/tests/libnx/host/build.py'), '--probe', 'bcl', '--output', str(out/'host'),
           '--corelib', str(baseline/'artifacts/bin/coreclr/libnx.arm64.Release/IL/System.Private.CoreLib.dll'),
           '--framework', str(baseline/'artifacts/bin/runtime/net10.0-libnx-Release-arm64'), '--dotnet-root', str(baseline/'.dotnet'),
           '--managed-source', str(here/'SwitchProbe.cs'), '--managed-directory', '/switch/celeste-hook-probe', '--log-prefix', '/switch/celeste-hook']
for obj in objects: command += ['--native-object', str(obj)]
for dll in closure.values(): command += ['--managed-reference', str(dll)]
for symbol in symbols: command += ['--export-symbol', symbol]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
(out/'integration-manifest.json').write_text(json.dumps({'command': command, 'source_sha256': {str(s): digest(s) for s in [Path(__file__),here/'SwitchProbe.cs',*sources, sources[1].with_name('asm.i')]},
    'runtime_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip(),
    'monomod_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=monomod,text=True).strip()},indent=2)+'\n')
subprocess.run(command, check=True)
