# control_in_population.py: put the known-ink controls into the Hecate population distribution using the IDENTICAL statistic
# (masked fraction over the render's valid area eroded by 64 px). Only w042 and w043 have their 9.6 um render archived in the
# repo, so only they can be made comparable; the far-winding controls have no archived render.
import json, os, subprocess, sys
import numpy as np, zarr
from PIL import Image
from scipy import ndimage
from huggingface_hub import hf_hub_download
R = "rodriguescarson/eligible-scroll-atlas-held"
TOK = open("/workspace/atlas/.hf_token").read().strip()
Image.MAX_IMAGE_PIXELS = None
pop = {}
for line in open("/tmp/hecate_all.jsonl"):
    line = line.strip()
    if not line: continue
    try: r = json.loads(line)
    except Exception: continue
    f, v = r.get("fwd"), r.get("rev")
    if isinstance(f, dict) and isinstance(v, dict) and "ge_0.75" in f:
        pop[r["mesh"]] = (f["ge_0.75"], v["ge_0.75"])
f075 = sorted(x[0] for x in pop.values())
ratio = sorted((x[0] + 1e-4) / (x[1] + 1e-4) for x in pop.values())
pct = lambda val, arr: 100.0 * sum(1 for x in arr if x <= val) / len(arr)
print("population meshes:", len(pop))
for name in ("w042", "w043"):
    d = f"/workspace/ctl/{name}"; os.makedirs(d, exist_ok=True)
    try:
        tar = hf_hub_download(R, f"c96b/{name}/r96_31.zarr.tar", repo_type="dataset", token=TOK, local_dir=d)
        fwd = hf_hub_download(R, f"c96b/{name}/hecate_fwd.png", repo_type="dataset", token=TOK, local_dir=d)
        rev = hf_hub_download(R, f"c96b/{name}/hecate_rev.png", repo_type="dataset", token=TOK, local_dir=d)
    except Exception as e:
        print(name, "download failed:", str(e)[:80]); continue
    subprocess.run(["tar", "-xf", tar, "-C", d], check=True)
    zp = [os.path.join(dp, x) for dp, dn, fn in os.walk(d) for x in dn if x.endswith(".zarr")]
    if not zp: print(name, "no zarr in archive"); continue
    a = zarr.open(zp[0], mode="r")["0"]
    valid = np.zeros(a.shape[1:], bool)
    for y in range(0, a.shape[1], 1024): valid[y:y + 1024] = a[:, y:y + 1024, :].max(axis=0) > 0
    er = ndimage.binary_erosion(valid, iterations=64, border_value=0)
    out = {}
    for tag, p in (("fwd", fwd), ("rev", rev)):
        img = np.asarray(Image.open(p)).astype(np.float32) / 255.0
        h, w = min(img.shape[0], er.shape[0]), min(img.shape[1], er.shape[1])
        v = img[:h, :w][er[:h, :w]]
        out[tag] = (float((v >= 0.5).mean()), float((v >= 0.75).mean()))
    r = (out["fwd"][1] + 1e-4) / (out["rev"][1] + 1e-4)
    print("%s: valid %d px | fwd >=0.5 %.4f >=0.75 %.4f | rev >=0.5 %.4f >=0.75 %.4f | ratio %.1f"
          % (name, int(er.sum()), out["fwd"][0], out["fwd"][1], out["rev"][0], out["rev"][1], r))
    print("   position in the %d-mesh population: fwd>=0.75 at %.1f pct, ratio at %.1f pct, above population max (%.4f): %s"
          % (len(pop), pct(out["fwd"][1], f075), pct(r, ratio), f075[-1], out["fwd"][1] > f075[-1]))
    subprocess.run(["rm", "-rf", d])
