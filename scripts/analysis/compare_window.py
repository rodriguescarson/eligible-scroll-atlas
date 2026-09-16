# compare_window.py <run_dir> <ref_mesh_dir>... : same-window yield comparison, our spiral fit vs pscamillo's exported meshes.
# For each reference mesh: densify its tifxyz grid x4, find the nearest point on any of our exported windings (also densified),
# report the winding it lands on (majority), the share of its points within 5/10/20 voxels of that winding, and both areas.
# Then the total area of all our windings in the window. Same volume frame (both tifxyz in PHerc0826 20250821151701 voxels).
import glob, json, os, sys, numpy as np, tifffile
from scipy.spatial import cKDTree
VOX = 9.362
def load(d, up=4):
    P = np.stack([tifffile.imread(f"{d}/{c}.tif").astype(np.float32) for c in "xyz"], -1); ok = (P > 0).all(-1)
    du = P[:-1, 1:] - P[:-1, :-1]; dv = P[1:, :-1] - P[:-1, :-1]
    q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    area = float(np.linalg.norm(np.cross(du, dv), axis=-1)[q].sum()) * (VOX * 1e-4) ** 2
    c00, c01, c10, c11 = P[:-1, :-1][q], P[:-1, 1:][q], P[1:, :-1][q], P[1:, 1:][q]
    t = (np.arange(up, dtype=np.float32) + 0.5) / up; a, b = np.meshgrid(t, t, indexing="ij"); a = a.reshape(1, -1, 1); b = b.reshape(1, -1, 1)
    pts = (1 - a) * (1 - b) * c00[:, None] + (1 - a) * b * c01[:, None] + a * (1 - b) * c10[:, None] + a * b * c11[:, None]
    return pts.reshape(-1, 3), area
run = sys.argv[1].rstrip("/") + "/"; refs = sys.argv[2:]
ours = sorted(glob.glob(run + "meshes/all/w*/")); allp = []; lab = []; areas = {}
for d in ours:
    n = os.path.basename(d.rstrip("/")); p, a = load(d.rstrip("/")); areas[n] = a; allp.append(p); lab.append(np.full(len(p), int(n[1:])))
allp = np.concatenate(allp); lab = np.concatenate(lab); tree = cKDTree(allp)
res = {"run": os.path.basename(run.rstrip("/")), "our_windings": len(ours), "our_total_cm2": round(sum(areas.values()), 2), "refs": {}}
for r in refs:
    p, a = load(r.rstrip("/")); zr = (float(p[:, 2].min()), float(p[:, 2].max())) if len(p) else None
    if len(p) > 200000: p = p[np.random.default_rng(0).choice(len(p), 200000, replace=False)]
    dist, idx = tree.query(p); w = lab[idx]; vals, cnt = np.unique(w, return_counts=True); best = int(vals[cnt.argmax()])
    on = w == best
    res["refs"][os.path.basename(r.rstrip("/"))] = dict(ref_cm2=round(a, 2), ref_z=zr, matched_winding=f"w{best:03d}", share_on_matched=round(float(on.mean()), 3),
        within5=round(float((dist[on] <= 5).mean()), 3), within10=round(float((dist[on] <= 10).mean()), 3), within20=round(float((dist <= 20).mean()), 3),
        median_dist_vx=round(float(np.median(dist)), 2), our_matched_cm2=round(areas[f"w{best:03d}"], 2),
        other_windings_hit={f"w{int(v):03d}": int(c) for v, c in zip(vals, cnt) if int(v) != best and c > 0.02 * len(p)})
print(json.dumps(res, indent=1)); json.dump(res, open(run + "compare_pscamillo.json", "w"), indent=1)
