# profile.py <out_dir> <name=zarr_path>...: per-render layer profile, 64 px tile peak-layer distribution, mid-layer PNG
import json, os, sys, numpy as np, zarr
from PIL import Image
od = sys.argv[1]; os.makedirs(od, exist_ok=True); out = {}
# record what was measured: attribution should not rest on file mtime
out["_source"] = {"out_dir": od, "inputs": [a.split("=", 1)[-1] for a in sys.argv[2:]]}
for arg in sys.argv[2:]:
    n, z = arg.split("=", 1); g = zarr.open(z, mode="r"); a = g["0"] if "0" in g else g
    v = np.asarray(a[:]).astype(np.float32); valid = v.max(axis=0) > 0
    if valid.sum() < 1000: out[n] = "tiny"; continue
    T = 64; H, W = valid.shape[0] // T, valid.shape[1] // T; peaks = []; contr = []
    for i in range(H):
        for j in range(W):
            if valid[i*T:(i+1)*T, j*T:(j+1)*T].mean() < 0.8: continue
            p = v[:, i*T:(i+1)*T, j*T:(j+1)*T].reshape(v.shape[0], -1).mean(1)
            peaks.append(int(p.argmax())); contr.append(float((p.max() - p.min()) / (p.mean() + 1e-6)))
    peaks = np.array(peaks); c = v.shape[0] // 2
    out[n] = dict(shape=list(v.shape), tiles=len(peaks), peak_within3=float((abs(peaks - c) <= 3).mean()),
                  peak_edge=float(((peaks <= 1) | (peaks >= v.shape[0] - 2)).mean()), contrast_median=float(np.median(contr)),
                  peak_hist=np.bincount(peaks, minlength=v.shape[0]).tolist())
    im = Image.fromarray(np.where(valid, v[c], 0).astype(np.uint8)); s = min(1.0, 1600 / im.width)
    im.resize((max(1, int(im.width * s)), max(1, int(im.height * s)))).save(f"{od}/{n}_mid.png")
    print(n, json.dumps({k: out[n][k] for k in ("shape", "tiles", "peak_within3", "peak_edge", "contrast_median")}))
json.dump(out, open(f"{od}/profiles.json", "w"), indent=1)
