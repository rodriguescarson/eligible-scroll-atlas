#!/usr/bin/env bash
# hecate_cand.sh: Hecate 9.6 um, both directions, on the four held PHerc0813 meshes ahead of the main queue (private)
set -u
W=/workspace/atlas; O=$W/h96/cand; L=$O/progress.log; mkdir -p $O $W/tools/stub.zarr
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=/workspace/vc3d_cfg TMPDIR=$W/tmp
PY=$W/villa/vesuvius/.venv/bin/python; APP=$W/tools/VC3D.AppImage; HEC=$W/hecate
URL=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0813/volumes/20250821151723-9.362um-1.2m-113keV-masked.zarr
for m in z7696_w020 z13088_w040 z5888_w020 z12496_w060; do
  D=$O/PHerc0813_$m; mkdir -p $D; t0=$(date +%s)
  $APP vc_render_tifxyz --volume $W/tools/stub.zarr --remote-url $URL --segmentation $W/meshes/PHerc0813/$m --scale 0.9752083 --group-idx 0 --num-slices 31 --slice-step 1.0254218 --cache-gb 8 --voxel-size 9.362 --voxel-unit micrometer --flip-normals --zarr-compressor zstd --timeout 30 --zarr-output $D/r96.zarr > $D/render.out 2>&1
  log "RENDER $m rc=$? secs=$(( $(date +%s) - t0 ))"
  for dir in fwd rev; do
    F=""; [ $dir = rev ] && F="--reverse"; t0=$(date +%s)
    $PY $HEC/hecate.py --checkpoint $HEC/hecate_9.6um.pth --input $D/r96.zarr --spacing-um 9.6 --output $D/hecate_$dir.png --device cuda --precision bf16 --batch-size 64 $F > $D/hecate_$dir.log 2>&1
    log "HECATE $m $dir rc=$? secs=$(( $(date +%s) - t0 ))"
  done
  $PY - $D <<'PY' >> $L 2>&1
import sys, numpy as np, zarr
from PIL import Image
from scipy import ndimage
d = sys.argv[1]; a = zarr.open(d + "/r96.zarr", mode="r")["0"]
valid = a[:].max(axis=0) > 0; er = ndimage.binary_erosion(valid, iterations=64, border_value=0)
res = {}
for dirn in ("fwd", "rev"):
    p = np.asarray(Image.open(f"{d}/hecate_{dirn}.png")).astype(np.float32) / 255.0
    h, w = min(p.shape[0], er.shape[0]), min(p.shape[1], er.shape[1]); v = p[:h, :w][er[:h, :w]]
    res[dirn] = (float((v >= 0.5).mean()), float((v >= 0.75).mean()))
print("STATS", d.split("/")[-1], "valid", int(er.sum()), "fwd >=0.5 %.4f >=0.75 %.4f | rev >=0.5 %.4f >=0.75 %.4f" % (res["fwd"] + res["rev"]))
PY
done
log "CAND DONE"
