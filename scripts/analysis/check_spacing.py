"""check_spacing.py <native_9.6.zarr> <source.zarr> <source_um> [--target-um 9.6]
K2 on a central 1024x1024 window (memory-safe): a direct-to-9.6 um render must match a trilinear resample of the
source-spacing render of the same mesh. Pass: in-plane size within 0.5 % of expected, Pearson r >= 0.98 over voxels
non-zero in both."""
import json, sys, numpy as np, zarr
from scipy import ndimage
a_p, b_p, s_um = sys.argv[1], sys.argv[2], float(sys.argv[3]); t_um = float(sys.argv[sys.argv.index("--target-um") + 1]) if "--target-um" in sys.argv else 9.6
Aa = zarr.open(a_p, mode="r")["0"]; Bb = zarr.open(b_p, mode="r")["0"]; f = s_um / t_um
exp_hw = (Bb.shape[1] * f, Bb.shape[2] * f)
size_err = max(abs(Aa.shape[1] - exp_hw[0]) / exp_hw[0], abs(Aa.shape[2] - exp_hw[1]) / exp_hw[1])
n = min(1024, Aa.shape[1], Aa.shape[2]); y0, x0 = Aa.shape[1] // 2 - n // 2, Aa.shape[2] // 2 - n // 2
A = Aa[:, y0:y0 + n, x0:x0 + n].astype(np.float32)
by0, bx0 = max(0, int(y0 / f) - 4), max(0, int(x0 / f) - 4); by1, bx1 = min(Bb.shape[1], int((y0 + n) / f) + 6), min(Bb.shape[2], int((x0 + n) / f) + 6)
B = Bb[:, by0:by1, bx0:bx1].astype(np.float32)
za, zb = (Aa.shape[0] - 1) / 2, (Bb.shape[0] - 1) / 2
best = None
for dz in (-0.5, 0.0, 0.5):
    for off in (0.0, 0.5):
        zz = (zb + (np.arange(A.shape[0]) - za) / f + dz).astype(np.float32)
        yy = ((np.arange(y0, y0 + n) + off) / f - off - by0).astype(np.float32)
        xx = ((np.arange(x0, x0 + n) + off) / f - off - bx0).astype(np.float32)
        R = np.empty_like(A)
        for i, z in enumerate(zz):
            Y, X = np.meshgrid(yy, xx, indexing="ij")
            R[i] = ndimage.map_coordinates(B, [np.full(Y.shape, z, np.float32), Y, X], order=1, mode="constant", cval=0)
        m = (A > 0) & (R > 0)
        r = float(np.corrcoef(A[m], R[m])[0, 1]) if m.sum() > 1000 else -1.0
        if best is None or r > best["r"]: best = {"r": r, "dz_layers": dz, "pixel_offset": off, "voxels": int(m.sum())}
print(json.dumps({"native": list(Aa.shape), "source": list(Bb.shape), "expected_hw": exp_hw, "size_err": size_err, "window": [y0, x0, n], "best": best, "pass": bool(size_err <= 0.005 and best["r"] >= 0.98)}, indent=1))
