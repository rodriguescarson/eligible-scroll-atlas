# radial_pitch.py <run_dir> <umbilicus.json> <ref_meshes_dir> <out_dir> [z0]
# Is our fit's winding pitch physical? At slice z0, cast 12 rays from the official umbilicus; sample the scan (raw level-0 chunks over
# HTTP, mean of 9 slices x 3 perpendicular offsets); detrend; find sheet peaks. Along the same rays, take the radius where each of our
# exported windings and each pscamillo mesh crosses. Compare our pitch with the scan's peak spacing and autocorrelation period in
# bands around our w027, w051, w073 (the windings his three meshes land on).
import glob, json, os, sys, urllib.request, numpy as np, tifffile
from concurrent.futures import ThreadPoolExecutor
from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.signal import find_peaks
from PIL import Image, ImageDraw
run, umb, refdir, out = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], sys.argv[4]
z0 = int(sys.argv[5]) if len(sys.argv) > 5 else 6928
os.makedirs(out, exist_ok=True)
B = sys.argv[6] if len(sys.argv) > 6 else "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0826/volumes/20250821151701-9.362um-1.2m-113keV-masked.zarr/0"
_zmeta = json.loads(urllib.request.urlopen(B + "/.zarray", timeout=60).read().decode())
C = int(_zmeta["chunks"][0]); SHAPE = tuple(int(s) for s in _zmeta["shape"])
print("volume", B.rsplit("/", 2)[-2], "shape", SHAPE, "chunks", C, flush=True)
cp = sorted(json.load(open(umb))["control_points"], key=lambda p: p["z"]); zs = np.array([p["z"] for p in cp], float)
ux = float(np.interp(z0, zs, [p["x"] for p in cp])); uy = float(np.interp(z0, zs, [p["y"] for p in cp]))
def dens(d, up=4):
    P = np.stack([tifffile.imread(f"{d}/{c}.tif").astype(np.float32) for c in "xyz"], -1); ok = (P > 0).all(-1)
    q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    c00, c01, c10, c11 = P[:-1, :-1][q], P[:-1, 1:][q], P[1:, :-1][q], P[1:, 1:][q]
    t = (np.arange(up, dtype=np.float32) + 0.5) / up; a, b = np.meshgrid(t, t, indexing="ij"); a = a.reshape(1, -1, 1); b = b.reshape(1, -1, 1)
    p = ((1 - a) * (1 - b) * c00[:, None] + (1 - a) * b * c01[:, None] + a * (1 - b) * c10[:, None] + a * b * c11[:, None]).reshape(-1, 3)
    p = p[np.abs(p[:, 2] - z0) < 3]
    return np.hypot(p[:, 0] - ux, p[:, 1] - uy), np.degrees(np.arctan2(p[:, 1] - uy, p[:, 0] - ux)) % 360
ours = {int(os.path.basename(d.rstrip("/"))[1:]): dens(d.rstrip("/")) for d in sorted(glob.glob(run + "meshes/all/w*/"))}
refs = {os.path.basename(d): dens(d) for d in sorted(glob.glob(refdir + "/z6528_w*"))}
def radius_on_ray(rt, th, tol=0.7):
    r, a = rt
    if len(r) == 0: return None
    dd = np.abs((a - th + 180) % 360 - 180); s = dd < tol
    return float(np.median(r[s])) if s.sum() >= 2 else None
