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
    of = glob.glob(os.path.join(d, f"*-{a.tag}.tif")); orv = glob.glob(os.path.join(d, f"*-{a.tag}_reverse.tif"))
    tf = os.path.join(a.theirs, scroll, f"{mesh}.tif"); trv = os.path.join(a.theirs, scroll, f"{mesh}_reverse.tif")
    if not (of and orv and os.path.exists(tf) and os.path.exists(trv)): continue
    mk = tifffile.imread(os.path.join(d, "valid_mask.tif")) != 0
    O, OR, T, TR = load(of[0]), load(orv[0]), load(tf), load(trv)
    H = min(O.shape[0], T.shape[0], mk.shape[0]); W = min(O.shape[1], T.shape[1], mk.shape[1]); m = mk[:H, :W]
    if m.sum() < 1000: continue
    v = lambda x: x[:H, :W][m]
    def corr(x, y):
        x, y = v(x), v(y); return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else float("nan")
    row = {"scroll": scroll, "mesh": mesh, "valid_px": int(m.sum()), "shape_ours": f"{O.shape[0]}x{O.shape[1]}", "shape_theirs": f"{T.shape[0]}x{T.shape[1]}",
           "r_ourfwd_theirfwd": corr(O, T), "r_ourfwd_theirrev": corr(O, TR), "r_ourrev_theirfwd": corr(OR, T),
           "mad_ourfwd_theirrev": float(np.abs(v(O) - v(TR)).mean()), "max_ad_ourfwd_theirrev": float(np.abs(v(O) - v(TR)).max()),
           "S1_ourfwd": float((v(O) >= 0.75).mean()), "S1_theirrev": float((v(TR) >= 0.75).mean()),
           "S1_ourrev": float((v(OR) >= 0.75).mean()), "S1_theirfwd": float((v(T) >= 0.75).mean())}
    rows.append(row)
    print(scroll, mesh, "fwd/fwd %.3f fwd/theirrev %.3f rev/theirfwd %.3f mad %.4f" % (row["r_ourfwd_theirfwd"], row["r_ourfwd_theirrev"], row["r_ourrev_theirfwd"], row["mad_ourfwd_theirrev"]), flush=True)
with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def q(k):
    a = np.array([x[k] for x in rows], float); a = a[~np.isnan(a)]
    return {"min": float(a.min()), "p10": float(np.percentile(a, 10)), "median": float(np.median(a)), "max": float(a.max())} if len(a) else None
summ = {"n": len(rows), "r_ourfwd_theirfwd": q("r_ourfwd_theirfwd"), "r_ourfwd_theirrev": q("r_ourfwd_theirrev"), "r_ourrev_theirfwd": q("r_ourrev_theirfwd"),
        "mad_ourfwd_theirrev": q("mad_ourfwd_theirrev"), "max_ad_ourfwd_theirrev": q("max_ad_ourfwd_theirrev"),
        "shape_mismatch": sum(1 for x in rows if x["shape_ours"] != x["shape_theirs"]),
        "note": "ours: --flip-normals renders (team layer order, repro/), padded to 64; theirs: pscamillo/vesuvius-eligible-meshes-ink9, seed43/060000 layers 7-24; compared over our eroded valid mask on the common top-left crop"}
json.dump(summ, open(a.out.replace(".csv", ".json"), "w"), indent=1); print(json.dumps(summ, indent=1))
