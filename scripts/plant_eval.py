"""plant_eval.py <planted dir>: does the pre-registered screen flag the planted window?
Reads plant.json (window coordinates), the three forward maps in <dir>/ink-detection, the valid mask; reports S1 inside
and outside the window, the share of the p_min>=0.75 mass inside the window, and the screens on the spliced volume."""
import glob, json, os, sys, numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screens import pmin, screens
d = sys.argv[1]; rec = json.load(open(os.path.join(d, "plant.json"))); um = rec["um"]
ink = os.path.join(d, "ink-detection")
fw = sorted(f for f in glob.glob(os.path.join(ink, "*.tif")) if not f.endswith("_reverse.tif") and not f.endswith("valid_mask.tif"))
pm, _ = pmin(fw); mk = tifffile.imread(os.path.join(ink, "valid_mask.tif")) != 0
H, W = min(pm.shape[0], mk.shape[0]), min(pm.shape[1], mk.shape[1]); pm, mk = pm[:H, :W], mk[:H, :W]
hit = mk & (pm >= 0.75); box = np.zeros_like(mk); ty, tx = rec["target_box_yx"]; h, w = rec["window_px"]; box[ty:ty + h, tx:tx + w] = True
s1_in = float((hit & box).sum() / max((mk & box).sum(), 1)); s1_out = float((hit & ~box).sum() / max((mk & ~box).sum(), 1))
share = float((hit & box).sum() / max(hit.sum(), 1)); area_share = float((mk & box).sum() / max(mk.sum(), 1))
sc = screens(ink, um, None, os.path.join(ink, "valid_mask.tif"))
out = {"S1_in_window": s1_in, "S1_outside": s1_out, "ratio_in_over_out": s1_in / s1_out if s1_out > 0 else None,
       "hit_mass_share_in_window": share, "window_area_share": area_share, "flagged": bool(share > 0.5 and s1_in > 5 * max(s1_out, 1e-9)),
       "screens_on_spliced": sc}
json.dump(out, open(os.path.join(d, "plant_eval.json"), "w"), indent=1); print(json.dumps(out, indent=1))
