"""screens.py: the four pre-registered screens (PREREG.md, "Screens") on one mesh's ink maps.
usage: screens.py <ink-detection dir> --voxel-um 9.362 [--control-s1 X] [--mask valid_mask.tif] [--json out.json]
p_min = pixelwise minimum over the three forward maps; valid = mask (nonzero). Thresholds are TAUIL's rule, unchanged.
S1 coverage = frac(valid & p_min>=0.75).  S2 ratio = S1/S1(control) within 5x.  S3 = dominant period 4-5 mm along the
row-stacking axis (image rows) with prominence > 1.2x background.  S4 = components of p_min>=0.75 with area 0.3-2 mm2
carry the majority of S1 mass.  Pass = S1..S4 forward and S1(forward) - S1(reverse) > 0."""
import argparse, glob, json, os, numpy as np, tifffile
from scipy import ndimage, signal

def load(p):
    m = tifffile.imread(p).astype(np.float32)
    return m / 255.0 if m.max() > 1.5 else m

def pmin(files):
    ms = [load(f) for f in files]
    H = min(m.shape[0] for m in ms); W = min(m.shape[1] for m in ms)
    return np.minimum.reduce([m[:H, :W] for m in ms]), [m[:H, :W] for m in ms]

def periodicity(hit, valid, um):
    """Row profile of the >=0.75 mask along image rows; dominant period in 4-5 mm vs background 2-10 mm."""
    rows = valid.sum(1) > 0
    prof = np.where(rows, hit.sum(1) / np.maximum(valid.sum(1), 1), 0.0)
    prof = prof[rows] if rows.sum() > 64 else prof
    prof = prof - ndimage.uniform_filter1d(prof, size=max(3, int(10_000 / um)))  # detrend at 10 mm
    n = len(prof)
    if n < 256: return {"period_mm": None, "prominence": 0.0, "pass": False, "rows": int(n)}
    f, P = signal.welch(prof, fs=1.0, nperseg=min(n, 4096))
    with np.errstate(divide="ignore"):
        per_mm = np.where(f > 0, 1 / f * um / 1000.0, np.inf)
    band = (per_mm >= 4.0) & (per_mm <= 5.0); bg = (per_mm >= 2.0) & (per_mm <= 10.0)
    if band.sum() == 0: return {"period_mm": None, "prominence": 0.0, "pass": False, "rows": int(n)}
    i = np.argmax(np.where(band, P, -1)); peak = P[i]
    excl = np.abs(per_mm - per_mm[i]) < 0.1 * per_mm[i]
    back = np.median(P[bg & ~excl]) if (bg & ~excl).sum() else np.inf
    prom = float(peak / back) if back > 0 else 0.0
    return {"period_mm": float(per_mm[i]), "prominence": prom, "pass": bool(prom > 1.2), "rows": int(n)}

def stroke_scale(hit, um):
    lab, n = ndimage.label(hit, structure=np.ones((3, 3)))
    if n == 0: return {"components": 0, "mass_in_band": 0.0, "pass": False}
    areas = np.bincount(lab.ravel())[1:] * (um / 1000.0) ** 2  # mm2
    total = areas.sum(); inband = areas[(areas >= 0.3) & (areas <= 2.0)].sum()
    return {"components": int(n), "mass_in_band": float(inband / total), "pass": bool(inband / total > 0.5),
            "median_area_mm2": float(np.median(areas))}

def mask_from_zarr(zp, erode=64):
    import zarr
    a = zarr.open(zp, mode="r")["0"]
    valid = np.zeros(a.shape[1:], bool)
    for y in range(0, a.shape[1], 1024): valid[y:y+1024] = a[:, y:y+1024, :].max(axis=0) > 0
    return ndimage.binary_erosion(valid, iterations=erode, border_value=0) if erode else valid

def screens(d, um, control_s1=None, maskp=None, mask_zarr=None):
    allt = [f for f in glob.glob(os.path.join(d, "*.tif")) if not f.endswith("valid_mask.tif")]
    fw = sorted(f for f in allt if not f.endswith("_reverse.tif"))
    rv = sorted(f for f in allt if f.endswith("_reverse.tif"))
    assert len(fw) == 3, fw
    pm, ms = pmin(fw)
    valid = np.ones(pm.shape, bool)
    if mask_zarr:
        mk = mask_from_zarr(mask_zarr); valid[:] = False
        h, w = min(mk.shape[0], pm.shape[0]), min(mk.shape[1], pm.shape[1]); valid[:h, :w] = mk[:h, :w]
    elif maskp and os.path.exists(maskp):
        mk = tifffile.imread(maskp) != 0; valid[:] = False
        h, w = min(mk.shape[0], pm.shape[0]), min(mk.shape[1], pm.shape[1]); valid[:h, :w] = mk[:h, :w]
    hit = valid & (pm >= 0.75)
    s1 = float(hit.sum() / max(valid.sum(), 1))
    s1_mean3 = float(np.mean([((m >= 0.75) & valid).sum() / max(valid.sum(), 1) for m in ms]))
    r = {"files_forward": [os.path.basename(f) for f in fw], "valid_px": int(valid.sum()), "voxel_um": um,
         "S1": s1, "S1_mean_over_files": s1_mean3}
    if rv:
        pmr, _ = pmin(rv); hr = valid[:pmr.shape[0], :pmr.shape[1]] & (pmr >= 0.75)
        r["S1_reverse"] = float(hr.sum() / max(valid.sum(), 1)); r["S1_fwd_minus_rev"] = s1 - r["S1_reverse"]
    if control_s1 is not None:
        r["S2_ratio"] = s1 / control_s1 if control_s1 > 0 else None
        r["S2_pass"] = bool(control_s1 > 0 and 0.2 <= s1 / control_s1 <= 5.0)
    r["S3"] = periodicity(hit, valid, um); r["S4"] = stroke_scale(hit, um)
    r["pass"] = bool(s1 > 0 and r.get("S2_pass", True) and r["S3"]["pass"] and r["S4"]["pass"] and r.get("S1_fwd_minus_rev", 1) > 0)
    if control_s1 is not None and control_s1 > 0: r["R"] = s1 / control_s1
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("dir"); ap.add_argument("--voxel-um", type=float, required=True)
    ap.add_argument("--control-s1", type=float); ap.add_argument("--mask"); ap.add_argument("--mask-zarr"); ap.add_argument("--json")
    a = ap.parse_args()
    r = screens(a.dir, a.voxel_um, a.control_s1, a.mask or os.path.join(a.dir, "valid_mask.tif"), a.mask_zarr)
    print(json.dumps(r, indent=1))
    if a.json: json.dump(r, open(a.json, "w"), indent=1)
