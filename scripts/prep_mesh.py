"""prep_mesh.py <render.zarr> <padded.zarr> <mask.tif> [--erode 64]
Valid mask = pixels with any nonzero layer at level 0, eroded 64 px (TAUIL's rule); written as uint8 TIFF at the
unpadded shape (infer aligns it top-left, so the padded border is masked out). The padded copy zero-pads Y and X up
to a multiple of 64 so the last stride-64 block sits on the grid (pre-registration, inference recipe)."""
import json, sys, time, numpy as np, zarr, tifffile
from scipy import ndimage
src, dst, maskp = sys.argv[1:4]
erode = int(sys.argv[sys.argv.index("--erode") + 1]) if "--erode" in sys.argv else 64
t = time.time()
a = zarr.open(src, mode="r")["0"][:]
Z, H, W = a.shape
valid = a.max(axis=0) > 0
er = ndimage.binary_erosion(valid, iterations=erode, border_value=0) if erode else valid
tifffile.imwrite(maskp, er.astype(np.uint8) * 255, compression="zlib")
Hp, Wp = -(-H // 64) * 64, -(-W // 64) * 64
g = zarr.open_group(dst, mode="w", zarr_format=2)
d = g.create_array("0", shape=(Z, Hp, Wp), chunks=(Z, 128, 128), dtype=a.dtype, compressors=None)
d[:, :H, :W] = a
print(json.dumps({"shape": [Z, H, W], "padded": [Z, Hp, Wp], "valid_frac": float(valid.mean()), "eroded_frac": float(er.mean()),
                  "valid_px": int(valid.sum()), "eroded_px": int(er.sum()), "prep_s": round(time.time() - t, 1)}))
