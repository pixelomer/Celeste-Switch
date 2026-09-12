#!/usr/bin/env python3
"""Run the local licensed Linux reference unprivileged, without network or host data."""
import argparse, os, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
a.build=a.build.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
if os.getuid()!=0:raise SystemExit('This runner requires root to switch to UID/GID 65534 before isolation')
os.chown(a.output,65534,65534)
command=['setpriv','--reuid','65534','--regid','65534','--clear-groups','--no-new-privs','bwrap','--die-with-parent','--unshare-all','--ro-bind','/usr','/usr','--symlink','usr/lib64','/lib64','--symlink','usr/lib','/lib','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(a.build/'sdk'),'/sdk','--ro-bind',str(a.build/'linux-probe'),'/probe','--bind',str(a.output),'/output','--chdir','/output','--clearenv','--setenv','LD_LIBRARY_PATH','/sdk/linux','/probe']
if (a.build/'payload/banks').is_dir():
 command[-1:-1]=['--ro-bind',str(a.build/'payload/banks'),'/banks']
with (a.output/'stdout.txt').open('w') as log:
 result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=90)
raise SystemExit(result.returncode)
