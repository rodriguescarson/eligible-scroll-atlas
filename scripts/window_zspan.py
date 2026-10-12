"""window_zspan.py <meshes-dir>
z span of every mesh and whether z-adjacent windows of one wrap overlap or leave a gap."""
import json, os, sys, glob
import numpy as np

root = sys.argv[1]
recs = []
for p in sorted(glob.glob(os.path.join(root, "*", "*", "meta.json"))):
    scroll, mesh = p.split(os.sep)[-3], p.split(os.sep)[-2]
    bb = json.load(open(p))["bbox"]
    z0, z1 = bb[0][2], bb[1][2]
    wrap = mesh.split("_")[1]
    recs.append(dict(scroll=scroll, mesh=mesh, wrap=wrap,
                     zwin=int(mesh.split("_")[0][1:]), z0=z0, z1=z1, span=z1 - z0))

spans = np.array([r["span"] for r in recs])
print(f"{len(recs)} meshes.  z span per mesh: median {np.median(spans):.0f} voxels, "
      f"range {spans.min():.0f}-{spans.max():.0f}")

gaps, overlaps = [], []
print(f"\n{'scroll':<10} {'wrap':<6} {'windows':>8} {'z covered':>12} {'median overlap':>15} {'gaps':>6}")
for scroll in sorted({r["scroll"] for r in recs}):
    for wrap in sorted({r["wrap"] for r in recs if r["scroll"] == scroll}):
        g = sorted([r for r in recs if r["scroll"] == scroll and r["wrap"] == wrap],
                   key=lambda r: r["zwin"])
        if len(g) < 2:
            continue
        ov = [g[i]["z1"] - g[i + 1]["z0"] for i in range(len(g) - 1)]
        ng = sum(1 for o in ov if o < 0)
        gaps += [o for o in ov if o < 0]; overlaps += [o for o in ov if o >= 0]
        cov = g[-1]["z1"] - g[0]["z0"]
        print(f"{scroll:<10} {wrap:<6} {len(g):>8} {cov:>11.0f}v {np.median(ov):>14.0f}v {ng:>6}")

print(f"\nadjacent-window joins: {len(overlaps)} overlap, {len(gaps)} gap")
if overlaps:
    o = np.array(overlaps)
    print(f"  overlap: median {np.median(o):.0f} voxels, min {o.min():.0f}, max {o.max():.0f}")
if gaps:
    print(f"  gaps:    {sorted(round(x) for x in gaps)}")
