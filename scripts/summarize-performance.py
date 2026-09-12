#!/usr/bin/env python3
"""Summarize closed SwitchPerformance records; retain inclusive timing semantics."""
import argparse
import collections
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('directory', type=Path)
a = p.parse_args()
records = [json.loads(v.read_text()) for v in sorted(a.directory.glob('*.json'))]
starts = [v for v in records if v.get('kind') == 'start']
if len(starts) != 1: p.error('Expected exactly one run start record')
frequency = starts[0]['frequency']
groups = collections.defaultdict(list)
for v in records:
    if v.get('kind') == 'window' and v['contextStart'] == v['contextEnd']:
        groups[v['contextEnd']].append(v)
summary = {'run': starts[0]['run'], 'hookFailures': [v for v in records if v.get('kind') == 'hook' and not v['success']],
           'snapshotFailures': [v for v in records if v.get('kind') == 'snapshotFailure'],
           'dropped': max((v.get('dropped', 0) for v in records), default=0), 'scenes': {}}
for scene, windows in groups.items():
    seconds = sum(v['end']-v['start'] for v in windows)/frequency
    totals = {}
    for v in windows:
        for meter in v['meters']:
            row = totals.setdefault(meter['name'], {'count': 0, 'ticks': 0, 'maximumTicks': 0, 'histogram': [0]*128})
            row['count'] += meter['count']; row['ticks'] += meter['ticks']
            row['maximumTicks'] = max(row['maximumTicks'], meter['maximumTicks'])
            row['histogram'] = [x+y for x, y in zip(row['histogram'], meter['histogram'])]
    phases = {}
    for name, row in totals.items():
        if not row['count']: continue
        seen = 0; p95 = None
        for i, n in enumerate(row['histogram']):
            seen += n
            if seen >= row['count']*.95:
                p95 = '>=31.75' if i == 127 else round((i+1)*.25, 2)
                break
        phases[name] = {'calls': row['count'], 'meanMs': row['ticks']/frequency*1000/row['count'],
                        'maxMs': row['maximumTicks']/frequency*1000, 'p95UpperMs': p95,
                        'inclusiveMsPerSecond': row['ticks']/frequency*1000/seconds}
    summary['scenes'][scene] = {'windows': len(windows), 'seconds': seconds,
                              'drawFps': totals.get('Engine.Draw', {}).get('count', 0)/seconds,
                              'entitiesRange': [min(v['entities'] or 0 for v in windows), max(v['entities'] or 0 for v in windows)],
                              'phases': phases}
for kind in ['checksum', 'loadZip']:
    values = [v for v in records if v.get('kind') == kind]
    summary[kind] = sorted([{'file': v['file'], 'seconds': v['ticks']/frequency} for v in values],
                           key=lambda v: v['seconds'], reverse=True)
print(json.dumps(summary, indent=2))
