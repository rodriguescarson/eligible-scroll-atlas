# overlap_consistency.py <runA_dir> <runB_dir> <z_lo> <z_hi> <out_json>
# Label-free winding-consistency test between two spiral fits whose z windows overlap. In [z_lo, z_hi) each winding of run B is
# matched to the nearest surfaces of run A. A consistent pair of fits gives every B winding one A winding (share near 1) and the
# same index offset everywhere; a sheet switch in either fit shows as a split share or a changing offset.
import glob, json, os, sys, numpy as np, tifffile
from scipy.spatial import cKDTree
runA, runB = (a.rstrip("/") + "/" for a in sys.argv[1:3]); z_lo, z_hi = float(sys.argv[3]), float(sys.argv[4]); out = sys.argv[5]
def load(run):
    pts, lab = [], []
    for d in sorted(glob.glob(run + "meshes/all/w*/")):
        P = np.stack([tifffile.imread(f"{d}/{c}.tif").astype(np.float32) for c in "xyz"], -1); ok = (P > 0).all(-1)
        q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
        c00, c01, c10, c11 = P[:-1, :-1][q], P[:-1, 1:][q], P[1:, :-1][q], P[1:, 1:][q]
        t = (np.arange(4, dtype=np.float32) + 0.5) / 4; a, b = np.meshgrid(t, t, indexing="ij"); a = a.reshape(1, -1, 1); b = b.reshape(1, -1, 1)
        p = ((1 - a) * (1 - b) * c00[:, None] + (1 - a) * b * c01[:, None] + a * (1 - b) * c10[:, None] + a * b * c11[:, None]).reshape(-1, 3)
        p = p[(p[:, 2] >= z_lo) & (p[:, 2] < z_hi)]
        if len(p): pts.append(p); lab.append(np.full(len(p), int(os.path.basename(d.rstrip("/"))[1:]), np.int32))
    return np.concatenate(pts), np.concatenate(lab)
pA, lA = load(runA); pB, lB = load(runB); tree = cKDTree(pA)
rows = []
for w in np.unique(lB):
    q = pB[lB == w]
    if len(q) < 500: continue
    if len(q) > 60000: q = q[np.random.default_rng(int(w)).choice(len(q), 60000, replace=False)]
    d, i = tree.query(q); m = lA[i]; vals, cnt = np.unique(m, return_counts=True); best = int(vals[cnt.argmax()])
    rows.append(dict(b=f"w{int(w):03d}", a=f"w{best:03d}", offset=best - int(w), share=round(float(cnt.max() / len(m)), 3),
                     dist_median=round(float(np.median(d)), 2), within5=round(float((d <= 5).mean()), 3), n=int(len(q))))
spacing = {}
rng = np.random.default_rng(0)
for w in [int(x) for x in np.unique(lA)][5::10]:
    s = pA[lA == w]; nb = pA[lA == w + 1]
    if len(s) < 500 or len(nb) < 500: continue
    s = s[rng.choice(len(s), min(20000, len(s)), replace=False)]; spacing[f"w{w:03d}->w{w + 1:03d}"] = round(float(np.median(cKDTree(nb).query(s)[0])), 1)
offs, shares = np.array([r["offset"] for r in rows]), np.array([r["share"] for r in rows])
vals, cnt = np.unique(offs, return_counts=True) if len(offs) else ([], [])
summary = dict(z_overlap=[z_lo, z_hi], b_windings_matched=len(rows), offset_histogram={int(v): int(c) for v, c in zip(vals, cnt)},
               share_median=round(float(np.median(shares)), 3) if len(shares) else None, share_ge_0_8=int((shares >= 0.8).sum()),
               share_lt_0_6=[r["b"] for r in rows if r["share"] < 0.6], dist_median_all=round(float(np.median([r["dist_median"] for r in rows])), 2) if rows else None,
               runA_adjacent_spacing_vx=spacing)
res = dict(runA=os.path.basename(runA.rstrip("/")), runB=os.path.basename(runB.rstrip("/")), summary=summary, windings=rows)
json.dump(res, open(out, "w"), indent=1); print(json.dumps(summary, indent=1))
