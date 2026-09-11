#!/usr/bin/env python3
"""Check original Switch probe logs against the exact local build inputs."""
import argparse
import hashlib
import json
import re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build', required=True, type=Path, help='Directory containing host/build-manifest.json')
p.add_argument('--logs', required=True, type=Path, help='runtime.txt, stdout.txt, stderr.txt')
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
manifest = json.loads((a.build / 'host/build-manifest.json').read_text())
stdout = (a.logs / 'stdout.txt').read_text()
runtime = (a.logs / 'runtime.txt').read_text()
stderr = (a.logs / 'stderr.txt').read_text()
observed = {}
for line in stdout.splitlines():
    if not line.startswith('INPUT '):
        continue
    match = re.fullmatch(r'INPUT (.+) (\d+) ([0-9a-f]{16})', line)
    if not match or match[1] in observed:
        raise SystemExit('Malformed or duplicate input record: ' + line)
    observed[match[1]] = [int(match[2]), match[3]]
expected = {}
for file in (a.build / 'host/managed').glob('*.dll'):
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest['managed_sha256'][file.name]:
        raise SystemExit('Local input differs from build manifest: ' + file.name)
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    expected[file.name] = [len(data), f'{value:016x}']
if set(expected) != set(manifest['managed_sha256']) or not expected or observed != expected:
    raise SystemExit('Target input checksums do not match local inputs')
if stderr or 'END FAIL' in stdout or 'END PASS Horizon hook gate' not in stdout:
    raise SystemExit('Probe failed or stderr is nonempty')
for marker in ('coreclr_execute_assembly result=00000000 exit=100', 'coreclr_shutdown result=00000000 exit=100'):
    if marker not in runtime:
        raise SystemExit('Missing successful lifecycle marker: ' + marker)
summary = {
    'result': 'PASS', 'assembly_count': len(expected),
    'checks': [line[5:] for line in stdout.splitlines() if line.startswith('PASS ')],
    'target_integrity': 'FNV-1a-64 and length; not a cryptographic signature',
    'nro_sha256': hashlib.sha256((a.build / 'host/coreclr-host-probe.nro').read_bytes()).hexdigest(),
    'build_manifest_sha256': hashlib.sha256((a.build / 'host/build-manifest.json').read_bytes()).hexdigest(),
    'log_sha256': {name: hashlib.sha256((a.logs / name).read_bytes()).hexdigest() for name in ('runtime.txt', 'stdout.txt', 'stderr.txt')},
}
a.output.write_text(json.dumps(summary, indent=2) + '\n')
print(f"PASS {len(expected)} target assemblies, {len(summary['checks'])} checks, execute and shutdown")
