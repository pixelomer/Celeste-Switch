#!/usr/bin/env python3
"""Build owned net8/net9 fixtures and a .NET 10 host against an explicit MonoMod build."""
import argparse, hashlib, json, os, shutil, subprocess
from xml.sax.saxutils import escape
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--monomod', type=Path, required=True)
p.add_argument('--output', type=Path, help='New directory for this control; existing output is rejected')
p.add_argument('--nuget-packages', type=Path, default=Path(os.environ.get('NUGET_PACKAGES', str(Path.home()/'.nuget/packages'))))
a = p.parse_args()
here = Path(__file__).resolve().parent
out = a.output.resolve() if a.output else here.parents[1]/'artifacts/runtime-hooks-host'
if a.output and out.exists(): p.error('--output must be a new directory')
out.mkdir(parents=True, exist_ok=True)
(out/'Directory.Build.props').write_text('<Project />\n')
(out/'Directory.Build.targets').write_text('<Project />\n')
(out/'global.json').write_text(json.dumps({'sdk': {'version': '10.0.111', 'rollForward': 'disable'}}))
for target in ('net8.0', 'net9.0'):
    d = out/target; d.mkdir(exist_ok=True)
    shutil.copyfile(here/'Fixture.cs', d/'Fixture.cs')
    (d/'Fixture.csproj').write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>{target}</TargetFramework><AssemblyName>OwnedHookFixture</AssemblyName><EnableNETAnalyzers>false</EnableNETAnalyzers></PropertyGroup></Project>')
    subprocess.run(['dotnet','build','-c','Release'],cwd=d,check=True)
d = out/'host'; d.mkdir(exist_ok=True)
shutil.copyfile(here/'Program.cs', d/'Program.cs')
deps = json.loads((a.monomod/'MonoMod.RuntimeDetour.deps.json').read_text())
closure = {}
for identity, details in deps['targets'][deps['runtimeTarget']['name']].items():
    library = deps['libraries'][identity]
    for asset in details.get('runtime', {}):
        if not asset.endswith('.dll'): continue
        path = (a.nuget_packages/library['path']/asset if library['type'] == 'package' else a.monomod/Path(asset).name).resolve()
        if not path.is_file(): raise SystemExit(f'Missing declared dependency: {path}')
        if path.name in closure and closure[path.name].read_bytes() != path.read_bytes(): raise SystemExit(f'Dependency collision: {path.name}')
        closure[path.name] = path
refs = ''.join(f'<Reference Include="{escape(p.stem)}"><HintPath>{escape(str(p))}</HintPath></Reference>' for p in closure.values())
(d/'Host.csproj').write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType><Nullable>enable</Nullable></PropertyGroup><ItemGroup>{refs}</ItemGroup></Project>')
subprocess.run(['dotnet','build','-c','Release'],cwd=d,check=True)
for dll in closure.values(): shutil.copyfile(dll,d/'bin/Release/net10.0'/dll.name)
command=['dotnet',str(d/'bin/Release/net10.0/Host.dll'),*[str(out/t/'bin/Release'/t/'OwnedHookFixture.dll') for t in ('net8.0','net9.0')]]
manifest={'command':command,'control':os.environ.get('CELESTE_HOOK_CONTROL'),'shape':os.environ.get('CELESTE_HOOK_SHAPE','collectible-target'),'diagnostic_wait':os.environ.get('CELESTE_HOOK_WAIT') == '1','source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in here.iterdir() if p.is_file()},'dependency_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in closure.values()}}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with (out/'result.txt').open('w') as log: result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
print((out/'result.txt').read_text());raise SystemExit(result.returncode)
