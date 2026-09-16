#!/usr/bin/env bash
# retry_failed.sh: rerun Hecate on meshes whose run hit CUDA OOM (two concurrent batch-64 processes on one A40; a large mesh
# takes ~33 GB). Waits for the main loop's INFERENCE DONE, then runs each failed mesh ALONE at batch 64 (same setting as the
# rest of the pass), falling back to batch 32 only if that still OOMs. The runpodctl wrapper holds removal until RETRY_DONE.
set -u
W=/workspace/atlas; H96=$W/h96; L=$H96/progress.log; MAPS=$H96/hold/h96/maps; PY=$W/villa/vesuvius/.venv/bin/python; HEC=$W/hecate
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
log "RETRY armed: waiting for the main inference loop to finish ($(find $H96/renders -name .failed | wc -l) failed so far)"
until grep -q "Z INFERENCE DONE maps=" $L; do sleep 30; done
while pgrep -f "hecate/hecate.py --checkpoint" > /dev/null; do sleep 15; done
for f in $(find $H96/renders -name .failed | sort); do
  d=$(dirname $f); m=$(basename $d); s=$(basename $(dirname $d)); mkdir -p $MAPS/$s
  [ -d $d/r96.zarr ] || { log "HECATE-RETRY $s/$m no render left, skipped"; continue; }
  for dir in fwd rev; do
    [ -f $MAPS/$s/${m}_$dir.png ] && continue
    F=""; [ $dir = rev ] && F="--reverse"
    for bs in 64 32; do
      t0=$(date +%s)
      $PY $HEC/hecate.py --checkpoint $HEC/hecate_9.6um.pth --input $d/r96.zarr --spacing-um 9.6 --output $MAPS/$s/${m}_$dir.png --device cuda --precision bf16 --batch-size $bs $F > $d/hecate_${dir}_retry$bs.log 2>&1
      rc=$?; log "HECATE-RETRY $s/$m $dir batch=$bs rc=$rc secs=$(( $(date +%s) - t0 )) png=$([ -f $MAPS/$s/${m}_$dir.png ] && echo yes || echo no)"
      [ -f $MAPS/$s/${m}_$dir.png ] && break
    done
  done
  $PY - $d/r96.zarr $MAPS/$s/$m >> $H96/stats.jsonl 2>> $H96/stats.err <<'PYEOF'
import json, sys, numpy as np, zarr
from PIL import Image
from scipy import ndimage
zp, base = sys.argv[1], sys.argv[2]
a = zarr.open(zp, mode="r")["0"]; valid = np.zeros(a.shape[1:], bool)
for y in range(0, a.shape[1], 1024): valid[y:y + 1024] = a[:, y:y + 1024, :].max(axis=0) > 0
er = ndimage.binary_erosion(valid, iterations=64, border_value=0)
out = {"mesh": base.split("/h96/maps/")[-1], "shape": list(a.shape), "valid_px": int(er.sum()), "retry": True}
for dirn in ("fwd", "rev"):
    try:
        p = np.asarray(Image.open(f"{base}_{dirn}.png")).astype(np.float32) / 255.0
        h, w = min(p.shape[0], er.shape[0]), min(p.shape[1], er.shape[1]); v = p[:h, :w][er[:h, :w]]
        out[dirn] = {"mean": float(v.mean()), "ge_0.5": float((v >= 0.5).mean()), "ge_0.75": float((v >= 0.75).mean()), "p99": float(np.percentile(v, 99))} if v.size else None
    except Exception as e:
        out[dirn] = {"error": str(e)[:120]}
print(json.dumps(out))
PYEOF
  if [ -f $MAPS/$s/${m}_fwd.png ] && [ -f $MAPS/$s/${m}_rev.png ]; then rm -f $f; rm -rf $d/r96.zarr; touch $d/.done; fi
done
log "RETRY DONE failed_left=$(find $H96/renders -name .failed | wc -l)"
touch $H96/RETRY_DONE
