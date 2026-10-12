"""Positive control for the sheet-offset test: the team's curated PHerc0139 w043 surface,
which carries readable ink and is therefore known to lie on a sheet. Several slabs, so the
calibration is not one lucky window."""
import json, sys
import numpy as np, zarr

U = ("https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0139/segments/"
     "20260112000000-w043_2026011217/surface-volumes/9.362um-1.2m-113keV-volume-20250728140407.zarr")
B = 64

def patches(v):
    Z, H, W = v.shape
    c = Z // 2
    offs, cons = [], []
    for i in range(0, H - B + 1, B):
        for j in range(0, W - B + 1, B):
            blk = v[:, i:i+B, j:j+B]
            m = (blk > 0).all(axis=0)
            if m.sum() < 0.9 * B * B:
                continue
            prof = blk[:, m].mean(axis=1)
            k = int(np.argmax(prof))
            if 0 < k < Z - 1:
                y0, y1, y2 = prof[k-1], prof[k], prof[k+1]
                d = 0.5 * (y0 - y2) / (y0 - 2*y1 + y2 + 1e-9)
            else:
                d = 0.0
            offs.append(k + d - c); cons.append(float(prof.max() - prof.min()))
    return offs, cons

a = zarr.open(U, mode="r")["0"]
Z, H, W = a.shape
print(f"control surface {a.shape}", flush=True)
allo, allc, rows = [], [], []
for (r0, c0) in [(1024, 2048), (2560, 3072), (3584, 1024), (4608, 4096)]:
    v = a[:, r0:r0+1024, c0:c0+2048].astype(np.float32)
    o, cn = patches(v)
    if len(o) < 20:
        print(f"  slab r{r0} c{c0}: too few valid patches", flush=True); continue
    o = np.array(o)
    q1, q3 = np.percentile(o, [25, 75])
    rows.append(dict(slab=f"r{r0}_c{c0}", patches=len(o), contrast=float(np.median(cn)),
                     median_off=float(np.median(o)), iqr=float(q3-q1),
                     within2=float(np.mean(np.abs(o) <= 2))))
    print(f"  slab r{r0} c{c0}: n={len(o):4d} contrast={np.median(cn):5.1f} "
          f"IQR={q3-q1:5.2f} within2={100*np.mean(np.abs(o)<=2):4.0f}%", flush=True)
    allo += list(o); allc += cn

o = np.array(allo); q1, q3 = np.percentile(o, [25, 75])
summary = dict(source=U, slabs=rows, patches=len(o), contrast=float(np.median(allc)),
               median_off=float(np.median(o)), iqr=float(q3-q1),
               within2=float(np.mean(np.abs(o) <= 2)), within1=float(np.mean(np.abs(o) <= 1)))
json.dump(summary, open("phase2/control_w043.json", "w"), indent=1)
np.save("phase2/control_w043_offsets.npy", o)
print(f"\nPOOLED CONTROL: n={len(o)} contrast={summary['contrast']:.1f} "
      f"median={summary['median_off']:+.2f} IQR={summary['iqr']:.2f} "
      f"within2={100*summary['within2']:.0f}% within1={100*summary['within1']:.0f}%")
