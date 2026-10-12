"""window_stitch_runs.py <meshes-dir>
Longest unbroken run of overlapping z windows per scroll and wrap, i.e. the tallest sheet that
could be assembled from published meshes if the layers matched. Read together with
window_layer_drift.py, which shows they mostly do not."""
import json, os, sys, glob
import numpy as np

UM = 8.64
root = sys.argv[1]
recs = []
for p in sorted(glob.glob(os.path.join(root, "*", "*", "meta.json"))):
    scroll, mesh = p.split(os.sep)[-3], p.split(os.sep)[-2]
    bb = json.load(open(p))["bbox"]
    recs.append(dict(scroll=scroll, mesh=mesh, wrap=mesh.split("_")[1],
                     zwin=int(mesh.split("_")[0][1:]), z0=bb[0][2], z1=bb[1][2]))

best = []
print(f"{'scroll':<10} {'wrap':<6} {'win':>4} {'longest run':>12} {'stitched height':>17}")
for scroll in sorted({r["scroll"] for r in recs}):
    for wrap in sorted({r["wrap"] for r in recs if r["scroll"] == scroll}):
        g = sorted([r for r in recs if r["scroll"] == scroll and r["wrap"] == wrap],
                   key=lambda r: r["zwin"])
        # walk the chain, breaking wherever the next window does not overlap the current one
        runs, cur = [], [g[0]]
        for a, b in zip(g, g[1:]):
            if b["z0"] <= a["z1"]:
                cur.append(b)
            else:
                runs.append(cur); cur = [b]
        runs.append(cur)
        r = max(runs, key=lambda c: c[-1]["z1"] - c[0]["z0"])
        h = (r[-1]["z1"] - r[0]["z0"]) * UM / 10000
        best.append(dict(scroll=scroll, wrap=wrap, n=len(r), cm=h,
                         z0=r[0]["zwin"], z1=r[-1]["zwin"]))
        print(f"{scroll:<10} {wrap:<6} {len(g):>4} {len(r):>8} win {h:>14.2f} cm")

b = max(best, key=lambda x: x["cm"])
print(f"\ntallest assemblable sheet: {b['scroll']}/{b['wrap']}  "
      f"{b['n']} windows z{b['z0']}..z{b['z1']}  =  {b['cm']:.2f} cm")
print(f"Nieuwlaar's winning segment: 2.12 cm")
print(f"single window as published:  0.69 cm (best of 227)")
cm = np.array([x["cm"] for x in best])
print(f"\nof the {len(best)} scroll-wrap columns, {(cm >= 2.12).sum()} reach 2.12 cm, "
      f"{(cm >= 1.0).sum()} reach 1.0 cm")
print(f"median {np.median(cm):.2f} cm")
# how many windows to clear Nieuwlaar
print("\nwindows needed to clear 2.12 cm, at ~600 new voxels a window: "
      f"{int(np.ceil((2.12*10000/UM - 797)/600)) + 1}")
