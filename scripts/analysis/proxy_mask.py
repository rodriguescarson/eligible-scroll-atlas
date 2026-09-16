# proxy_mask.py: three known-ink controls have Hecate maps but no archived render, so the population statistic (mask from the
# render's valid area, eroded 64 px) cannot be computed for them. Test whether a mask taken from the map itself reproduces that
# statistic on the two controls where the render IS archived; apply it to the other three only if the error is small.
import json, os, subprocess
import numpy as np, zarr
from PIL import Image
from scipy import ndimage
from huggingface_hub import hf_hub_download
R = "rodriguescarson/eligible-scroll-atlas-held"; TOK = open("/workspace/atlas/.hf_token").read().strip()
Image.MAX_IMAGE_PIXELS = None
pop = {}
for line in open("/tmp/hecate_all.jsonl"):
    line = line.strip()
    if not line: continue
    try: r = json.loads(line)
    except Exception: continue
    f, v = r.get("fwd"), r.get("rev")
    if isinstance(f, dict) and isinstance(v, dict) and "ge_0.75" in f: pop[r["mesh"]] = (f["ge_0.75"], v["ge_0.75"])
f075 = sorted(x[0] for x in pop.values()); ratios = sorted((x[0] + 1e-4) / (x[1] + 1e-4) for x in pop.values())
pct = lambda v, arr: 100.0 * sum(1 for x in arr if x <= v) / len(arr)
def stats(mask, fwd_p, rev_p):
    out = {}
    for tag, p in (("fwd", fwd_p), ("rev", rev_p)):
        im = np.asarray(Image.open(p)).astype(np.float32) / 255.0
        h, w = min(im.shape[0], mask.shape[0]), min(im.shape[1], mask.shape[1])
        v = im[:h, :w][mask[:h, :w]]
        out[tag] = (float((v >= 0.5).mean()), float((v >= 0.75).mean()))
    return out
print("== proxy validation on the two controls with an archived render")
for name in ("w042", "w043"):
    d = f"/workspace/proxy/{name}"; os.makedirs(d, exist_ok=True)
    tar = hf_hub_download(R, f"c96b/{name}/r96_31.zarr.tar", repo_type="dataset", token=TOK, local_dir=d)
    fwd = hf_hub_download(R, f"c96b/{name}/hecate_fwd.png", repo_type="dataset", token=TOK, local_dir=d)
    rev = hf_hub_download(R, f"c96b/{name}/hecate_rev.png", repo_type="dataset", token=TOK, local_dir=d)
    subprocess.run(["tar", "-xf", tar, "-C", d], check=True)
    zp = [os.path.join(dp, x) for dp, dn, fn in os.walk(d) for x in dn if x.endswith(".zarr")][0]
    a = zarr.open(zp, mode="r")["0"]
    valid = np.zeros(a.shape[1:], bool)
    for y in range(0, a.shape[1], 1024): valid[y:y + 1024] = a[:, y:y + 1024, :].max(axis=0) > 0
    true_mask = ndimage.binary_erosion(valid, iterations=64, border_value=0)
    im = np.asarray(Image.open(fwd))
    proxy_mask = ndimage.binary_erosion(im > 0, iterations=64, border_value=0)
    t, p = stats(true_mask, fwd, rev), stats(proxy_mask, fwd, rev)
    print("%s: true fwd>=0.75 %.4f vs proxy %.4f (%+.1f%%) | true rev %.4f vs proxy %.4f | mask px %d vs %d"
          % (name, t["fwd"][1], p["fwd"][1], 100 * (p["fwd"][1] - t["fwd"][1]) / max(t["fwd"][1], 1e-9), t["rev"][1], p["rev"][1], int(true_mask.sum()), int(proxy_mask.sum())))
    subprocess.run(["rm", "-rf", d])
print("\n== proxy applied to the controls with no archived render")
for g, label in (("c96c/hecate_0139_w058", "PHerc0139 w058"), ("c96c/hecate_0139_w051", "PHerc0139 w051"), ("c96c/hecate_0172_w081", "PHerc0172 w081")):
    d = f"/workspace/proxy/{g.split('/')[-1]}"; os.makedirs(d, exist_ok=True)
    try:
        fwd = hf_hub_download(R, f"{g}/hecate_fwd.png", repo_type="dataset", token=TOK, local_dir=d)
        rev = hf_hub_download(R, f"{g}/hecate_rev.png", repo_type="dataset", token=TOK, local_dir=d)
    except Exception as e:
        print(label, "unavailable", str(e)[:60]); continue
    im = np.asarray(Image.open(fwd))
    m = ndimage.binary_erosion(im > 0, iterations=64, border_value=0)
    s = stats(m, fwd, rev); r = (s["fwd"][1] + 1e-4) / (s["rev"][1] + 1e-4)
    print("%-16s fwd >=0.5 %.4f >=0.75 %.4f | rev >=0.75 %.4f | ratio %4.1f | %.1f pct of %d, ratio %.1f pct"
          % (label, s["fwd"][0], s["fwd"][1], s["rev"][1], r, pct(s["fwd"][1], f075), len(f075), pct(r, ratios)))
    subprocess.run(["rm", "-rf", d])
