#!/usr/bin/env bash
# hecate_all.sh: Hecate 9.6 um on every mesh in queue.txt (scroll mesh voxel volid url keV).
# Render loop (CPU/network): direct 9.6 um render per mesh, grouped by scroll + z window so the remote chunk cache is reused,
# 6 concurrent, --flip-normals, --scale voxel/9.6, --slice-step 9.6/voxel, 31 slices; writes .ready when a render finishes.
# Inference loop (GPU): 2 concurrent hecate.py processes consume .ready renders, forward and --reverse, bf16 batch 64;
# per-mesh stats over the valid mask (non-zero render, eroded 64 px); the render is deleted after both maps exist.
# Maps and stats go to the PRIVATE repo per scroll (held until submission). When every mesh has both maps and the private
# repo holds them, the pod removes itself.
set -u
W=/workspace/atlas; H96=$W/h96; L=$H96/progress.log; POD=${POD:?set POD to this pod id}
MAPS=$H96/hold/h96/maps; mkdir -p $H96/renders $MAPS $W/tmp $W/tools/stub.zarr
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=/workspace/vc3d_cfg TMPDIR=$W/tmp
PY=$W/villa/vesuvius/.venv/bin/python; APP=$W/tools/VC3D.AppImage; HEC=$W/hecate; Q=$W/render/queue.txt
[ -f $HEC/hecate_9.6um.pth ] || HF_TOKEN=$(cat $W/.hf_token) uvx --from huggingface_hub hf download scrollprize/hecate --local-dir $HEC > $H96/hecate_dl.out 2>&1
log "START queue=$(wc -l < $Q) appimage=$(sha256sum $APP | cut -c1-16) hecate_pth=$(sha256sum $HEC/hecate_9.6um.pth | cut -c1-16) hecate_py=$(sha256sum $HEC/hecate.py | cut -c1-16)"

render_one(){ # scroll mesh voxel url
  local s=$1 m=$2 vs=$3 url=$4 d=$H96/renders/$1/$2
  [ -f $d/.ready ] || [ -f $MAPS/$s/${m}_rev.png ] && return 0
  mkdir -p $d; local sc st t0=$(date +%s) rc=1 att=0
  sc=$(python3 -c "print(f'{$vs/9.6:.7f}')"); st=$(python3 -c "print(f'{9.6/$vs:.7f}')")
  while [ $att -lt 3 ] && [ $rc -ne 0 ]; do
    att=$((att+1)); rm -rf $d/r96.zarr
    $APP vc_render_tifxyz --volume $W/tools/stub.zarr --remote-url "$url" --segmentation $W/meshes/$s/$m --scale $sc --group-idx 0 --num-slices 31 --slice-step $st --cache-gb 8 --voxel-size $vs --voxel-unit micrometer --flip-normals --zarr-compressor zstd --timeout 30 --zarr-output $d/r96.zarr > $d/render.out 2>&1; rc=$?
  done
  if [ $rc -eq 0 ]; then touch $d/.ready; log "RENDER $s/$m rc=0 att=$att secs=$(( $(date +%s) - t0 ))"; else log "RENDERFAIL $s/$m rc=$rc att=$att"; fi
}
export -f render_one log; export W H96 L APP

render_loop(){
  prev=""
  while read -r s m vs vid url kev; do
    g="$s/${m%%_*}"
    if [ "$g" != "$prev" ]; then [ -n "$prev" ] && { wait; find /workspace/remote_cache -mindepth 1 -delete 2>/dev/null; }; prev=$g; fi
    # back-pressure: keep at most 30 unconsumed renders on disk
    while [ $(find $H96/renders -name .ready | wc -l) -ge 30 ]; do sleep 20; done
    while [ $(jobs -rp | wc -l) -ge 6 ]; do sleep 5; done
    render_one $s $m $vs $url &
  done < $Q
  wait; touch $H96/RENDERS_DONE; log "RENDERS DONE"
}

