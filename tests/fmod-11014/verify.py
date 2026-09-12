#!/usr/bin/env python3
"""Verify FMOD version, target payload identity, completion and captured PCM."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('build','deployment-manifest','deployment-log','switch-log','switch-pcm','linux-pcm','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();src=Path(__file__).resolve().parent
build=json.loads((a.build/'build-manifest.json').read_text());deploy=json.loads(a.deployment_manifest.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if build['fmod_version']!='1.10.14' or build['output_api']!=3:raise SystemExit('Wrong FMOD version/API')
if sha(a.build/'celeste-fmod-11014.nro')!=build['nro_sha256']:raise SystemExit('NRO changed')
expected={}
for name in ('libfmod.so','libfmodstudio.so'):
 expected['sdmc:/switch/celeste-fmod-11014/lib/'+name]=build['sdk_files']['android/'+name]
for name,digest in build['bank_sha256'].items():expected['sdmc:/switch/celeste-fmod-11014/banks/'+name]=digest
if {f['destination']:f['sha256'] for f in deploy['files']}!=expected or len(deploy['files'])!=len(expected):raise SystemExit('Deployment differs from build inputs')
lines=a.deployment_log.read_text().splitlines()
if lines[0]!='BEGIN payload deployment manifest='+deploy['id']:raise SystemExit('Wrong target deployment log')
actual={};copied=0
for line in lines[1:-1]:
 parts=line.split(' ',3)
 if len(parts)!=4 or parts[0]!='VERIFIED' or parts[1] not in ('copied','existing') or parts[3] in actual:raise SystemExit('Invalid target readback')
 actual[parts[3]]=parts[2];copied+=parts[1]=='copied'
if actual!=expected or lines[-1]!=f'END deployment verified={len(expected)} copied={copied} failures=0':raise SystemExit('Incomplete target verification')
log=a.switch_log.read_text()
for marker in ('FMOD_PROBE VERSION 11014','FMOD_PROBE PASS silent initialization and release','FMOD_PROBE PCM tone frames=96256','FMOD_PROBE audout released=','FMOD_PROBE DONE'):
 if marker not in log:raise SystemExit('Missing '+marker)
if 'FAIL' in log:raise SystemExit('Target failure')
count=int(re.search(r'audout released=(\d+)',log)[1])
if count<94:raise SystemExit('Incomplete output')
if build['event'] and ('FMOD_PROBE selected '+build['event'] not in log or 'FMOD_PROBE PCM music frames=768000' not in log):raise SystemExit('Missing bank event')
analyses={}
for platform,folder in [('switch',a.switch_pcm),('linux',a.linux_pcm)]:
 analyses[platform]=json.loads(subprocess.check_output([sys.executable,str(src/'analyze-pcm.py'),str(folder)],text=True))
comparison=json.loads(subprocess.check_output([sys.executable,str(src/'compare-pcm.py'),str(a.linux_pcm),str(a.switch_pcm)],text=True))
result={'result':'pass','scope':'Native tone/bank PCM and audout completion; HOME/exit checked separately','nro_sha256':build['nro_sha256'],'deployment_id':deploy['id'],'files_verified':len(expected),'log_sha256':sha(a.switch_log),'audout_released':count,'analysis':analyses,'comparison':comparison}
a.output.write_text(json.dumps(result,indent=2)+'\n');print('PASS native FMOD 1.10.14,',len(expected),'files,',count,'audout releases, reference PCM comparison')
