#!/usr/bin/env python3
"""Build exact FMOD 1.10.14 controls from user-supplied SDK archives, never FMOD 2."""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, tarfile
from pathlib import Path
from fmod_imports import generate_imports
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--archives',type=Path,required=True)
p.add_argument('--loader',type=Path,required=True)
p.add_argument('--libnx',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--banks',type=Path)
p.add_argument('--event')
a=p.parse_args()
for k in ('archives','loader','libnx','output'): setattr(a,k,getattr(a,k).resolve())
a.output.mkdir(parents=True,exist_ok=False)
source=Path(__file__).resolve().parent; out=a.output
src=out/'sources';src.mkdir()
for path in source.iterdir():
 if path.is_file():shutil.copy2(path,src/path.name)
sdk=out/'sdk'; sdk.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
expected={'android':'e374d9d4e189281d3a24b6459614df48a24b9816c829fded449ec14b7b0baccb','linux':'52e393725872e1da044dd95be71b54e96911b49cb34bb0615e12ded6e4d37103'}
inputs={}
for platform,digest in expected.items():
 archive=a.archives/f'fmodstudioapi11014{platform}.tar.gz'
 if sha(archive)!=digest:raise SystemExit('SDK archive does not match the required 1.10.14 input: '+str(archive))
 inputs[archive.name]=digest
 with tarfile.open(archive) as t:
  for m in t:
   if not m.isfile():continue
   header=platform=='android' and ('/api/lowlevel/inc/' in m.name or '/api/studio/inc/' in m.name) and m.name.endswith('.h')
   library=('/arm64-v8a/' if platform=='android' else '/x86_64/') in m.name and re.search(r'/libfmod(?:studio)?\.so(?:\.\d+)*$',m.name)
   if not (header or library):continue
   if m.size>32*1024*1024:raise SystemExit('Oversized SDK member')
   dest=sdk/('inc' if header else platform)/Path(m.name).name;dest.parent.mkdir(exist_ok=True)
   if dest.exists():raise SystemExit('Duplicate SDK basename')
   dest.write_bytes(t.extractfile(m).read())
if not re.search(r'#define\s+FMOD_VERSION\s+0x00011014\b',(sdk/'inc/fmod_common.h').read_text()):raise SystemExit('Wrong FMOD header')
if not re.search(r'#define\s+FMOD_OUTPUT_PLUGIN_VERSION\s+3\b',(sdk/'inc/fmod_output.h').read_text()):raise SystemExit('Wrong output ABI')
for stem in ('libfmod','libfmodstudio'):(sdk/'linux'/f'{stem}.so.10').symlink_to(f'{stem}.so.10.14')
revision=subprocess.check_output(['git','-C',str(a.loader),'rev-parse','HEAD'],text=True).strip()
if revision!='41e045ea275fcfae906009f165a6635725e9a08f':raise SystemExit('Unsupported loader revision')
if subprocess.check_output(['git','-C',str(a.loader),'status','--porcelain','--','source/so_util.c','source/so_util.h'],text=True):raise SystemExit('Modified upstream loader')
s=(a.loader/'source/so_util.c').read_text().replace('#include "config.h"','').replace('#include "util.h"','int debugPrintf(const char*,...);').replace('#include "error.h"','void fatal_error(const char*,...) __attribute__((noreturn));')
s=s.replace('envGetOwnProcessHandle()', 'probeProcessHandle()').replace('#include <switch.h>', '#include <switch.h>\nHandle probeProcessHandle(void);')
needle='  return 0;\n}\n\nvoid so_execute_init_array'
if s.count(needle)!=1:raise SystemExit('Loader fail-fast patch mismatch')
s=s.replace(needle,'  return missing;\n}\n\nvoid so_execute_init_array')
(out/'so_util.c').write_text(s);shutil.copy2(a.loader/'source/so_util.h',out/'so_util.h')
unknown=generate_imports(sdk,out,True)
bank_flags=[]; bank_hashes={}
if bool(a.banks) != bool(a.event):raise SystemExit('--banks and --event must be supplied together')
if a.banks:
 bank_dir=out/'payload/banks';bank_dir.mkdir(parents=True)
 names=[]
 for path in sorted(a.banks.glob('*.bank'),key=lambda p:(not p.name.endswith('.strings.bank'),p.name)):
  if path.is_symlink() or not path.is_file():raise SystemExit('Invalid bank input')
  shutil.copy2(path,bank_dir/path.name);names.append(path.name);bank_hashes[path.name]=sha(path)
 if not names:raise SystemExit('No bank inputs')
 bank_flags=['-DFMOD_PROBE_EVENT='+json.dumps(a.event),'-DFMOD_PROBE_BANK_FILES='+','.join(map(json.dumps,names))]
commands=[]
def run(cmd):commands.append(list(map(str,cmd)));subprocess.run(commands[-1],check=True)
flags=['-O2','-g','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE','-D__SWITCH__','-D_GNU_SOURCE','-DFMOD_PROBE_RELEASE',f'-I{out}',f'-I{sdk}/inc',f'-I{Path(os.environ["JAVA_HOME"]).resolve()}/include',f'-I{Path(os.environ["JAVA_HOME"]).resolve()}/include/linux',f'-I{a.libnx}/include','-I/opt/devkitpro/portlibs/switch/include','-Werror=incompatible-pointer-types','-Werror=implicit-function-declaration',*bank_flags]
objs=[]
for path in [src/'probe.c',src/'android.c',src/'jni.c',out/'so_util.c']:
 obj=out/(path.stem+'.o');run(['aarch64-none-elf-gcc',*flags,'-c',path,'-o',obj]);objs.append(obj)
run(['aarch64-none-elf-g++',f'-specs={a.libnx}/switch.specs',*flags,*objs,f'-L{a.libnx}/lib','-L/opt/devkitpro/portlibs/switch/lib','-Wl,--start-group','-lnx','-lpthread','-lm','-Wl,--end-group',f'-Wl,-Map,{out}/probe.map','-o',out/'probe.elf'])
run(['nacptool','--create','Celeste FMOD 1.10.14 control','Homebrew research','0.1',out/'probe.nacp'])
run(['elf2nro',out/'probe.elf',out/'celeste-fmod-11014.nro',f'--nacp={out}/probe.nacp'])
run(['gcc','-O2','-g','-Wl,-z,execstack','-D_GNU_SOURCE','-Werror=incompatible-pointer-types',f'-I{sdk}/inc',*bank_flags,src/'probe.c','-ldl','-lm','-o',out/'linux-probe'])
payload=out/'payload/lib';payload.mkdir(parents=True)
for path in (sdk/'android').glob('*.so'):shutil.copy2(path,payload/path.name)
manifest={'built_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fmod_version':'1.10.14','output_api':3,'bank_sha256':bank_hashes,'event':a.event,'archives':inputs,'loader_revision':revision,'sources':{p.name:sha(p) for p in src.iterdir() if p.is_file()},'sdk_files':{str(p.relative_to(sdk)):sha(p) for p in sdk.rglob('*') if p.is_file()},'libnx_sha256':sha(a.libnx/'lib/libnx.a'),'commands':commands,'unsupported_android_imports':unknown,'nro_sha256':sha(out/'celeste-fmod-11014.nro'),'linux_probe_sha256':sha(out/'linux-probe')}
(out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built',out,'fail-fast imports:',unknown)
