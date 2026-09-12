#!/usr/bin/env python3
"""Build KeraLua's pinned Lua 5.4 native dependency for Horizon from public source."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
import dnfile
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','keralua','libnx','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
for key,value in vars(a).items():setattr(a,key,value.resolve())
revision=subprocess.check_output(['git','-C',str(a.source),'rev-parse','HEAD'],text=True).strip()
if revision!='995a493cbbcaadceab6b080cd23d8555e7747efa':raise SystemExit('Expected KeraLua1.4.7 Lua source pin')
if subprocess.check_output(['git','-C',str(a.source),'status','--porcelain'],text=True).strip():raise SystemExit('Lua source tree must be clean')
a.output.mkdir(parents=True,exist_ok=False)
snapshot=a.output/'source';snapshot.mkdir()
for folder in ('src','include'):shutil.copytree(a.source/folder,snapshot/folder)
commands=[];objects=[]
def run(cmd):commands.append(list(map(str,cmd)));subprocess.run(commands[-1],check=True)
# Upstream generic C configuration: no POSIX process or dynamic-library claims.
for source in sorted((snapshot/'src').glob('*.c')):
 if source.name in ('lua.c','luac.c','android_strpcpy.c'):continue
 obj=a.output/(source.stem+'.o')
 run(['aarch64-none-elf-gcc','-O2','-g','-fexceptions','-fno-omit-frame-pointer','-ffunction-sections','-fdata-sections','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE','-D__SWITCH__','-I'+str(snapshot/'include'),'-I'+str(a.libnx/'include'),'-c',source,'-o',obj]);objects.append(obj)
archive=a.output/'liblua54.a';run(['aarch64-none-elf-ar','rcs',archive,*objects])
nm=subprocess.check_output(['aarch64-none-elf-nm','-g','--defined-only',str(archive)],text=True)
exports=sorted({line.split()[-1] for line in nm.splitlines() if len(line.split())==3 and line.split()[-1].startswith(('lua_','luaL_','luaopen_'))})
pe=dnfile.dnPE(str(a.keralua));imports={str(r.ImportName) for r in pe.net.mdtables.ImplMap.rows};pe.close()
missing=imports-set(exports)
if missing:raise SystemExit('Missing KeraLua imports: '+str(sorted(missing)))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
manifest={'revision':revision,'version':'5.4.8','keralua_sha256':sha(a.keralua),'keralua_imports':sorted(imports),'exports':exports,'archive_sha256':sha(archive),'source_sha256':{str(p.relative_to(snapshot)):sha(p) for p in snapshot.rglob('*') if p.is_file()},'commands':commands,'libnx_sha256':sha(a.libnx/'lib/libnx.a')}
(a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Lua5.4.8 built; all '+str(len(imports))+' KeraLua imports present')