ANG = [15 + 30 * k for k in range(12)]
w_all = {w: np.median(rt[0]) if len(rt[0]) else np.nan for w, rt in ours.items()}
r_all_max = max((float(rt[0].max()) for rt in ours.values() if len(rt[0])), default=1500.0)
Rmax = int(min(4100, r_all_max + 150))
print("umbilicus at z0", z0, "x %.1f y %.1f" % (ux, uy), "| sanity: median r w000 %.1f w001 %.1f w089 %.1f" % (w_all.get(0, np.nan), w_all.get(1, np.nan), w_all.get(89, np.nan)), "| Rmax", Rmax, flush=True)
rr = np.arange(Rmax, dtype=np.float32); coords = {}
keys = set()
for th in ANG:
    c, s = np.cos(np.radians(th)), np.sin(np.radians(th)); X, Y, Z = [], [], []
    for dz in range(-4, 5):
        for dp in (-1, 0, 1):
            X.append(np.rint(ux + rr * c - dp * s)); Y.append(np.rint(uy + rr * s + dp * c)); Z.append(np.full(Rmax, z0 + dz))
    X, Y, Z = (np.stack(v).astype(np.int64) for v in (X, Y, Z)); coords[th] = (Z, Y, X)
    inb = (X >= 0) & (Y >= 0) & (X < SHAPE[2]) & (Y < SHAPE[1])
    keys.update(zip((Z[inb] // C).tolist(), (Y[inb] // C).tolist(), (X[inb] // C).tolist()))
def fetch(k):
    try:
        b = urllib.request.urlopen(f"{B}/{k[0]}/{k[1]}/{k[2]}", timeout=90).read(); a = np.frombuffer(b, np.uint8)
        return k, (a.reshape(C, C, C) if a.size == C ** 3 else None)
    except Exception:
        return k, None
with ThreadPoolExecutor(32) as ex: cache = dict(ex.map(fetch, sorted(keys)))
print("chunks", len(keys), "missing/empty", sum(v is None for v in cache.values()), flush=True)
res = {"z0": z0, "umbilicus_xy": [ux, uy], "volume": B, "volume_shape": list(SHAPE), "rays": {}}
panels = []
profiles = {}
for th in ANG:
    Z, Y, X = coords[th]; vals = np.zeros(Z.shape, np.float32); good = np.zeros(Z.shape, bool)
    inb = (X >= 0) & (Y >= 0) & (X < SHAPE[2]) & (Y < SHAPE[1])
    kz, ky, kx = Z // C, Y // C, X // C
    for k in set(zip(kz[inb].tolist(), ky[inb].tolist(), kx[inb].tolist())):
        a = cache.get(k)
        if a is None: continue
        m = inb & (kz == k[0]) & (ky == k[1]) & (kx == k[2])
        vals[m] = a[Z[m] % C, Y[m] % C, X[m] % C]; good[m] = True
    good &= vals > 0
    prof = np.where(good.sum(0) > 0, (vals * good).sum(0) / np.maximum(good.sum(0), 1), np.nan)
    f = np.where(np.isnan(prof), np.nanmedian(prof), prof)
    sm = gaussian_filter1d(f, 1.0); det = sm - median_filter(sm, 41)
    noise = 1.4826 * np.median(np.abs(det - np.median(det)))
    pk, _ = find_peaks(det, distance=4, prominence=noise)
    radii = {w: radius_on_ray(rt, th) for w, rt in ours.items()}; radii = {w: r for w, r in radii.items() if r is not None}
    rref = {n: radius_on_ray(rt, th) for n, rt in refs.items()}
    ray = {"n_our_windings": len(radii), "our_radii": {f"w{w:03d}": round(r, 1) for w, r in sorted(radii.items())},
           "ref_radii": {n: (round(r, 1) if r is not None else None) for n, r in rref.items()}, "bands": {}}
    ow = sorted(radii.items(), key=lambda x: x[1])
    if ow:
        r_in, r_out = ow[0][1], ow[-1][1]; ray["scan_peaks_between_inner_and_outer_winding"] = int(((pk >= r_in) & (pk <= r_out)).sum())
        a0, a1 = int(r_in), int(min(Rmax - 1, r_out))
        for kk in (2, 3):
            pk_k, _ = find_peaks(det, distance=4, prominence=kk * noise); ray[f"scan_peaks_span_k{kk}"] = int(((pk_k >= a0) & (pk_k <= a1)).sum())
        seg = det[a0:a1] - det[a0:a1].mean()
        if len(seg) > 130:
            ac = np.correlate(seg, seg, "full")[len(seg) - 1:]; ac = ac / (ac[0] + 1e-9)
            lm = [L for L in range(8, 61) if ac[L] > ac[L - 1] and ac[L] >= ac[L + 1] and ac[L] > 0.05]
            ray["span_autocorr_period"] = lm[0] if lm else None
            ray["sheet_count_from_period"] = round((a1 - a0) / lm[0], 1) if lm else None
    profiles[f"det_{th}"] = det.astype(np.float32); profiles[f"prof_{th}"] = np.nan_to_num(prof).astype(np.float32)
    for w in (27, 51, 73):
        if w not in radii: continue
        lo, hi = int(max(0, radii[w] - 60)), int(min(Rmax, radii[w] + 60))
        if hi - lo < 40: continue
        ob = sorted(r for r in radii.values() if lo <= r <= hi); pb = pk[(pk >= lo) & (pk <= hi)]
        seg = det[lo:hi] - det[lo:hi].mean(); ac = np.correlate(seg, seg, "full")[len(seg) - 1:]; ac = ac / (ac[0] + 1e-9)
        lm = [L for L in range(4, 41) if ac[L] > ac[L - 1] and ac[L] >= ac[L + 1] and ac[L] > 0.1]
        ray["bands"][f"w{w:03d}"] = dict(r=round(radii[w], 1), our_n=len(ob), our_pitch=round(float(np.median(np.diff(ob))), 1) if len(ob) > 2 else None,
            scan_peaks_n=int(len(pb)), scan_peak_pitch=round(float(np.median(np.diff(pb))), 1) if len(pb) > 2 else None, scan_autocorr_period=(lm[0] if lm else None),
            valid_share=round(float(np.mean(~np.isnan(prof[lo:hi]))), 2))
    res["rays"][str(th)] = ray
    if len(panels) < 4 and 51 in radii and radii[51] + 60 < Rmax:
        lo, hi = int(max(0, radii[51] - 120)), int(min(Rmax, radii[51] + 120)); W, H = 1200, 200; im = Image.new("RGB", (W, H), (255, 255, 255)); dr = ImageDraw.Draw(im)
        seg = det[lo:hi]; s = (seg - seg.min()) / (np.ptp(seg) + 1e-9)
        dr.line([(i * W / (hi - lo), H - 20 - s[i] * (H - 40)) for i in range(hi - lo)], fill=(0, 0, 0), width=1)
        for r in radii.values():
            if lo <= r < hi: x = (r - lo) * W / (hi - lo); dr.line([(x, 0), (x, 14)], fill=(220, 0, 0), width=2)
        for p in pk[(pk >= lo) & (pk < hi)]: x = (p - lo) * W / (hi - lo); dr.ellipse([x - 2, H - 14, x + 2, H - 10], fill=(0, 150, 0))
        for n, r in rref.items():
            if r is not None and lo <= r < hi: x = (r - lo) * W / (hi - lo); dr.line([(x, H - 8), (x, H)], fill=(0, 0, 220), width=3)
        dr.text((4, 16), f"ray {th} deg, r {lo}-{hi} vx: red = our windings, green = scan peaks, blue = pscamillo", fill=(0, 0, 0)); panels.append(im)
summ = {}
for w in ("w027", "w051", "w073"):
    b = [ray["bands"][w] for ray in res["rays"].values() if w in ray["bands"]]
    g = lambda k: [x[k] for x in b if x[k] is not None]
    summ[w] = dict(rays=len(b), our_pitch_median=float(np.median(g("our_pitch"))) if g("our_pitch") else None, our_n_median=float(np.median(g("our_n"))) if b else None,
                   scan_peak_pitch_median=float(np.median(g("scan_peak_pitch"))) if g("scan_peak_pitch") else None, scan_peaks_n_median=float(np.median(g("scan_peaks_n"))) if b else None,
                   scan_autocorr_median=float(np.median(g("scan_autocorr_period"))) if g("scan_autocorr_period") else None)
res["summary"] = summ
res["summary"]["windings_vs_scan_peaks_inner_to_outer"] = [(ray["n_our_windings"], ray.get("scan_peaks_between_inner_and_outer_winding")) for ray in res["rays"].values()]
res["summary"]["per_ray_ours_vs_scan"] = [dict(ray=th, ours=ray["n_our_windings"], peaks_k1=ray.get("scan_peaks_between_inner_and_outer_winding"), peaks_k2=ray.get("scan_peaks_span_k2"), peaks_k3=ray.get("scan_peaks_span_k3"), period=ray.get("span_autocorr_period"), count_from_period=ray.get("sheet_count_from_period")) for th, ray in res["rays"].items()]
np.savez_compressed(f"{out}/profiles.npz", **profiles)
json.dump(res, open(f"{out}/radial_pitch.json", "w"), indent=1); print(json.dumps(res["summary"], indent=1))
if panels:
    canvas = Image.new("RGB", (1200, 200 * len(panels)), (255, 255, 255))
    for i, p in enumerate(panels): canvas.paste(p, (0, 200 * i))
    canvas.save(f"{out}/radial_w051_panels.png")