infer_one(){ # ready-marker
  local r=$1 d; d=$(dirname $r); local m=$(basename $d) s=$(basename $(dirname $d)); mkdir -p $MAPS/$s
  mv $r $d/.running
  for dir in fwd rev; do
    F=""; [ $dir = rev ] && F="--reverse"; local t0=$(date +%s)
    $PY $HEC/hecate.py --checkpoint $HEC/hecate_9.6um.pth --input $d/r96.zarr --spacing-um 9.6 --output $MAPS/$s/${m}_$dir.png --device cuda --precision bf16 --batch-size 64 $F > $d/hecate_$dir.log 2>&1
    log "HECATE $s/$m $dir rc=$? secs=$(( $(date +%s) - t0 )) png=$([ -f $MAPS/$s/${m}_$dir.png ] && echo yes || echo no)"
  done
  $PY - $d/r96.zarr $MAPS/$s/$m >> $H96/stats.jsonl 2>> $H96/stats.err <<'PYEOF'
import json, sys, numpy as np, zarr
from PIL import Image
from scipy import ndimage
zp, base = sys.argv[1], sys.argv[2]
a = zarr.open(zp, mode="r")["0"]; valid = np.zeros(a.shape[1:], bool)
for y in range(0, a.shape[1], 1024): valid[y:y + 1024] = a[:, y:y + 1024, :].max(axis=0) > 0
er = ndimage.binary_erosion(valid, iterations=64, border_value=0)
out = {"mesh": base.split("/h96/maps/")[-1], "shape": list(a.shape), "valid_px": int(er.sum())}
for dirn in ("fwd", "rev"):
    try:
        p = np.asarray(Image.open(f"{base}_{dirn}.png")).astype(np.float32) / 255.0
        h, w = min(p.shape[0], er.shape[0]), min(p.shape[1], er.shape[1]); v = p[:h, :w][er[:h, :w]]
        out[dirn] = {"mean": float(v.mean()), "ge_0.5": float((v >= 0.5).mean()), "ge_0.75": float((v >= 0.75).mean()), "p99": float(np.percentile(v, 99))} if v.size else None
    except Exception as e:
        out[dirn] = {"error": str(e)[:120]}
print(json.dumps(out))
PYEOF
  if [ -f $MAPS/$s/${m}_fwd.png ] && [ -f $MAPS/$s/${m}_rev.png ]; then rm -rf $d/r96.zarr; touch $d/.done; else mv $d/.running $d/.failed; fi
}
export -f infer_one; export PY HEC MAPS

infer_loop(){
  # K3 gate: inference starts only after the w043 control shows text rows and forward beats reverse (GO), written by hand
  # from the control results. NOGO, or no decision within 2 h, cancels inference and removes the pod.
  local waited=0
  until [ -f $H96/GO ] || [ -f $H96/NOGO ] || [ $waited -ge 7200 ]; do sleep 30; waited=$((waited + 30)); done
  if [ ! -f $H96/GO ]; then
    log "NOGO or no decision after ${waited}s: Hecate inference cancelled"
    kill $RENDER_PID 2>/dev/null; sleep 5; pkill -f "vc_render_tifxyz --volume $W/tools/stub.zarr" 2>/dev/null
    log "removing pod"; runpodctl remove pod $POD || runpodctl stop pod $POD; exit 0
  fi
  log "GO received: starting Hecate inference"
  while true; do
    for r in $(find $H96/renders -name .ready | sort | head -4); do
      while [ $(jobs -rp | wc -l) -ge 2 ]; do sleep 5; done
      infer_one $r &
      sleep 2
    done
    if [ -f $H96/RENDERS_DONE ] && [ -z "$(find $H96/renders -name .ready)" ]; then wait; break; fi
    sleep 15
  done
  log "INFERENCE DONE maps=$(find $MAPS -name '*.png' | wc -l) failed=$(find $H96/renders -name .failed | wc -l)"
}

upload_verify(){
  $PY - <<PYEOF >> $H96/upload.out 2>&1
import glob, os
from huggingface_hub import HfApi
api = HfApi(token=open("$W/.hf_token").read().strip()); R = "rodriguescarson/eligible-scroll-atlas-held"
api.create_repo(R, repo_type="dataset", private=True, exist_ok=True)
for f in ("progress.log", "stats.jsonl", "stats.err"):
    if os.path.exists("$H96/" + f): api.upload_file(path_or_fileobj="$H96/" + f, path_in_repo="h96/" + f, repo_id=R, repo_type="dataset")
api.upload_large_folder(repo_id=R, folder_path="$H96/hold", repo_type="dataset", num_workers=4)
local = glob.glob("$MAPS/*/*.png"); remote = [f for f in api.list_repo_files(R, repo_type="dataset") if f.endswith(".png")]
print("local", len(local), "remote_png", len(remote))
open("$H96/upload_verified", "w").write("ok" if len(remote) >= len(local) else "short")
PYEOF
  log "UPLOAD $(tail -1 $H96/upload.out) verified=$(cat $H96/upload_verified 2>/dev/null)"
}

render_loop &
RENDER_PID=$!
infer_loop
upload_verify
if [ "$(cat $H96/upload_verified 2>/dev/null)" = ok ]; then log "ALL DONE, removing pod"; runpodctl remove pod $POD || runpodctl stop pod $POD
else log "ALL DONE but upload NOT verified; pod left running"; fi
