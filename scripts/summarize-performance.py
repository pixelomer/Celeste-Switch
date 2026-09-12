#!/usr/bin/env python3
"""Summarize closed SwitchPerformance records; retain inclusive timing semantics."""
import argparse
import collections
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('directory', type=Path)
p.add_argument('--first-window', type=int, help='Inclusive window index for a controlled condition')
p.add_argument('--last-window', type=int, help='Inclusive window index for a controlled condition')
a = p.parse_args()
records = []
for path in sorted(a.directory.glob('*.json')):
    value = json.loads(path.read_text())
    records.extend(value if isinstance(value, list) else [value])
starts = [v for v in records if v.get('kind') == 'start']
if len(starts) != 1: p.error('Expected exactly one run start record')
frequency = starts[0]['frequency']
groups = collections.defaultdict(list)
all_windows = {v['index']: v for v in records if v.get('kind') == 'window'}
for v in records:
    if v.get('kind') == 'window' and v['contextStart'] == v['contextEnd']:
        if a.first_window is not None and v['index'] < a.first_window: continue
        if a.last_window is not None and v['index'] > a.last_window: continue
        groups[v['contextEnd']].append(v)
summary = {'run': starts[0]['run'], 'hookFailures': [v for v in records if v.get('kind') == 'hook' and not v['success']],
           'windowBounds': [a.first_window, a.last_window],
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
    result = summary['scenes'][scene]
    gc = {key: 0 for key in ['gc0', 'gc1', 'gc2', 'allocatedBytes', 'gcPauseTicks']}
    gc_seconds = 0
    samples = {}
    sampled_frames = {'Update': sum(v.get('sampledUpdates', 0) for v in windows),
                      'Render': sum(v.get('sampledDraws', 0) for v in windows)}
    for v in windows:
        previous = all_windows.get(v['index']-1)
        if previous and previous['end'] == v['start']:
            gc_seconds += (v['end']-v['start'])/frequency
            for key in gc: gc[key] += v[key]-previous[key]
        for meter in v.get('entitySamples', []):
            row = samples.setdefault(meter['name'], {'count': 0, 'ticks': 0, 'maximumTicks': 0})
            row['count'] += meter['count']; row['ticks'] += meter['ticks']
            row['maximumTicks'] = max(row['maximumTicks'], meter['maximumTicks'])
    result['gcDeltas'] = dict(gc, measuredSeconds=gc_seconds, pauseMs=gc['gcPauseTicks']/10000)
    result['sampledFrames'] = sampled_frames
    result['entitySamples'] = sorted([
        {'name': name, 'calls': row['count'], 'totalMs': row['ticks']/frequency*1000,
         'meanMs': row['ticks']/frequency*1000/row['count'],
         'maxMs': row['maximumTicks']/frequency*1000,
         'msPerSampledFrame': row['ticks']/frequency*1000/sampled_frames[name.split(':', 1)[0]]
             if sampled_frames[name.split(':', 1)[0]] else None}
        for name, row in samples.items() if row['count']],
        key=lambda v: v['msPerSampledFrame'] or 0, reverse=True)
for kind in ['checksum', 'loadZip']:
    values = [v for v in records if v.get('kind') == kind]
    summary[kind] = sorted([{'file': v['file'], 'seconds': v['ticks']/frequency} for v in values],
                           key=lambda v: v['seconds'], reverse=True)
print(json.dumps(summary, indent=2))
