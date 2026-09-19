#!/usr/bin/env python3
"""Depth profile of Hecate 9.6 um 3D ink probability, exactly as pre-registered in prereg/HECATE-3D.md.

usage: hecate_profile.py <name> <render.zarr> <ink2d.png> <ink3d.zarr> <out.json>
"""
import json, sys
import numpy as np
import zarr
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
name, render_path, png_path, zarr3d_path, out_path = sys.argv[1:6]
CENTRE, ERODE, ROWS = 15, 64, 512


def array0(path):
    node = zarr.open(path, mode="r")
    return node["0"] if hasattr(node, "keys") and "0" in node else node


render = array0(render_path)
vol = array0(zarr3d_path)
attrs = dict(vol.attrs)
if "evaluated_z_interval" not in attrs:          # attributes may sit on the group rather than the array
    attrs = dict(zarr.open(zarr3d_path, mode="r").attrs)
z0, z1 = (int(v) for v in attrs["evaluated_z_interval"])
H, W = render.shape[1], render.shape[2]

p2d = np.asarray(Image.open(png_path))
assert p2d.shape == (H, W), (p2d.shape, (H, W))
assert tuple(vol.shape[1:]) == (H, W), (vol.shape, (H, W))

# valid: render nonzero at the surface plane, eroded 64 px city-block with the image edge counted as outside
# (identical to binary_erosion(valid, iterations=64, border_value=0) with the default cross element)
valid = np.zeros((H, W), bool)
for r in range(0, H, ROWS):
    valid[r:r + ROWS] = np.asarray(render[CENTRE, r:r + ROWS, :]) > 0
dist = ndimage.distance_transform_cdt(np.pad(valid, 1), metric="taxicab")[1:-1, 1:-1]
valid &= dist > ERODE
ink = valid & (p2d >= 128)        # probability >= 0.5 on the round(255 p) scale
nonink = valid & (p2d <= 25)      # probability < 0.1

planes = list(range(z0, z1))
mass_ink = np.zeros(len(planes)); mass_non = np.zeros(len(planes))
for r in range(0, H, ROWS):
    block = np.asarray(vol[z0:z1, r:r + ROWS, :], dtype=np.float32) / 255.0
    mi, mn = ink[r:r + ROWS], nonink[r:r + ROWS]
    if mi.any(): mass_ink += block[:, mi].sum(axis=1)
    if mn.any(): mass_non += block[:, mn].sum(axis=1)


def metrics(mass):
    total = float(mass.sum())
    if total <= 0:
        return {"profile": [0.0] * len(planes), "argmax_plane": None, "argmax_offset": None, "LC": None, "CF": None}
    prof = mass / total
    k = int(np.argmax(prof)); plane = planes[k]
    lc = float(prof[max(0, k - 2):k + 3].sum())
    cf = float(sum(p for z, p in zip(planes, prof) if abs(z - CENTRE) <= 2))
    return {"profile": [round(float(x), 6) for x in prof], "argmax_plane": plane,
            "argmax_offset": plane - CENTRE, "LC": round(lc, 6), "CF": round(cf, 6)}


ink_m, non_m = metrics(mass_ink), metrics(mass_non)
passes = (ink_m["argmax_offset"] is not None and abs(ink_m["argmax_offset"]) <= 3 and ink_m["LC"] >= 0.50)
out = {"name": name, "shape_yx": [H, W], "evaluated_z_interval": [z0, z1], "centre_plane": CENTRE,
       "flat_LC": round(5 / len(planes), 6), "n_valid": int(valid.sum()), "n_ink": int(ink.sum()),
       "n_nonink": int(nonink.sum()), "ink": ink_m, "nonink": non_m,
       "control_criterion_met": bool(passes),
       "criterion": "|argmax_offset| <= 3 and LC >= 0.50 (prereg/HECATE-3D.md, tag prereg-hecate3d-v1)"}
json.dump(out, open(out_path, "w"), indent=1)
print(json.dumps({k: out[k] for k in ("name", "n_ink", "control_criterion_met")}),
      "ink:", {k: ink_m[k] for k in ("argmax_offset", "LC", "CF")},
      "nonink:", {k: non_m[k] for k in ("argmax_offset", "LC", "CF")}, flush=True)
