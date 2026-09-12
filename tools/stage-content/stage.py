#!/usr/bin/env python3
"""Snapshot only game Content from a supplied PC ZIP; never execute its files."""
import argparse,hashlib,json,shutil,stat,zipfile
from pathlib import Path,PurePosixPath
p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
a.output=a.output.resolve()
if a.output.exists():p.error('Use a new staging directory')
with zipfile.ZipFile(a.archive) as z:
 entries=[];seen=set();total=0
 for info in z.infolist():
  if not info.filename.startswith('Content/') or info.is_dir():continue
  name=PurePosixPath(info.filename)
  if '\\' in info.filename or any(ord(c)<32 for c in info.filename) or name.is_absolute() or '..' in name.parts:raise SystemExit('Unsafe content path')
  if stat.S_ISLNK(info.external_attr>>16):raise SystemExit('Symlink input rejected')
  folded=str(name).casefold()
  if folded in seen:raise SystemExit('Duplicate/case-colliding content path')
  seen.add(folded);total+=info.file_size
  if info.file_size>600*1024**2 or total>2*1024**3:raise SystemExit('Unexpected content size')
  entries.append(info)
 if not entries:raise SystemExit('No PC Content entries')
 a.output.mkdir(parents=True)
 records=[]
 for info in entries:
  dest=a.output/info.filename;dest.parent.mkdir(parents=True,exist_ok=True)
  with z.open(info) as source,dest.open('xb') as target:shutil.copyfileobj(source,target,1024*1024)
  with dest.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
  if dest.stat().st_size!=info.file_size:raise SystemExit('Truncated content')
  records.append({'path':info.filename,'bytes':info.file_size,'sha256':digest})
with a.archive.open('rb') as stream:archive_hash=hashlib.file_digest(stream,'sha256').hexdigest()
(a.output/'content-manifest.json').write_text(json.dumps({'archive_sha256':archive_hash,'file_count':len(records),'total_bytes':total,'files':records},indent=2)+'\n')
print('Staged',len(records),'content files,',total,'bytes; no executable launched')
