#!/usr/bin/env python3
"""Link verified FNA inputs and FMOD1.10.14 output into a CoreCLR control."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('runtime','runtime-baseline','graphics-build','fmod-build','celeste','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
for key,value in vars(a).items():setattr(a,key,value.resolve())
a.output.mkdir(parents=True,exist_ok=False);out=a.output
here=Path(__file__).resolve().parent;platform=here.parents[1]/'native/fmod'
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
fna=a.graphics_build/'host/managed/FNA.dll'
if sha(fna)!=graphics['managed_sha256']['FNA.dll']:raise SystemExit('Changed FNA input')
for name in ('so_util.c','so_util.h','imports.inc'):shutil.copy2(a.fmod_build/name,snapshot/name)
sdk=None
for line in (a.runtime/'artifacts/obj/coreclr/libnx.arm64.Release/coreclr-probe/CMakeCache.txt').read_text().splitlines():
 if line.startswith('LIBNX_ROOT:PATH='):sdk=Path(line.split('=',1)[1])
if sdk is None:raise SystemExit('Missing runtime SDK')
commands=[]
def run(cmd):commands.append(list(map(str,cmd)));subprocess.run(commands[-1],check=True)
flags=['-O2','-g','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE','-D__SWITCH__','-D_GNU_SOURCE','-DFMOD_PROBE_RELEASE','-DFMOD_ADAPTER_MIN_STACK=1572864',f'-I{snapshot}',f'-I{a.fmod_build}/sdk/inc',f'-I{sdk}/include','-I/opt/devkitpro/portlibs/switch/include',f'-I{Path(os.environ["JAVA_HOME"]).resolve()}/include',f'-I{Path(os.environ["JAVA_HOME"]).resolve()}/include/linux','-Werror=incompatible-pointer-types','-Werror=implicit-function-declaration']
objects=[]
for name in ('android','jni','runtime','output','so_util','imports'):
 obj=out/(name+'.o');run(['aarch64-none-elf-gcc',*flags,'-c',snapshot/(name+'.c'),'-o',obj]);objects.append(obj)
archives.append(Path(subprocess.check_output(['aarch64-none-elf-gcc','-print-file-name=libpthread.a'],text=True).strip()).resolve())
cmd=['python3',a.runtime/'src/coreclr/pal/tests/libnx/host/build.py','--probe','bcl','--output',out/'host','--corelib',a.runtime_baseline/'artifacts/bin/coreclr/libnx.arm64.Release/IL/System.Private.CoreLib.dll','--framework',a.runtime_baseline/'artifacts/bin/runtime/net10.0-libnx-Release-arm64','--dotnet-root',a.runtime_baseline/'.dotnet','--managed-source',snapshot/'Probe.cs','--managed-reference',fna,'--managed-reference',a.celeste,'--managed-directory','/switch/celeste-audio-managed','--log-prefix','/switch/celeste-audio-managed']
for obj in objects:cmd+=['--native-object',obj]
for archive in archives:cmd+=['--native-library',archive]
for symbol in json.loads((a.graphics_build/'imports.json').read_text())['resident_exports']:cmd+=['--export-symbol',symbol]
run(cmd);shutil.copy2(out/'host/coreclr-host-probe.nro',out/'celeste-audio-managed.nro')
manifest={'native_sources':{p.name:sha(p) for p in snapshot.iterdir() if p.is_file()},'fmod_input_manifest_sha256':sha(a.fmod_build/'build-manifest.json'),'graphics_input_manifest_sha256':sha(a.graphics_build/'host/build-manifest.json'),'celeste_sha256':sha(a.celeste),'libnx_sha256':sha(sdk/'lib/libnx.a'),'commands':commands,'nro_sha256':sha(out/'celeste-audio-managed.nro')}
(out/'integration-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
