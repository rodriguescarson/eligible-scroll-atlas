"""window_layer_drift.py <meshes-dir>
Across-sheet drift at every adjacent-window join in the whole mesh set. For each pair of
z-adjacent windows sharing a wrap label, measures how far apart the two surfaces are in the
shared z band, split into the component across the sheet and the component along it. Sheets are
about 13 voxels apart, so an across-sheet median above that means the two windows are tracking
different layers and must not be joined. Expects the pscamillo eligible-meshes layout,
<meshes-dir>/<scroll>/z<window>_w<wrap>/{x,y,z}.tif + meta.json."""
import os, sys, json
import numpy as np, tifffile
from scipy.spatial import cKDTree

root = sys.argv[1]
def load(sc, mesh):
    d = os.path.join(root, sc, mesh)
    xyz = np.stack([tifffile.imread(os.path.join(d, f"{c}.tif")) for c in "xyz"], -1).astype(np.float64)
    return xyz, json.load(open(os.path.join(d, "meta.json")))["bbox"]

def normals(xyz):
    n = np.cross(np.gradient(xyz, axis=1), np.gradient(xyz, axis=0))
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    return np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)

rows = []
for sc in sorted(os.listdir(root)):
    all_m = os.listdir(os.path.join(root, sc))
    wins = sorted({int(m.split("_")[0][1:]) for m in all_m})
    for wrap in sorted({m.split("_")[1] for m in all_m}):
        for za, zb in zip(wins, wins[1:]):
            ma, mb = f"z{za}_{wrap}", f"z{zb}_{wrap}"
            if ma not in all_m or mb not in all_m: continue
            A, bbA = load(sc, ma); B, bbB = load(sc, mb)
            zlo, zhi = bbB[0][2], bbA[1][2]
            if zhi <= zlo: continue
            nB = normals(B)
            vb = (B[..., 0] != 0) & (B[..., 2] >= zlo) & (B[..., 2] <= zhi)
            va = (A[..., 0] != 0) & (A[..., 2] >= zlo) & (A[..., 2] <= zhi)
            pb, nb, pa = B[vb], nB[vb], A[va]
            if len(pa) < 50 or len(pb) < 50: continue
            d, i = cKDTree(pb).query(pa, k=1)
            disp = pa - pb[i]
            across = np.abs(np.einsum("ij,ij->i", disp, nb[i]))
            inpl = np.sqrt(np.maximum(d**2 - across**2, 0))
            rows.append(dict(scroll=sc, wrap=wrap, za=za, zb=zb,
                             across=float(np.median(across)), inpl=float(np.median(inpl))))

a = np.array([r["across"] for r in rows]); p = np.array([r["inpl"] for r in rows])
print(f"{len(rows)} adjacent-window joins across {len({r['scroll'] for r in rows})} scrolls\n")
print(f"across-sheet residual: median {np.median(a):.1f} voxels, "
      f"p10 {np.percentile(a,10):.1f}, p90 {np.percentile(a,90):.1f}, max {a.max():.1f}")
print(f"in-plane residual:     median {np.median(p):.1f} voxels, p90 {np.percentile(p,90):.1f}")
print(f"\nacross-sheet dominates in-plane on {int((a>p).sum())}/{len(rows)} joins")
print(f"joins where across-sheet < 6 voxels (same layer):  {int((a<6).sum())}/{len(rows)}")
print(f"joins where across-sheet < 13 voxels (one layer):  {int((a<13).sum())}/{len(rows)}")
print("\nper scroll (median across-sheet, voxels):")
for sc in sorted({r["scroll"] for r in rows}):
    v = [r["across"] for r in rows if r["scroll"] == sc]
    print(f"  {sc:<10} n={len(v):>3}  {np.median(v):>6.1f}   range {min(v):>5.1f}-{max(v):>5.1f}")
