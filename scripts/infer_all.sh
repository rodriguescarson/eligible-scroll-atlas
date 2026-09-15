#!/usr/bin/env bash
# infer_all.sh: consume renders in queue order as they finish; per mesh run the pre-registered inference recipe
# (3 checkpoint files x both directions, overlap 0.5, hann, masked, padded to 64) and write ink-detection/ outputs + infer.json.
# usage: setsid nohup bash infer_all.sh > /workspace/atlas/log/infer_all.out 2>&1 &
set -u
W=/workspace/atlas; R=$W/renders; Q=$W/render/queue.txt; P=$W/infer/progress.log; T=$W/tmp
PY=$W/villa/vesuvius/.venv/bin/python; CK=$W/checkpoints
BATCH=${BATCH:-16}; COMPILE=${COMPILE:---no-compile}
VILLA=$(git -C $W/villa rev-parse HEAD)
mkdir -p $W/infer $T
log(){ echo "$(date -u +%FT%TZ) $*" >> $P; }
declare -A TAG=( [$CK/ink_9um/hybrid_3d2d-seed43/step-060000.pth]=s43_060k [$CK/ink_9um/hybrid_3d2d-seed42/step-020000.pth]=s42_020k [$CK/soup42_early3.pth]=soup42_early3 )
CKS="$CK/ink_9um/hybrid_3d2d-seed43/step-060000.pth $CK/ink_9um/hybrid_3d2d-seed42/step-020000.pth $CK/soup42_early3.pth"
log "START batch=$BATCH compile=$COMPILE villa=$VILLA"
for ck in $CKS; do log "ckpt ${TAG[$ck]} sha256=$(sha256sum $ck | cut -c1-64)"; done

while read -r s m vs vid url kev; do
  d=$R/$s/$m; side=$d/render.json; out=$d/ink-detection; mkdir -p $out
  [ -f $out/infer.json ] && { log "SKIP $s/$m"; continue; }
  # wait for the render (pipeline behind render_all.sh); give up on a mesh whose render failed
  while [ ! -f $side ]; do grep -q "ALL DONE" $W/render/progress.log && break; sleep 30; done
  [ -f $side ] || { log "NORENDER $s/$m"; continue; }
  grep -q '"rc": 0' $side || { log "RENDERFAIL $s/$m"; continue; }
  zr=$(ls -d $d/surface-volumes/*.zarr | head -1); pad=$T/${s}_${m}.zarr; mask=$out/valid_mask.tif
  t0=$(date +%s)
  prep=$($PY $W/prep_mesh.py $zr $pad $mask 2>$out/prep.err) || { log "PREPFAIL $s/$m $(tail -1 $out/prep.err)"; rm -rf $pad; continue; }
  t1=$(date +%s); runs=""
  for ck in $CKS; do
    tag=${TAG[$ck]}; o=$out/${s}-${m}-${vid}-ink9um-${tag}.tif; ta=$(date +%s)
    $PY -m vesuvius.ink_detection.inference.infer $pad $ck $o --mask-path $mask --overlap 0.5 --blend-mode hann --direction both --batch-size $BATCH $COMPILE > $out/infer_${tag}.out 2>&1; rc=$?
    runs="$runs {\"tag\":\"$tag\",\"rc\":$rc,\"secs\":$(( $(date +%s) - ta )),\"forward\":\"$(basename $o)\",\"reverse\":\"$(basename ${o%.tif})_reverse.tif\"},"
    [ $rc -ne 0 ] && log "INFERFAIL $s/$m $tag rc=$rc $(tr '\r' '\n' < $out/infer_${tag}.out | grep -i "error\|Traceback" | tail -1)"
  done
  rm -rf $pad
  $PY - <<PY
import json, glob, os, numpy as np, tifffile
from PIL import Image
out="$out"; prev=[]
for f in sorted(glob.glob(out+"/*.tif")):
    if f.endswith("valid_mask.tif"): continue
    m=tifffile.imread(f); info={"file":os.path.basename(f),"dtype":str(m.dtype),"shape":list(m.shape)}
    x=m.astype(np.float32); x=x/255.0 if m.dtype==np.uint8 else x
    H,Wd=(x.shape[0]//8)*8,(x.shape[1]//8)*8
    ds=x[:H,:Wd].reshape(H//8,8,Wd//8,8).mean((1,3))
    Image.fromarray((np.clip((ds-0.25)/0.5,0,1)*255).astype(np.uint8)).save(f[:-4]+"-ds8.jpg", quality=85)
    info.update({"mean":float(x.mean()),"p99":float(np.percentile(x,99)),"frac_ge_0.75":float((x>=0.75).mean())}); prev.append(info)
json.dump({"scroll":"$s","mesh":"$m","volume_id":"$vid","prep":$prep,"prep_s":$((t1-t0)),"runs":[$runs][:-1] if False else [$(echo "$runs" | sed 's/,$//')],
  "recipe":"overlap 0.5, blend hann, direction both, batch $BATCH, $COMPILE, mask valid&erode64, padded to 64",
  "villa_commit":"$VILLA","maps":prev,"finished_utc":"$(date -u +%FT%TZ)","wall_s":$(( $(date +%s) - t0 ))}, open(out+"/infer.json","w"), indent=1)
PY
  log "DONE $s/$m secs=$(( $(date +%s) - t0 )) prep=$((t1-t0)) maps=$(ls $out/*.tif | grep -vc valid_mask)"
done < $Q
log "ALL DONE done=$(grep -c '^.*DONE PHerc' $P) fails=$(grep -c 'FAIL' $P)"
[ -f $W/finish.sh ] && bash $W/finish.sh
