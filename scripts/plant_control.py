"""plant_control.py: the planted-ink control (PREREG "Controls" 2).
Splices a 4 cm2 window of the team's w043 native render (the window with the most p_min>=0.75 mass in the control maps)
into one eligible 9.362 um render at the same pitch, writes the spliced volume as zarr v2 plus a JSON receipt with the
window coordinates. Inference and screens run on the spliced volume exactly as on any eligible mesh; the window is
"flagged" if it carries the majority of the spliced volume's S1 mass and the spliced volume passes the screens that the
untouched target did not.
usage: plant_control.py --control-zarr w043.zarr --control-maps <dir with w043_*.tif> --target-zarr <render.zarr>
                        --out <dir> [--area-cm2 4] [--um 9.362]"""
import argparse, glob, json, os, numpy as np, zarr, tifffile
from scipy import ndimage

def box_sum(a, h, w):
    """Sum of a over every h x w window (top-left anchored)."""
    c = np.cumsum(np.cumsum(np.pad(a.astype(np.float64), ((1, 0), (1, 0))), 0), 1)
    return c[h:, w:] - c[:-h, w:] - c[h:, :-w] + c[:-h, :-w]

ap = argparse.ArgumentParser()
ap.add_argument("--control-zarr", required=True); ap.add_argument("--control-maps", required=True)
ap.add_argument("--target-zarr", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--area-cm2", type=float, default=4.0); ap.add_argument("--um", type=float, default=9.362)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
C = zarr.open(a.control_zarr, mode="r")["0"]; T = zarr.open(a.target_zarr, mode="r")["0"]
Zc, Hc, Wc = C.shape; Zt, Ht, Wt = T.shape
px_per_cm = 1e4 / a.um
h = int(min(2 * px_per_cm, Ht - 256)); w = int(round(a.area_cm2 * px_per_cm ** 2 / h))
assert w <= Wc - 128 and h <= Hc - 128, (h, w)
# control window: most p_min>=0.75 mass, restricted to where the control render is valid
maps = sorted(f for f in glob.glob(os.path.join(a.control_maps, "w043_*.tif")) if not f.endswith("_reverse.tif"))
ms = []
for f in maps:
    m = tifffile.imread(f).astype(np.float32); ms.append(m / 255.0 if m.max() > 1.5 else m)
pm = np.minimum.reduce(ms)[:Hc, :Wc]
cvalid = np.zeros((Hc, Wc), bool)
for y in range(0, Hc, 1024): cvalid[y:y + 1024] = C[:, y:y + 1024, :].max(axis=0) > 0
hit = (pm >= 0.75) & cvalid
S = box_sum(hit, h, w); V = box_sum(cvalid, h, w) / (h * w)
S[V < 0.98] = -1
cy, cx = np.unravel_index(np.argmax(S), S.shape)
# target location: the h x w box with the highest valid fraction in the target render
tvalid = np.zeros((Ht, Wt), bool)
for y in range(0, Ht, 1024): tvalid[y:y + 1024] = T[:, y:y + 1024, :].max(axis=0) > 0
Vt = box_sum(tvalid, h, w) / (h * w)
ty, tx = np.unravel_index(np.argmax(Vt), Vt.shape)
z0 = (Zt - Zc) // 2
spliced = T[:]
spliced[z0:z0 + Zc, ty:ty + h, tx:tx + w] = C[:, cy:cy + h, cx:cx + w]
g = zarr.open_group(os.path.join(a.out, "spliced.zarr"), mode="w", zarr_format=2)
d = g.create_array("0", shape=spliced.shape, chunks=(Zt, 128, 128), dtype=spliced.dtype, compressors=None)
d[:] = spliced
rec = {"control_zarr": a.control_zarr, "target_zarr": a.target_zarr, "um": a.um, "window_px": [h, w],
       "window_cm2": h * w / px_per_cm ** 2, "control_box_yx": [int(cy), int(cx)], "control_box_hit_mass": int(S[cy, cx]),
       "control_box_valid_frac": float(V[cy, cx]), "target_box_yx": [int(ty), int(tx)], "target_box_valid_frac": float(Vt[ty, tx]),
       "layers_placed": [z0, z0 + Zc], "control_maps_used": [os.path.basename(f) for f in maps]}
json.dump(rec, open(os.path.join(a.out, "plant.json"), "w"), indent=1); print(json.dumps(rec, indent=1))
