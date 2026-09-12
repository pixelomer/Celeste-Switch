#!/usr/bin/env python3
"""Run the source-built standard Everest installer in an isolated game copy."""
import argparse,hashlib,json,os,shutil,subprocess,zipfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('pc-zip','everest-publish','installer-build','fna','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
for key,value in vars(a).items():setattr(a,key,value.resolve())
if os.getuid()!=0:raise SystemExit('This runner requires root initially and runs the installer as UID/GID 65534')
a.output.mkdir(parents=True,exist_ok=False)
install=a.output/'install';shutil.copytree(a.everest_publish,install)
shutil.copytree(a.installer_build,install,dirs_exist_ok=True)
inputs={}
with zipfile.ZipFile(a.pc_zip) as z:
 for name in ('Celeste.exe','Celeste.Content.dll','FNA.dll','Celeste.exe.config','FNA.dll.config'):
  if name not in z.namelist():
   if name.endswith('.config'):continue
   raise SystemExit('Missing PC input '+name)
  data=z.read(name);(install/name).write_bytes(data);inputs[name]=hashlib.sha256(data).hexdigest()
# Use the paired source-built FNA port for the standard installer FNA patch step.
shutil.copy2(a.fna,install/'everest-lib/FNA.dll')
(install/'Content').mkdir(exist_ok=True)
for path in [install,*install.rglob('*')]:
 if not path.is_symlink():os.chown(path,65534,65534)
command=['setpriv','--reuid','65534','--regid','65534','--clear-groups','--no-new-privs','bwrap','--die-with-parent','--unshare-all','--ro-bind','/usr','/usr','--symlink','usr/lib64','/lib64','--symlink','usr/lib','/lib','--dev','/dev','--ro-bind','/proc','/proc','--tmpfs','/tmp','--bind',str(install),'/install','--chdir','/install','--clearenv','--setenv','PATH','/usr/bin:/usr/sbin','--setenv','MINIINSTALLER_PLATFORM','Linux','--setenv','DOTNET_ROLL_FORWARD','LatestMajor','/usr/bin/dotnet','/install/MiniInstaller.dll']
(a.output/'inputs.json').write_text(json.dumps({'pc_inputs':inputs,'fna_sha256':hashlib.sha256(a.fna.read_bytes()).hexdigest(),'command':command},indent=2)+'\n')
with (a.output/'stdout.txt').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300)
if r.returncode:raise SystemExit(r.returncode)
outputs={}
for name in ('Celeste.dll','FNA.dll','MMHOOK_Celeste.dll'):
 path=install/name
 if not path.is_file():raise SystemExit('Missing installer output '+name)
 outputs[name]=hashlib.sha256(path.read_bytes()).hexdigest()
(a.output/'outputs.json').write_text(json.dumps(outputs,indent=2)+'\n');print('Standard Everest installer completed; game entry not invoked')
