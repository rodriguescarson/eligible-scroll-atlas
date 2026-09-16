# make_canvases.py: synthetic uint8 canvases spanning the range seen in the September pass. Written against whichever zarr API
# is installed, and it verifies each group reads back before declaring success.
import os, sys, numpy as np, zarr
SIZES = {"2p5": (1600, 1560), "11p5": (2100, 5480), "29p8": (2380, 12520)}
rng = np.random.default_rng(0)
major = int(zarr.__version__.split(".")[0])
print("zarr", zarr.__version__, "major", major, flush=True)
for name, (h, w) in SIZES.items():
    p = f"/workspace/sweep/canvas_{name}.zarr"
    if os.path.exists(p):
        print("exists", p); continue
    if major >= 3:
        g = zarr.open_group(p, mode="w")
        a = g.create_array("0", shape=(31, h, w), chunks=(31, 256, 256), dtype="u1", compressors=None)
    else:
        g = zarr.open_group(p, mode="w")
        a = g.create_dataset("0", shape=(31, h, w), chunks=(31, 256, 256), dtype="u1", compressor=None)
    for y in range(0, h, 256):
        blk = rng.integers(60, 200, size=(31, min(256, h - y), w), dtype=np.uint8)
        a[:, y:y + blk.shape[1], :] = blk
    chk = zarr.open_group(p, mode="r")["0"]
    assert chk.shape == (31, h, w), chk.shape
    print("built", p, chk.shape, round(h * w / 1e6, 1), "Mpx", flush=True)
built = len([d for d in os.listdir("/workspace/sweep") if d.endswith(".zarr")])
print("canvases on disk:", built)
sys.exit(0 if built == len(SIZES) else 1)
