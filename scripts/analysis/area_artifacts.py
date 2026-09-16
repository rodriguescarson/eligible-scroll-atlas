# area_artifacts.py: commit an area artifact for every fit run. Only the 6528-7328 window had one; the other three areas were
# quoted from pod logs, which the findings document promises not to do. Meshes come back from the private dataset.
import glob, json, os
import numpy as np, tifffile
from huggingface_hub import snapshot_download
TOK = open("/workspace/atlas/.hf_token").read().strip()
RUNS = ["spiralfit/PHerc0826/2026-09-15_PHerc0826_slice-8928-9728_0-patch",
        "spiralfit/PHerc0826/2026-09-15_PHerc0826_slice-9328-10128_0-patch",
        "spiralfit/PHerc0191/2026-09-15_PHerc0191_slice-11600-12400_0-patch_w90",
        "spiralfit/PHerc0191/2026-09-15_PHerc0191_slice-11600-12400_0-patch_w45"]
VOX = 9.362
for R in RUNS:
    snapshot_download("rodriguescarson/eligible-scroll-atlas-held", repo_type="dataset", token=TOK,
                      local_dir="/workspace/areas", allow_patterns=[R + "/meshes/all/*"])
    run = f"/workspace/areas/{R}/"
    rows, tot = [], 0.0
    for d in sorted(glob.glob(run + "meshes/all/w*/")):
        x, y, z = (tifffile.imread(f"{d}{c}.tif").astype(np.float64) for c in "xyz")
        ok = (x > 0) & (y > 0) & (z > 0); P = np.stack([x, y, z], -1)
        du = P[:-1, 1:] - P[:-1, :-1]; dv = P[1:, :-1] - P[:-1, :-1]
        q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
        cm2 = float(np.linalg.norm(np.cross(du, dv), axis=-1)[q].sum()) * (VOX * 1e-4) ** 2
        rows.append(dict(w=os.path.basename(d.rstrip("/")), cm2=round(cm2, 3), valid_frac=round(float(ok.mean()), 3)))
        tot += cm2
    out = dict(run=os.path.basename(R), source="meshes/all recomputed from the private dataset", voxel_um=VOX,
               windings=len(rows), total_cm2=round(tot, 2), per_winding=rows)
    name = f"/tmp/area_{os.path.basename(R)}.json"
    json.dump(out, open(name, "w"), indent=1)
    print("%-62s windings %2d  total %8.2f cm2" % (os.path.basename(R), len(rows), tot))
