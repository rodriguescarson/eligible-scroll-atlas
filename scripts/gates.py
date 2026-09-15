#!/usr/bin/env python3
"""Join pscamillo's index.csv with TAUIL's per-mesh alignment into one gate table.

Keys: index.csv 'path' is meshes/<scroll>/<zNNN_wNNN>; TAUIL's JSON is keyed
<scroll>_<zNNN_wNNN>. Nothing is excluded here; the columns are the gates the
pre-registration names, and every downstream table cites this one.
"""
import csv, json, statistics, sys
idx = list(csv.DictReader(open('data/pscamillo_index.csv')))
al = json.load(open('data/tauil_mesh_alignment.json'))
meshes = al.get('meshes', al) if isinstance(al, dict) else {}
def key(p): return p.split('/', 1)[1].replace('/', '_')
rows = []
for r in idx:
    k = key(r['path']); a = meshes.get(k) or {}
    ang = a.get('median_angle_deg', a.get('median_deg', a.get('median')))
    try: ang = float(ang) if ang is not None else None
    except (TypeError, ValueError): ang = None
    rows.append({
        'mesh': k, 'scroll': r['scroll'], 'window_z': r['window_z'], 'wrap': r['wrap'],
        'area_cm2': r['area_cm2'], 'verdict': r['gate_verdict'],
        'median_angle_deg': '' if ang is None else f'{ang:.2f}',
        'aligned_lt30': '' if ang is None else str(ang < 30), 'reprova': str(r['gate_verdict'] == 'reprova'),
        'path': r['path'],
    })
with open('data/gates.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
n = len(rows); meas = [r for r in rows if r['median_angle_deg']]
lt30 = [r for r in meas if r['aligned_lt30'] == 'True']
ok = [r for r in lt30 if r['reprova'] == 'False']
print(f'meshes {n} | angle measured {len(meas)} | aligned<30 {len(lt30)} | aligned<30 and not reprova {len(ok)} | reprova {sum(r["reprova"]=="True" for r in rows)}')
if meas: print('median of medians', round(statistics.median(float(r['median_angle_deg']) for r in meas), 2), 'deg')
