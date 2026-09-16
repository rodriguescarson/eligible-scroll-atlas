# label_map.py <run_dir> <ref_meshes_dir> <out_dir>: for each pscamillo mesh grid point, which of our windings is nearest and how far;
# spatial coherence of those labels (share of 4-neighbour grid pairs with the same label), label-map PNGs, and our own spacing
# between adjacent windings at the matched windings (to show whether a 4-5 voxel match can be ambiguous between windings).
import glob, json, os, sys, numpy as np, tifffile
from scipy.spatial import cKDTree
from PIL import Image
run, refdir, out = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3]; os.makedirs(out, exist_ok=True)
def grid(d):
    P = np.stack([tifffile.imread(f"{d}/{c}.tif").astype(np.float32) for c in "xyz"], -1); return P, (P > 0).all(-1)
def dens(P, ok, up=4):
    q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    c00, c01, c10, c11 = P[:-1, :-1][q], P[:-1, 1:][q], P[1:, :-1][q], P[1:, 1:][q]
    t = (np.arange(up, dtype=np.float32) + 0.5) / up; a, b = np.meshgrid(t, t, indexing="ij"); a = a.reshape(1, -1, 1); b = b.reshape(1, -1, 1)
    return ((1 - a) * (1 - b) * c00[:, None] + (1 - a) * b * c01[:, None] + a * (1 - b) * c10[:, None] + a * b * c11[:, None]).reshape(-1, 3)
pts, lab = [], []
for d in sorted(glob.glob(run + "meshes/all/w*/")):
    P, ok = grid(d.rstrip("/")); p = dens(P, ok); pts.append(p); lab.append(np.full(len(p), int(os.path.basename(d.rstrip("/"))[1:]), np.int32))
allp = np.concatenate(pts); lab = np.concatenate(lab); tree = cKDTree(allp)
PAL = np.array([[230,25,75],[60,180,75],[255,225,25],[0,130,200],[245,130,48],[145,30,180],[70,240,240],[240,50,230],[210,245,60],[250,190,212],[0,128,128],[170,110,40],[128,0,0],[170,255,195],[128,128,0],[0,0,128]], np.uint8)
res = {"spacing": {}, "refs": {}}
for name in ("z6528_w020", "z6528_w040", "z6528_w060"):
    P, ok = grid(f"{refdir}/{name}"); dist, idx = tree.query(P[ok]); w = lab[idx]
    L = np.full(ok.shape, -1, np.int32); L[ok] = w; D = np.full(ok.shape, np.nan, np.float32); D[ok] = dist
    same = []
    for A, B in ((L[:-1, :], L[1:, :]), (L[:, :-1], L[:, 1:])):
        v = (A >= 0) & (B >= 0); same.append((A[v] == B[v]))
    same = np.concatenate(same)
    vals, cnt = np.unique(w, return_counts=True); order = np.argsort(-cnt)
    img = np.zeros(ok.shape + (3,), np.uint8); rank = {int(vals[i]): r for r, i in enumerate(order)}
    for v in vals: img[L == v] = PAL[rank[int(v)] % len(PAL)]
    img[ok & (D > 20)] = 40
    Image.fromarray(img).resize((ok.shape[1] * 3, ok.shape[0] * 3), Image.NEAREST).save(f"{out}/{name}_labels.png")
    res["refs"][name] = dict(grid=list(ok.shape), neighbour_same_label=round(float(same.mean()), 3),
        labels_by_count=[(f"w{int(vals[i]):03d}", int(cnt[i]), [int(c) for c in PAL[r % len(PAL)]]) for r, i in enumerate(order)],
        dist_median=round(float(np.nanmedian(D)), 2), dist_p90=round(float(np.nanpercentile(D, 90)), 2))
rng = np.random.default_rng(0)
for w0 in (27, 51, 73):
    pw = allp[lab == w0]; s = pw[rng.choice(len(pw), min(20000, len(pw)), replace=False)]
    for nb in (w0 - 1, w0 + 1):
        d, _ = cKDTree(allp[lab == nb]).query(s); res["spacing"][f"w{w0:03d}->w{nb:03d}"] = dict(median=round(float(np.median(d)), 1), p10=round(float(np.percentile(d, 10)), 1))
print(json.dumps(res, indent=1)); json.dump(res, open(f"{out}/label_map.json", "w"), indent=1)
