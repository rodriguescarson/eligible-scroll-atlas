"""compare_pscamillo.py: mesh-by-mesh reproducibility check of our seed43/060000 forward maps against pscamillo's
(pscamillo/vesuvius-eligible-meshes-ink9: seed43/060000, layer-start 7, layer-end 24, same render recipe, older binary).
Per mesh: Pearson r over the valid mask, S1 (frac >= 0.75) for both, and the S1 ratio. Writes a CSV and a summary JSON.
usage: compare_pscamillo.py --ours /workspace/atlas/renders --theirs /workspace/atlas/pscamillo_maps --out compare.csv"""
import argparse, csv, glob, json, os, numpy as np, tifffile

def load(p):
    m = tifffile.imread(p).astype(np.float32)
    return m / 255.0 if m.max() > 1.5 else m

ap = argparse.ArgumentParser(); ap.add_argument("--ours", required=True); ap.add_argument("--theirs", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--tag", default="s43_060k")
a = ap.parse_args()
rows = []
for side in sorted(glob.glob(os.path.join(a.ours, "*", "*", "ink-detection", "infer.json"))):
    d = os.path.dirname(side); mesh = os.path.basename(os.path.dirname(d)); scroll = os.path.basename(os.path.dirname(os.path.dirname(d)))
    ours = glob.glob(os.path.join(d, f"*-{a.tag}.tif")); theirs = os.path.join(a.theirs, scroll, f"{mesh}.tif")
    if not ours or not os.path.exists(theirs): continue
    o = load(ours[0]); t = load(theirs); mk = tifffile.imread(os.path.join(d, "valid_mask.tif")) != 0
    H, W = min(o.shape[0], t.shape[0], mk.shape[0]), min(o.shape[1], t.shape[1], mk.shape[1])
    o, t, mk = o[:H, :W], t[:H, :W], mk[:H, :W]
    if mk.sum() < 1000: continue
    ov, tv = o[mk], t[mk]
    r = float(np.corrcoef(ov, tv)[0, 1]) if ov.std() > 0 and tv.std() > 0 else float("nan")
    s1o, s1t = float((ov >= 0.75).mean()), float((tv >= 0.75).mean())
    rows.append({"scroll": scroll, "mesh": mesh, "valid_px": int(mk.sum()), "shape_ours": f"{o.shape[0]}x{o.shape[1]}",
                 "pearson_r": r, "S1_ours": s1o, "S1_theirs": s1t, "mean_ours": float(ov.mean()), "mean_theirs": float(tv.mean()),
                 "mad": float(np.abs(ov - tv).mean())})
    print(scroll, mesh, f"r={r:.3f} S1 {s1o:.4f} vs {s1t:.4f} mad {rows[-1]['mad']:.3f}", flush=True)
with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
rs = np.array([x["pearson_r"] for x in rows]); rs = rs[~np.isnan(rs)]
summ = {"n": len(rows), "pearson_r_median": float(np.median(rs)) if len(rs) else None, "pearson_r_p10": float(np.percentile(rs, 10)) if len(rs) else None,
        "S1_ours_median": float(np.median([x["S1_ours"] for x in rows])), "S1_theirs_median": float(np.median([x["S1_theirs"] for x in rows])),
        "note": "theirs: seed43/060000 layers 7-24, older VC3D binary; ours: seed43/060000 default layer window, VC3D 4b3c728, masked, padded to 64"}
json.dump(summ, open(a.out.replace(".csv", ".json"), "w"), indent=1); print(json.dumps(summ, indent=1))
