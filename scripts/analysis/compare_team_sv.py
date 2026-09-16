"""compare_team_sv.py <local_render.zarr> <team_surface_volume.zarr or URL>: layer-order convention check on a central
2048x2048 window (limits remote reads). Prints Pearson r for the render as is and with its layers reversed."""
import json, sys, numpy as np, zarr
a = zarr.open(sys.argv[1], mode="r")["0"]; b = zarr.open(sys.argv[2], mode="r")["0"]
Z, H, W = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1]), min(a.shape[2], b.shape[2])
h, w = min(2048, H), min(2048, W); y0, x0 = H // 2 - h // 2, W // 2 - w // 2
A = a[:Z, y0:y0 + h, x0:x0 + w].astype(np.float32); T = b[:Z, y0:y0 + h, x0:x0 + w].astype(np.float32)
def corr(x, y):
    m = (x > 0) & (y > 0); return (float(np.corrcoef(x[m], y[m])[0, 1]) if m.sum() > 1000 else None), float(np.abs(x[m] - y[m]).mean()) if m.sum() else None, int(m.sum())
r, mad, n = corr(A, T); rr, madr, nr = corr(A[::-1], T)
print(json.dumps({"render_shape": list(a.shape), "team_shape": list(b.shape), "window": [y0, x0, h, w], "r_as_is": r, "mad_as_is": mad, "voxels": n,
                  "r_layers_reversed": rr, "mad_layers_reversed": madr, "flip_normals_matches_team": bool(r is not None and rr is not None and r > rr)}))
