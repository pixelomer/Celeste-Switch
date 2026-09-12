#!/usr/bin/env python3
"""Build original FNA graphics control with explicit source/runtime/native inputs."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import dnfile
p=argparse.ArgumentParser(description=__doc__)
for name in ('runtime','runtime-baseline','fna','mesa-library','output'): p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--sdl-library',type=Path,help='Explicit source-built SDL2 archive; default is the installed portlib')
a=p.parse_args()
a=argparse.Namespace(**{k:(v.resolve() if v else None) for k,v in vars(a).items()})
if a.output.exists(): p.error('Use a new output directory to preserve existing outputs')
a.output.mkdir(parents=True)
here=Path(__file__).resolve().parent
dkp=Path(os.environ.get('DEVKITPRO','/opt/devkitpro'))
port=dkp/'portlibs/switch'
cache=a.runtime/'artifacts/obj/coreclr/libnx.arm64.Release/coreclr-probe/CMakeCache.txt'
sdk=None
for line in cache.read_text().splitlines():
    if line.startswith('LIBNX_ROOT:PATH='): sdk=Path(line.split('=',1)[1])
if sdk is None or not (sdk/'switch.specs').is_file(): p.error('Missing runtime libnx SDK')
commands=[]
def run(command, **kwargs):
    command=list(map(str,command)); commands.append(command)
    return subprocess.run(command,check=True,**kwargs)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def revision(path): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip()
toolchain=a.output/'Switch.cmake'
toolchain.write_text('include("'+str(dkp/'cmake/Switch.cmake')+'")\nset(NX_ROOT "'+str(sdk)+'")\nlist(PREPEND CMAKE_FIND_ROOT_PATH "'+str(sdk)+'")\n')
run(['cmake','-S',a.fna/'lib/FNA3D','-B',a.output/'native','-G','Ninja',
    '-DCMAKE_TOOLCHAIN_FILE='+str(toolchain),'-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
    '-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DBUILD_SHARED_LIBS=OFF','-DBUILD_VULKAN=OFF',
    '-DSDL2_INCLUDE_DIRS='+str(port/'include/SDL2'),'-DSDL2_LIBRARIES='+str(port/'lib/libSDL2.a')])
run(['cmake','--build',a.output/'native','--parallel','8'])
run(['dotnet','build',a.fna/'FNA.Core.csproj','-c','Release','-p:TargetFrameworks=net8.0','-p:ArtifactsPath='+str(a.output/'fna')])
fna=a.output/'fna/bin/FNA.Core/release_net8.0/FNA.dll'
imports={}
pe=dnfile.dnPE(str(fna))
for row in pe.net.mdtables.ImplMap.rows:
    name=str(row.ImportScope.row.Name)
    imports.setdefault(name,set()).add(str(row.ImportName))
pe.close()
archives=[a.output/'native/libFNA3D.a',a.output/'native/libmojoshader.a',a.sdl_library or port/'lib/libSDL2.a',a.mesa_library,port/'lib/libglapi.a',port/'lib/libdrm_nouveau.a']
provided=set()
for archive in archives[:3]:
    symbols=subprocess.check_output([str(dkp/'devkitA64/bin/aarch64-none-elf-nm'),'-g','--defined-only',str(archive)],text=True)
    provided.update(line.split()[-1] for line in symbols.splitlines() if len(line.split())==3)
requested=set.union(*(v for k,v in imports.items() if k in ('SDL2','FNA3D')))
exported=sorted(requested & provided)
missing=sorted(requested-provided)
(a.output/'imports.json').write_text(json.dumps({'declared':{k:sorted(v) for k,v in imports.items()},'resident_exports':exported,'unavailable_graphics_imports':missing},indent=2)+'\n')
print('Native graphics exports:',len(exported),'unavailable optional entries:',missing,flush=True)
obj=a.output/'imports.o'
run([dkp/'devkitA64/bin/aarch64-none-elf-gcc','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE','-O2','-g','-I'+str(sdk/'include'),'-I'+str(port/'include/SDL2'),'-c',here/'imports.c','-o',obj])
command=['python3',a.runtime/'src/coreclr/pal/tests/libnx/host/build.py','--probe','bcl','--output',a.output/'host',
    '--corelib',a.runtime_baseline/'artifacts/bin/coreclr/libnx.arm64.Release/IL/System.Private.CoreLib.dll',
    '--framework',a.runtime_baseline/'artifacts/bin/runtime/net10.0-libnx-Release-arm64','--dotnet-root',a.runtime_baseline/'.dotnet',
    '--managed-source',here/'Probe.cs','--managed-reference',fna,'--native-object',obj,
    '--managed-directory','/switch/celeste-fna-probe','--log-prefix','/switch/celeste-fna']
for archive in archives: command += ['--native-library',archive]
for symbol in exported: command += ['--export-symbol',symbol]
run(command)
(a.output/'celeste-fna-probe.nro').write_bytes((a.output/'host/coreclr-host-probe.nro').read_bytes())
manifest={'runtime_revision':revision(a.runtime),'fna_revision':revision(a.fna),'fna3d_revision':revision(a.fna/'lib/FNA3D'),
    'mojoshader_revision':revision(a.fna/'lib/FNA3D/MojoShader'),'mesa_library':str(a.mesa_library),'mesa_sha256':sha(a.mesa_library),
    'libnx':str(sdk),'sources':{s.name:sha(s) for s in (here/'build.py',here/'imports.c',here/'Probe.cs')},'commands':commands}
(a.output/'integration-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for repo,name in [(a.fna,'fna'),(a.fna/'lib/FNA3D','fna3d'),(a.fna/'lib/FNA3D/MojoShader','mojoshader')]:
    (a.output/(name+'-diff.patch')).write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=repo))
