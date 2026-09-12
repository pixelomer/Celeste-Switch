#!/usr/bin/env python3
"""Build the SD-backed PC Celeste host from user-owned game inputs and source ports."""
import argparse,hashlib,json,os,shutil,subprocess
import dnfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('runtime','runtime-baseline','graphics-build','fmod-build','celeste','content-assembly','fna','sdl-build','monomod','dependency-directory','output'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--prepared-fna',type=Path,help='Use the paired FNA already patched by the standard Everest installer')
p.add_argument('--lua-build',type=Path,help='Pinned native Lua build for Everest')
p.add_argument('--mesa-library',type=Path,help='Explicit replacement Mesa archive for graphics diagnostics; recorded separately')
p.add_argument('--nvmap-diagnostics',action='store_true',help='Testing only: log failed NV allocation/map calls')
p.add_argument('--nv-transfer-mib',type=int,default=0,help='NV service transfer-memory budget; zero keeps libnx default, otherwise 8..64 MiB in steps of 8')
p.add_argument('--managed-pool-mib',type=int,default=512,help='Shared GC/PAL data backing pool in MiB (64..2048); leaves native graphics/audio allocations separate')
p.add_argument('--gc-region-mib',type=int,default=0,help='Optional upstream GCRegionRange override in MiB; zero retains runtime default')
p.add_argument('--protected-managed-pool',action='store_true',help='Use opt-in Horizon data alias pool; virtual capacity equals backing size')
p.add_argument('--nxlink-stdio',action='store_true',help='Testing only: stream stdout/stderr to the nxlink launcher instead of SD files')
a=p.parse_args()
if not 64 <= a.managed_pool_mib <= 2048:p.error('Managed pool must be 64..2048 MiB')
if a.nv_transfer_mib and (a.nv_transfer_mib < 8 or a.nv_transfer_mib > 64 or a.nv_transfer_mib % 8):p.error('NV transfer budget must be zero or 8..64 MiB in steps of 8')
if a.gc_region_mib and (a.gc_region_mib < 64 or a.gc_region_mib % 64 or a.gc_region_mib > a.managed_pool_mib):p.error('GC region must be zero or a multiple of 64 MiB within the managed pool')
for key,value in vars(a).items():
 if isinstance(value,Path):setattr(a,key,value.resolve())
a.output.mkdir(parents=True,exist_ok=False);out=a.output
here=Path(__file__).resolve().parent;platform=here.parent/'native/fmod'
snapshot=out/'sources';snapshot.mkdir()
for folder in (here,platform):
 for path in folder.iterdir():
  if path.is_file():shutil.copy2(path,snapshot/path.name)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
fm=json.loads((a.fmod_build/'build-manifest.json').read_text())
if fm['fmod_version']!='1.10.14' or fm['output_api']!=3:raise SystemExit('Wrong FMOD input version')
for name,digest in fm['sdk_files'].items():
 if sha(a.fmod_build/'sdk'/name)!=digest:raise SystemExit('Changed SDK input: '+name)
graphics=json.loads((a.graphics_build/'host/build-manifest.json').read_text())
archives=[]
for name,digest in graphics['native_libraries'].items():
 path=Path(name)
 if sha(path)!=digest:raise SystemExit('Changed graphics archive: '+name)
 archives.append(path)
if a.mesa_library:
 if sum(path.name == 'libEGL.a' for path in archives) != 1:raise SystemExit('Expected one Mesa archive to replace')
 archives=[a.mesa_library if path.name == 'libEGL.a' else path for path in archives]
sdl=json.loads((a.sdl_build/'manifest.json').read_text())
if sha(a.sdl_build/'libSDL2.a')!=sdl['archive_sha256']:raise SystemExit('Changed SDL input')
archives=[a.sdl_build/'libSDL2.a' if path.name=='libSDL2.a' else path for path in archives]
if not a.prepared_fna:subprocess.run(['dotnet','build',str(a.fna/'FNA.Core.csproj'),'-c','Release','-p:TargetFrameworks=net8.0','-p:ArtifactsPath='+str(out/'fna')],check=True)
fna=a.prepared_fna or out/'fna/bin/FNA.Core/release_net8.0/FNA.dll'
lua=None
if a.lua_build:
 lua=json.loads((a.lua_build/'manifest.json').read_text())
 if sha(a.lua_build/'liblua54.a')!=lua['archive_sha256']:raise SystemExit('Changed Lua archive')
 archives.append(a.lua_build/'liblua54.a')
for name in ('so_util.c','so_util.h','imports.inc'):shutil.copy2(a.fmod_build/name,snapshot/name)
if a.nvmap_diagnostics:shutil.copy2(here.parent/'native/mesa/nv-diagnostics.c',snapshot/'nv-diagnostics.c')
for path in (a.monomod/'native/libnx/exception-helper.c',a.monomod/'src/MonoMod.Core/Platforms/Architectures/arm64/exhelper_linux_macos_arm64.S',a.monomod/'src/MonoMod.Core/Platforms/Architectures/arm64/asm.i'):shutil.copy2(path,snapshot/path.name)
sdk=None
for line in (a.runtime/'artifacts/obj/coreclr/libnx.arm64.Release/coreclr-probe/CMakeCache.txt').read_text().splitlines():
 if line.startswith('LIBNX_ROOT:PATH='):sdk=Path(line.split('=',1)[1])
if sdk is None:raise SystemExit('Missing runtime SDK')
commands=[]
def run(cmd):commands.append(list(map(str,cmd)));subprocess.run(commands[-1],check=True)
flags=['-O2','-g','-fexceptions','-fno-omit-frame-pointer',f'-I{a.runtime}/src/coreclr/hosts/inc','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE','-D__SWITCH__','-D_GNU_SOURCE','-DFMOD_PROBE_RELEASE','-DFMOD_ADAPTER_MIN_STACK=1572864','-DCELESTE_FMOD_LIBRARY_DIR="sdmc:/switch/celeste-pc/lib"',f'-I{snapshot}',f'-I{a.fmod_build}/sdk/inc',f'-I{sdk}/include','-I/opt/devkitpro/portlibs/switch/include',f'-I{Path(os.environ["JAVA_HOME"]).resolve()}/include',f'-I{Path(os.environ["JAVA_HOME"]).resolve()}/include/linux','-Werror=incompatible-pointer-types','-Werror=implicit-function-declaration']
flags += [f'-I{a.runtime}/src/native/libs/Common',f'-DCELESTE_MANAGED_POOL_MIB={a.managed_pool_mib}']
flags.append(f'-DCELESTE_GC_REGION_MIB={a.gc_region_mib}')
flags.append(f'-DCELESTE_PROTECTED_MANAGED_POOL={int(a.protected_managed_pool)}')
flags.append(f'-DCELESTE_NV_TRANSFER_MIB={a.nv_transfer_mib}')
if a.nxlink_stdio:flags.append('-DCELESTE_NXLINK_STDIO')
objects=[]
for name in ('android','jni','runtime','output','so_util','imports'):
 obj=out/(name+'.o');run(['aarch64-none-elf-gcc',*flags,'-c',snapshot/(name+'.c'),'-o',obj]);objects.append(obj)
for name in ('exception-helper.c','exhelper_linux_macos_arm64.S'):
 obj=out/(name+'.o');run(['aarch64-none-elf-gcc',*flags,'-c',snapshot/name,'-o',obj]);objects.append(obj)
if a.nvmap_diagnostics:
 obj=out/'nv-diagnostics.o';run(['aarch64-none-elf-gcc',*flags,'-c',snapshot/'nv-diagnostics.c','-o',obj]);objects.append(obj)
archives.append(Path(subprocess.check_output(['aarch64-none-elf-gcc','-print-file-name=libpthread.a'],text=True).strip()).resolve())
cmd=['python3',a.runtime/'src/coreclr/pal/tests/libnx/host/build.py','--probe','bcl','--output',out/'host','--corelib',a.runtime_baseline/'artifacts/bin/coreclr/libnx.arm64.Release/IL/System.Private.CoreLib.dll','--framework',a.runtime_baseline/'artifacts/bin/runtime/net10.0-libnx-Release-arm64','--dotnet-root',a.runtime_baseline/'.dotnet','--application-entry','Celeste.dll','--managed-reference',fna,'--managed-reference',a.celeste,'--managed-reference',a.content_assembly,'--watchdog-seconds','0','--managed-directory','/switch/celeste-pc','--log-prefix','/switch/celeste-pc']
# Resolve the complete metadata reference closure, retaining the matching Horizon
# framework. Coreification adds runtime shims (NETCoreifier), not only IL edits.
framework=a.runtime_baseline/'artifacts/bin/runtime/net10.0-libnx-Release-arm64'
known={path.stem for path in framework.glob('*.dll')} | {'System.Private.CoreLib'}
pending=[fna,a.celeste,a.content_assembly]
dependencies=[]
if a.prepared_fna:
 # Standard Everest installer support read dynamically by relinking/HookGen.
 for name in ('MMHOOK_Celeste.dll','Celeste.Mod.mm.dll'):
  path=a.dependency_directory/name
  if not path.is_file():raise SystemExit('Missing Everest support '+name)
  dependencies.append(path)
  # Everest reads the patch assembly with Cecil and extracts runtime rules.
  # It does not execute its Steam build/reference-only dependency graph.
  if name != 'Celeste.Mod.mm.dll':pending.append(path)
known.update(path.stem for path in pending)
while pending:
 path=pending.pop()
 assembly=dnfile.dnPE(str(path),fast_load=False)
 if not assembly.net:raise SystemExit('Not a managed assembly: '+str(path))
 refs=assembly.net.mdtables.AssemblyRef
 for ref in refs.rows if refs else []:
  name=str(ref.Name)
  if name in known:continue
  candidate=a.dependency_directory/(name+'.dll')
  if not candidate.is_file():raise SystemExit('Missing dependency '+name+' referenced by '+path.name)
  known.add(name);dependencies.append(candidate);pending.append(candidate)
 assembly.close()
for path in dependencies:cmd+=['--managed-reference',path]
for obj in objects:cmd+=['--native-object',obj]
if a.nvmap_diagnostics:
 for symbol in ('nvioctlNvmap_Create','nvioctlNvmap_Alloc','nvAddressSpaceMap'):cmd+=['--wrap-symbol',symbol]
for archive in archives:cmd+=['--native-library',archive]
for symbol in json.loads((a.graphics_build/'imports.json').read_text())['resident_exports']:cmd+=['--export-symbol',symbol]
for symbol in ('coreclr_libnx_get_jit','coreclr_libnx_jit_get_compile_callback','coreclr_libnx_jit_set_compile_callback','coreclr_libnx_memory_granularity','coreclr_libnx_memory_allocate','coreclr_libnx_memory_free','coreclr_libnx_memory_readable','coreclr_libnx_memory_patch','monomod_libnx_exception_helper'):cmd+=['--export-symbol',symbol]
if lua:
 for symbol in lua['exports']:cmd+=['--export-symbol',symbol]
run(cmd);shutil.copy2(out/'host/coreclr-host-probe.nro',out/'celeste-pc.nro')
manifest={'prepared_fna_sha256':sha(fna),'lua_manifest_sha256':sha(a.lua_build/'manifest.json') if lua else None,'managed_dependencies':{path.name:sha(path) for path in dependencies},'native_sources':{p.name:sha(p) for p in snapshot.iterdir() if p.is_file()},'fmod_input_manifest_sha256':sha(a.fmod_build/'build-manifest.json'),'graphics_input_manifest_sha256':sha(a.graphics_build/'host/build-manifest.json'),'celeste_sha256':sha(a.celeste),'content_assembly_sha256':sha(a.content_assembly),'sdl_manifest_sha256':sha(a.sdl_build/'manifest.json'),'monomod_revision':subprocess.check_output(['git','-C',str(a.monomod),'rev-parse','HEAD'],text=True).strip(),'fna_revision':subprocess.check_output(['git','-C',str(a.fna),'rev-parse','HEAD'],text=True).strip(),'libnx_sha256':sha(sdk/'lib/libnx.a'),'commands':commands,'nro_sha256':sha(out/'celeste-pc.nro')}
manifest['managed_pool_mib']=a.managed_pool_mib
manifest['nvmap_diagnostics']=a.nvmap_diagnostics
manifest['nv_transfer_mib']=a.nv_transfer_mib
manifest['mesa_override']={'path':str(a.mesa_library),'sha256':sha(a.mesa_library)} if a.mesa_library else None
manifest['gc_region_mib']=a.gc_region_mib
manifest['protected_managed_pool']=a.protected_managed_pool
manifest['nxlink_stdio']=a.nxlink_stdio
manifest['nxvm_header_sha256']=sha(a.runtime/'src/native/libs/Common/nxvm.h')
payload=out/'host/managed/lib';payload.mkdir()
for name in ('libfmod.so','libfmodstudio.so'):shutil.copy2(a.fmod_build/'sdk/android'/name,payload/name)
(out/'integration-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
