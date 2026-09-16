# spacing_profile.py <run_dir> <z_lo> <z_hi> <out_json>: median separation between every pair of consecutive exported windings
# in a z band. A papyrus sheet at 9.362 um/voxel is at least ~10 voxels thick, so consecutive windings closer than that cannot be
# distinct sheets.
import glob, json, os, sys, numpy as np, tifffile
from scipy.spatial import cKDTree
run = sys.argv[1].rstrip("/") + "/"; z_lo, z_hi = float(sys.argv[2]), float(sys.argv[3]); out = sys.argv[4]
def load(d, up=4):
    P = np.stack([tifffile.imread(f"{d}/{c}.tif").astype(np.float32) for c in "xyz"], -1); ok = (P > 0).all(-1)
    q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    c00, c01, c10, c11 = P[:-1, :-1][q], P[:-1, 1:][q], P[1:, :-1][q], P[1:, 1:][q]
    t = (np.arange(up, dtype=np.float32) + 0.5) / up; a, b = np.meshgrid(t, t, indexing="ij"); a = a.reshape(1, -1, 1); b = b.reshape(1, -1, 1)
    p = ((1 - a) * (1 - b) * c00[:, None] + (1 - a) * b * c01[:, None] + a * (1 - b) * c10[:, None] + a * b * c11[:, None]).reshape(-1, 3)
    return p[(p[:, 2] >= z_lo) & (p[:, 2] < z_hi)]
ws = sorted(glob.glob(run + "meshes/all/w*/")); pts = {int(os.path.basename(d.rstrip("/"))[1:]): load(d.rstrip("/")) for d in ws}
rng = np.random.default_rng(0); rows = []
for w in sorted(pts):
    a, b = pts.get(w), pts.get(w + 1)
    if a is None or b is None or len(a) < 200 or len(b) < 200: continue
    s = a[rng.choice(len(a), min(20000, len(a)), replace=False)]
    d, _ = cKDTree(b).query(s)
    rows.append(dict(w=f"w{w:03d}->w{w + 1:03d}", median=round(float(np.median(d)), 2), p10=round(float(np.percentile(d, 10)), 2), p90=round(float(np.percentile(d, 90)), 2)))
med = np.array([r["median"] for r in rows])
summary = dict(pairs=len(rows), median_spacing_vx=round(float(np.median(med)), 2), under_5vx=int((med < 5).sum()), under_10vx=int((med < 10).sum()),
               min=round(float(med.min()), 2), max=round(float(med.max()), 2))
print(json.dumps(summary)); print("first 10:", [(r["w"], r["median"]) for r in rows[:10]]); print("last 10:", [(r["w"], r["median"]) for r in rows[-10:]])
json.dump(dict(run=os.path.basename(run.rstrip("/")), z=[z_lo, z_hi], summary=summary, pairs=rows), open(out, "w"), indent=1)
