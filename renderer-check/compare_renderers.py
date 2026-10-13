"""Does a CPU Python renderer reproduce what VC3D wrote, on a different scroll and scan type?

Ours was rendered by VC3D with --flip-normals and 31 slices (depth d = i - 15).
The CPU renderer writes 66 layers with VC's default normal (depth d = k - 33).
If the flip is the only difference, our layer i is the renderer's layer 48 - i.
The unflipped mapping, 18 + i, is carried as the control: it should be clearly worse.
"""
import glob, sys
import numpy as np, zarr

ours_p, theirs_p = sys.argv[1], sys.argv[2]
A = zarr.open(glob.glob(ours_p + "/*.zarr")[0], mode="r")["0"]   # VC3D, 31 layers
B = zarr.open(theirs_p, mode="r")["0"]                            # CPU, 66 layers
print(f"VC3D {A.shape}   CPU {B.shape}")
assert A.shape[1:] == B.shape[1:], "canvas differs"

rows = slice(0, A.shape[1])
cols = slice(0, A.shape[2], 4)        # subsample columns; every row kept
a = A[:, rows, cols].astype(np.int16)
valid = (a > 0).all(axis=0)
print(f"valid pixels {valid.sum():,} of {valid.size:,} ({100*valid.mean():.1f}%)\n")

def score(mapfn, label):
    w1 = tot = 0
    diffs, cors = [], []
    for i in range(A.shape[0]):
        k = mapfn(i)
        if not (0 <= k < B.shape[0]):
            continue
        b = B[k, rows, cols].astype(np.int16)
        d = np.abs(a[i] - b)[valid]
        w1 += int((d <= 1).sum()); tot += d.size
        diffs.append(d.mean())
        x, y = a[i][valid].astype(np.float64), b[valid].astype(np.float64)
        cors.append(np.corrcoef(x, y)[0, 1])
    print(f"{label}: within 1 grey level {100*w1/tot:.3f}%  "
          f"mean |diff| {np.mean(diffs):.2f}  median r {np.median(cors):.5f}")
    return w1 / tot

flip = score(lambda i: 48 - i, "flipped  (ours[i] = theirs[48-i])")
noflip = score(lambda i: 18 + i, "unflipped(ours[i] = theirs[18+i]) <- control")
print(f"\nflipped mapping is {'BETTER' if flip > noflip else 'WORSE'} than the control "
      f"({100*flip:.2f}% vs {100*noflip:.2f}%)")

# per-layer detail on the better mapping
m = (lambda i: 48 - i) if flip > noflip else (lambda i: 18 + i)
print("\nper layer (better mapping):")
for i in range(0, A.shape[0], 5):
    b = B[m(i), rows, cols].astype(np.int16)
    d = np.abs(a[i] - b)[valid]
    print(f"  ours d={i-15:+3d} vs theirs k={m(i):2d}: within1 {100*(d<=1).mean():6.2f}%  "
          f"mean|diff| {d.mean():5.2f}  max {d.max():3d}")
