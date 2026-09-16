#!/usr/bin/env bash
# setup.sh: public checkpoint + synthetic canvases for the Hecate memory sweep. No private data is needed: the question is how
# peak GPU memory scales with batch and canvas, and synthetic uint8 volumes exercise the identical code path.
set -u
W=/workspace; L=$W/sweep/progress.log; mkdir -p $W/sweep
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > $W/sweep/apt.out 2>&1; apt-get install -y -qq python3-pip git > $W/sweep/apt.out 2>&1; log "apt rc=$?"
python3 -m pip install -q --break-system-packages torch numpy zarr pillow huggingface_hub >> $W/sweep/pip.out 2>&1; log "pip rc=$?"
cd $W/sweep && python3 - <<'PY' >> $L 2>&1
from huggingface_hub import hf_hub_download
import shutil
for f in ("hecate.py", "hecate_9.6um.pth"):
    p = hf_hub_download("scrollprize/hecate", f, local_dir="/workspace/sweep/hecate")
    print("fetched", f, p)
PY
log "checkpoint+code fetched rc=$?"
python3 - <<'PY' >> $L 2>&1
import numpy as np, zarr, os
# canvases spanning the range seen in the September pass: 2.5, 11.5 and 29.8 megapixels, 31 planes as rendered
rng = np.random.default_rng(0)
for mpx, (h, w) in {"2p5": (1600, 1560), "11p5": (2100, 5480), "29p8": (2380, 12520)}.items():
    p = f"/workspace/sweep/canvas_{mpx}.zarr"
    if os.path.exists(p): continue
    g = zarr.open_group(p, mode="w", zarr_format=2)
    a = g.create_array("0", shape=(31, h, w), chunks=(31, 256, 256), dtype="u1", compressors=None)
    for y in range(0, h, 256):
        blk = rng.integers(60, 200, size=(31, min(256, h - y), w), dtype=np.uint8)
        a[:, y:y + blk.shape[1], :] = blk
    print("built", p, (31, h, w), round(h * w / 1e6, 1), "Mpx")
PY
log "SETUP DONE"
