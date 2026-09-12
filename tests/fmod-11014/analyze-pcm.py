#!/usr/bin/env python3
"""Check finite PCM, energy, and the 440 Hz probe tone without extra packages."""
import array,math,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);result={}
for name in ('tone','music'):
 if name == 'music' and not (root/'music.f32').exists():continue
 data=array.array('f');data.frombytes((root/(name+'.f32')).read_bytes())
 if sys.byteorder!='little':data.byteswap()
 finite=all(math.isfinite(x) for x in data)
 if not finite or not data:raise RuntimeError(f'{name}: invalid PCM')
 rms=math.sqrt(sum(x*x for x in data)/len(data));peak=max(map(abs,data))
 result[name]={'frames':len(data)//2,'seconds':len(data)/96000,'rms':rms,'peak':peak,'finite':finite}
 if name=='tone':
  # Ignore startup/filter settling. Goertzel scan across expected frequency.
  samples=[(data[i]+data[i+1])/2 for i in range(8192,min(len(data),8192+48000),2)]
  spectrum={}
  for hz in range(420,461):
   coeff=2*math.cos(2*math.pi*hz/48000);a=b=0.
   for v in samples:a,b=v+coeff*a-b,a
   spectrum[hz]=a*a+b*b-coeff*a*b
  result[name]['dominant_hz_420_460']=max(spectrum,key=spectrum.get)
  assert abs(result[name]['dominant_hz_420_460']-440)<=1
 assert peak>1e-5
print(json.dumps(result,indent=2))
