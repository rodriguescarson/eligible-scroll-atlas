#!/usr/bin/env bash
# hecate_one.sh <scroll> <mesh> <volume_url> <voxel_um>: Hecate 9.6 um both directions on one held mesh (private)
set -u
S=$1; M=$2; URL=$3; VS=$4
W=/workspace/atlas; D=$W/h96/cand/${S}_$M; L=$W/h96/cand/progress.log; mkdir -p $D $W/tools/stub.zarr
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=/workspace/vc3d_cfg TMPDIR=$W/tmp
PY=$W/villa/vesuvius/.venv/bin/python; HEC=$W/hecate
sc=$(python3 -c "print(f'{$VS/9.6:.7f}')"); st=$(python3 -c "print(f'{9.6/$VS:.7f}')"); t0=$(date +%s)
$W/tools/VC3D.AppImage vc_render_tifxyz --volume $W/tools/stub.zarr --remote-url $URL --segmentation $W/meshes/$S/$M --scale $sc --group-idx 0 --num-slices 31 --slice-step $st --cache-gb 8 --voxel-size $VS --voxel-unit micrometer --flip-normals --zarr-compressor zstd --timeout 30 --zarr-output $D/r96.zarr > $D/render.out 2>&1
log "RENDER $S/$M rc=$? secs=$(( $(date +%s) - t0 ))"
for dir in fwd rev; do
  F=""; [ $dir = rev ] && F="--reverse"; t0=$(date +%s)
  $PY $HEC/hecate.py --checkpoint $HEC/hecate_9.6um.pth --input $D/r96.zarr --spacing-um 9.6 --output $D/hecate_$dir.png --device cuda --precision bf16 --batch-size 64 $F > $D/hecate_$dir.log 2>&1
  log "HECATE $S/$M $dir rc=$? secs=$(( $(date +%s) - t0 ))"
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
log "ONE DONE $S/$M"
