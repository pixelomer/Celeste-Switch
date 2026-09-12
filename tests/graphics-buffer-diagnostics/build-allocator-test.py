#!/usr/bin/env python3
"""Build original/fixed Mesa allocator fault injection without game or GPU code."""
import argparse, hashlib, json, shlex, shutil, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('mesa-build','libnx','output'): p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--fixed',action='store_true')
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent
entries=json.loads((a.mesa_build/'compile_commands.json').read_text())
entry,=[e for e in entries if e['file'].endswith('/nouveau/nouveau_mm.c')]
cwd=Path(entry['directory']);source=(cwd/entry['file']).resolve()
if a.fixed:
 subprocess.run(['patch','--batch','--fuzz=0','-o',str(out/'nouveau_mm.c'),str(source),str(here.parents[1]/'native/mesa/nouveau-mm-failure.patch')],check=True)
else: shutil.copy2(source,out/'nouveau_mm.c')
shutil.copy2(here/'allocator-test.c',out/'allocator-test.c')
command=[];skip=False
for item in shlex.split(entry['command']):
 if skip:skip=False;continue
 if item in ('-o','-MF','-MQ'):skip=True;continue
 if item in ('-MD','-c',entry['file']):continue
 command.append(item)
obj=out/'test.o';sdk=a.libnx.resolve()
command += ['-I'+str(source.parent),'-I'+str(sdk/'include'),'-DTEST_FIXED='+str(int(a.fixed)),'-g','-c',str(out/'allocator-test.c'),'-o',str(obj)]
subprocess.run(command,cwd=cwd,check=True)
target=out/('mesa-allocator-fixed' if a.fixed else 'mesa-allocator-original')
subprocess.run(['aarch64-none-elf-gcc','-march=armv8-a+crc+crypto','-mtp=soft','-fPIE','-specs='+str(sdk/'switch.specs'),'-Wl,--gc-sections','-Wl,-Map,'+str(target.with_suffix('.map')),str(obj),'-L'+str(sdk/'lib'),'-lnx','-o',str(target.with_suffix('.elf'))],check=True)
subprocess.run(['nacptool','--create','Mesa allocator failure probe','Homebrew runtime research','1.0.0',str(target.with_suffix('.nacp'))],check=True)
subprocess.run(['elf2nro',str(target.with_suffix('.elf')),str(target.with_suffix('.nro')),'--nacp='+str(target.with_suffix('.nacp'))],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'manifest.json').write_text(json.dumps({'fixed':a.fixed,'command':command,'source_sha256':sha(out/'nouveau_mm.c'),'test_sha256':sha(out/'allocator-test.c'),'nro_sha256':sha(target.with_suffix('.nro')),'sdk_sha256':sha(sdk/'lib/libnx.a')},indent=2)+'\n')
print(target.with_suffix('.nro'))
