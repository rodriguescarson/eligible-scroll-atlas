"""sheet_offset.py <scroll> <mesh> — is a rendered surface actually sitting on a papyrus sheet?

The render already samples the CT along the surface normal at 31 depths, so the question needs no
raw CT, no umbilicus and no ray casting: inside a small patch, mean intensity across depth peaks
where the sheet is. A surface that follows a sheet puts that peak at depth 0 everywhere; a surface
that ignores the sheets puts it anywhere within half a sheet spacing.

Reports the spread of the per-patch peak offset. Calibrated against the team's curated PHerc0139
w043 surface, which carries readable ink: there the offsets sit in an interquartile range 1.1
voxels wide with 46% of patches within 2 voxels of the surface.
"""
import csv, glob, os, subprocess, sys, tarfile
import numpy as np, zarr

BASE = "https://huggingface.co/datasets/rodriguescarson/eligible-scroll-atlas-renders/resolve/main"
B = 64                      # patch side, rendered pixels
COLSTEP = 4                 # column subsample; rows kept whole

def measure(zpath):
    a = zarr.open(zpath, mode="r")["0"]
    Z = a.shape[0]
    v = a[:, :, ::COLSTEP].astype(np.float32)
    H, W = v.shape[1], v.shape[2]
    c = Z // 2
    offs, cons = [], []
    for i in range(0, H - B + 1, B):
        for j in range(0, W - B + 1, B):
            blk = v[:, i:i + B, j:j + B]
            m = (blk > 0).all(axis=0)
            if m.sum() < 0.9 * B * B:
                continue
            prof = blk[:, m].mean(axis=1)
            k = int(np.argmax(prof))
            if 0 < k < Z - 1:
                y0, y1, y2 = prof[k - 1], prof[k], prof[k + 1]
                d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-9)
            else:
                d = 0.0
            offs.append(k + d - c)
            cons.append(float(prof.max() - prof.min()))
    if len(offs) < 20:
        return None
    o = np.array(offs)
    q1, q3 = np.percentile(o, [25, 75])
    return dict(patches=len(o), contrast=float(np.median(cons)),
                median_off=float(np.median(o)), iqr=float(q3 - q1),
                within2=float(np.mean(np.abs(o) <= 2)),
                within1=float(np.mean(np.abs(o) <= 1)))

def main():
    scroll, mesh, work = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(work, exist_ok=True)
    tar = os.path.join(work, "sv.tar")
    url = f"{BASE}/{scroll}/{mesh}/surface-volumes.tar"
    subprocess.run(["curl", "-sfL", "-o", tar, url], check=True, timeout=1800)
    with tarfile.open(tar) as t:
        t.extractall(work, filter="data")
    os.remove(tar)
    z = glob.glob(os.path.join(work, "surface-volumes", "*.zarr"))
    if not z:
        raise SystemExit("no zarr in tar")
    r = measure(z[0])
    print("" if r is None else
          f"{r['patches']},{r['contrast']:.2f},{r['median_off']:.3f},{r['iqr']:.3f},"
          f"{r['within2']:.4f},{r['within1']:.4f}")

if __name__ == "__main__":
    main()
