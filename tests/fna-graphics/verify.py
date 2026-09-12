#!/usr/bin/env python3
"""Match graphics results and target SHA-256 readbacks to the exact build."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('build','logs','deployment-manifest','deployment-log','output'): p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--lifecycle',action='store_true')
a=p.parse_args()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
build=json.loads((a.build/'host/build-manifest.json').read_text())
deploy=json.loads(a.deployment_manifest.read_text())
expected={v['destination']:v['sha256'] for v in deploy['files']}
local={}
for path in (a.build/'host/managed').glob('*.dll'):
    digest=sha(path)
    if digest!=build['managed_sha256'].get(path.name): raise SystemExit('Changed local DLL: '+path.name)
    local['sdmc:'+build['managed_directory']+'/'+path.name]=digest
if local!=expected or len(local)!=len(build['managed_sha256']): raise SystemExit('Deployment manifest differs from build')
lines=a.deployment_log.read_text().splitlines(); actual={}; copied=0
if not lines or lines[0]!='BEGIN payload deployment manifest='+deploy['id']: raise SystemExit('Wrong deployment identity')
for line in lines[1:-1]:
    parts=line.split(' ',3)
    if len(parts)!=4 or parts[0]!='VERIFIED' or parts[1] not in ('existing','copied') or parts[3] in actual: raise SystemExit('Invalid deployment result')
    actual[parts[3]]=parts[2]; copied+=parts[1]=='copied'
if actual!=expected or lines[-1]!=f'END deployment verified={len(expected)} copied={copied} failures=0': raise SystemExit('Incomplete or wrong target readback')
stdout=(a.logs/'stdout.txt').read_text(); runtime=(a.logs/'runtime.txt').read_text(); stderr=(a.logs/'stderr.txt').read_text()
checks=[v[5:] for v in stdout.splitlines() if v.startswith('PASS ')]
count=21 if a.lifecycle else 17
if len(checks)!=count or 'END PASS checks='+str(count) not in stdout or 'FAIL' in stdout or stderr: raise SystemExit('Graphics assertions failed/incomplete')
if 'FNA3D Driver: OpenGL' not in stdout: raise SystemExit('Wrong graphics backend')
if a.lifecycle and ('INPUT A received' not in stdout or not any(v.startswith('Horizon resume notification count=') for v in checks)): raise SystemExit('Missing input or native resume evidence')
for marker in ('coreclr_execute_assembly result=00000000 exit=100','coreclr_shutdown result=00000000 exit=100'):
    if marker not in runtime: raise SystemExit('Runtime did not complete normally')
summary={'result':'PASS','checks':checks,'assembly_count':len(local),'target_integrity':'Full SHA-256 readback against host manifest',
    'nro_sha256':sha(a.build/'celeste-fna-probe.nro'),'build_manifest_sha256':sha(a.build/'host/build-manifest.json'),
    'deployment_manifest_id':deploy['id'],'log_sha256':{n:sha(a.logs/n) for n in ('stdout.txt','stderr.txt','runtime.txt')}}
a.output.write_text(json.dumps(summary,indent=2)+'\n')
print('PASS',len(checks),'checks,',len(local),'target DLLs, normal runtime shutdown')
