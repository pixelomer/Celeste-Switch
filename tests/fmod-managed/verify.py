#!/usr/bin/env python3
"""Match combined runtime results to managed and licensed-native payload hashes."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('build','audio-build','logs','managed-manifest','managed-log','audio-manifest','audio-log','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def deployment(manifest,log,expected):
 m=json.loads(manifest.read_text());lines=log.read_text().splitlines()
 if {v['destination']:v['sha256'] for v in m['files']}!=expected or len(m['files'])!=len(expected):raise SystemExit('Wrong payload')
 if not lines or lines[0]!='BEGIN payload deployment manifest='+m['id']:raise SystemExit('Wrong target identity')
 actual={};copied=0
 for line in lines[1:-1]:
  parts=line.split(' ',3)
  if len(parts)!=4 or parts[0]!='VERIFIED' or parts[1] not in ('existing','copied') or parts[3] in actual:raise SystemExit('Invalid target result')
  actual[parts[3]]=parts[2];copied+=parts[1]=='copied'
 if actual!=expected or lines[-1]!=f'END deployment verified={len(expected)} copied={copied} failures=0':raise SystemExit('Incomplete target hashes')
 return m['id']
b=json.loads((a.build/'host/build-manifest.json').read_text());i=json.loads((a.build/'integration-manifest.json').read_text());audio=json.loads((a.audio_build/'build-manifest.json').read_text())
if sha(a.build/'celeste-audio-managed.nro')!=i['nro_sha256']:raise SystemExit('Changed NRO')
expected={}
for name,digest in b['managed_sha256'].items():
 if sha(a.build/'host/managed'/name)!=digest:raise SystemExit('Changed managed assembly')
 expected['sdmc:'+b['managed_directory']+'/'+name]=digest
managed_id=deployment(a.managed_manifest,a.managed_log,expected)
expected={}
for name in ('libfmod.so','libfmodstudio.so'):expected['sdmc:/switch/celeste-fmod-11014/lib/'+name]=audio['sdk_files']['android/'+name]
for name,digest in audio['bank_sha256'].items():expected['sdmc:/switch/celeste-fmod-11014/banks/'+name]=digest
audio_id=deployment(a.audio_manifest,a.audio_log,expected)
stdout=(a.logs/'stdout.txt').read_text();runtime=(a.logs/'runtime.txt').read_text();stderr=(a.logs/'stderr.txt').read_text()
checks=[line[5:] for line in stdout.splitlines() if line.startswith('PASS ')]
if len(checks)!=11 or 'END PASS checks=11' not in stdout or 'FAIL' in stdout or stderr:raise SystemExit('Incomplete/failed integration')
for marker in ('coreclr_execute_assembly result=00000000 exit=100','coreclr_shutdown result=00000000 exit=100'):
 if marker not in runtime:raise SystemExit('Abnormal runtime completion')
result={'result':'pass','scope':'FNA/actual Celeste FMOD bindings/native asynchronous output; game entry not invoked','nro_sha256':i['nro_sha256'],'managed_count':len(b['managed_sha256']),'native_files':len(expected),'managed_deployment':managed_id,'native_deployment':audio_id,'checks':checks,'log_sha256':{name:sha(a.logs/name) for name in ('stdout.txt','stderr.txt','runtime.txt')}}
a.output.write_text(json.dumps(result,indent=2)+'\n');print('PASS 11 checks;',len(b['managed_sha256']),'managed and',len(expected),'native/data files verified; normal runtime shutdown')
