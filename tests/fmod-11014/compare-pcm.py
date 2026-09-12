#!/usr/bin/env python3
"""Compare matching stereo float32 captures (local test output only)."""
import array,math,json,pathlib,sys
left,right=map(pathlib.Path,sys.argv[1:]);result={}
for name in ('tone','music'):
 if name == 'music' and not (left/'music.f32').exists() and not (right/'music.f32').exists():continue
 a=array.array('f');a.frombytes((left/(name+'.f32')).read_bytes())
 b=array.array('f');b.frombytes((right/(name+'.f32')).read_bytes())
 if sys.byteorder!='little':a.byteswap();b.byteswap()
 assert len(a)==len(b) and a
 assert all(math.isfinite(v) for v in a) and all(math.isfinite(v) for v in b)
 energy_a=sum(x*x for x in a);energy_b=sum(x*x for x in b)
 result[name]={'samples':len(a),'max_abs_difference':max(abs(x-y) for x,y in zip(a,b)),'rms_difference':math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/len(a)),'correlation':sum(x*y for x,y in zip(a,b))/math.sqrt(energy_a*energy_b)}
 assert result[name]['correlation']>0.9999
print(json.dumps(result,indent=2))
