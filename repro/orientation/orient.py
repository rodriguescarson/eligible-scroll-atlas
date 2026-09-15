"""Sign of the tifxyz grid normal relative to the scroll axis, for the team PHerc0800 mesh (used in the flip-normals
reproduction) and for pscamillo PHerc0800 meshes. Same normal formula for all meshes, so only the relative sign matters.
n = cross(P[i, j+1] - P[i, j], P[i+1, j] - P[i, j]) with P[i, j] = (x, y, z) from x.tif/y.tif/z.tif (rows i, cols j).
Axis centre per mesh-z: centroid of a full-wrap pscamillo mesh at the nearest z window (checked for 360 deg coverage)."""
import glob, json, os, numpy as np, tifffile
def load(d):
    X, Y, Z = (tifffile.imread(os.path.join(d, f"{c}.tif")).astype(np.float64) for c in "xyz")
    valid = (X > 0) & (Y > 0) & (Z > 0)
    return X, Y, Z, valid
def normals(X, Y, Z, valid):
    P = np.stack([X, Y, Z], -1)
    du = P[:-1, 1:] - P[:-1, :-1]; dv = P[1:, :-1] - P[:-1, :-1]
    ok = valid[:-1, :-1] & valid[:-1, 1:] & valid[1:, :-1]
    n = np.cross(du, dv); return P[:-1, :-1][ok], n[ok]
def centre(d):
    X, Y, Z, v = load(d); x, y = X[v], Y[v]; cx, cy = x.mean(), y.mean()
    ang = np.degrees(np.arctan2(y - cy, x - cx)); hist = np.histogram(ang, bins=36, range=(-180, 180))[0]
    return cx, cy, float((hist > 0).mean()), float(Z[v].mean())
def sign_stats(d, cx, cy):
    X, Y, Z, v = load(d); p, n = normals(X, Y, Z, v)
    r = p[:, :2] - np.array([cx, cy]); r /= np.linalg.norm(r, axis=1, keepdims=True) + 1e-9
    nh = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    dot = (nh[:, 0] * r[:, 0] + nh[:, 1] * r[:, 1])
    return {"n_vertices": int(len(dot)), "mean_dot_radial": float(dot.mean()), "frac_outward": float((dot > 0).mean()), "mean_abs_nz": float(np.abs(nh[:, 2]).mean())}
out = {}
team = "orient/team_mesh"; tX, tY, tZ, tv = load(team); tz = float(tZ[tv].mean())
cands = sorted(glob.glob("meshes/PHerc0800/z*_w*"))
zs = sorted({int(os.path.basename(c).split("_")[0][1:]) for c in cands})
zwin = min(zs, key=lambda z: abs(z + 400 - tz))  # windows are +-400 around the z in the name? report both
out["team_mesh_mean_z"] = tz; out["nearest_window"] = zwin
cs = {}
for c in [c for c in cands if os.path.basename(c).startswith(f"z{zwin}_")]:
    cs[os.path.basename(c)] = centre(c)
out["pscamillo_centres"] = {k: {"cx": v[0], "cy": v[1], "angular_coverage": v[2], "mean_z": v[3]} for k, v in cs.items()}
full = [v for v in cs.values() if v[2] > 0.95]; cx = float(np.median([v[0] for v in full])); cy = float(np.median([v[1] for v in full]))
out["axis_centre_used"] = [cx, cy]
out["team"] = sign_stats(team, cx, cy)
out["pscamillo"] = {os.path.basename(c): sign_stats(c, cx, cy) for c in cands if os.path.basename(c).startswith(f"z{zwin}_")}
# every PHerc0800 pscamillo mesh with its own centroid as the axis (full wraps)
allsig = {}
for c in cands:
    cx2, cy2, cov, _ = centre(c)
    if cov > 0.95: allsig[os.path.basename(c)] = sign_stats(c, cx2, cy2)["frac_outward"]
out["pscamillo_all_frac_outward_summary"] = {"n": len(allsig), "min": min(allsig.values()), "median": float(np.median(list(allsig.values()))), "max": max(allsig.values())}
json.dump(out, open("orient/orient.json", "w"), indent=1); print(json.dumps(out, indent=1))
