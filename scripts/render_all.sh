#!/usr/bin/env bash
# render_all.sh: render every mesh in queue.txt (scroll mesh voxel volid volurl keV) into the team's segment layout
#   renders/<scroll>/<mesh>/surface-volumes/<um>um-1.2m-<keV>keV-volume-<volid>.zarr  + render.json sidecar.
# Groups by (scroll, z-window) so the shared remote chunk cache is reused across wraps and cleared between slabs.
# usage: CONC=6 setsid nohup bash render_all.sh > /workspace/atlas/log/render_all.out 2>&1 &
set -u
export APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=/workspace/vc3d_cfg
export W=/workspace/atlas R=/workspace/atlas/renders P=/workspace/atlas/render/progress.log APP=/workspace/atlas/tools/VC3D.AppImage
export PY=/workspace/atlas/villa/vesuvius/.venv/bin/python
Q=$W/render/queue.txt
export APPSHA=$(sha256sum $APP | cut -c1-64) VILLA=$(git -C $W/villa rev-parse HEAD) MESHES=$(git -C $W/meshes-repo rev-parse HEAD)
export CONC=${CONC:-6} TIMEOUT_MIN=${TIMEOUT_MIN:-20} ATTEMPTS=${ATTEMPTS:-3} COMP=${COMP:-zstd}
mkdir -p $R $W/render $W/tools/stub.zarr /workspace/remote_cache
log(){ echo "$(date -u +%FT%TZ) $*" >> $P; }; export -f log

render_one(){ # scroll mesh voxel volid volurl keV [outdir-override]
  local s=$1 m=$2 vs=$3 vid=$4 url=$5 kev=$6 comp=${7:-$COMP}
  local d=$R/$s/$m; [ -n "${8:-}" ] && d=$8
  local out=$d/surface-volumes/${vs}um-1.2m-${kev}keV-volume-${vid}.zarr side=$d/render.json
  [ -f $side ] && grep -q '"rc": 0' $side && { log "SKIP $s/$m"; return 0; }
  mkdir -p $d/surface-volumes
  local t0=$(date +%s) rc=1 att=0
  while [ $att -lt $ATTEMPTS ] && [ $rc -ne 0 ]; do
    att=$((att+1)); rm -rf $out
    $APP vc_render_tifxyz --volume $W/tools/stub.zarr --remote-url "$url" --segmentation $W/meshes/$s/$m --scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 8 --voxel-size $vs --voxel-unit micrometer --flip-normals --zarr-compressor $comp --timeout $TIMEOUT_MIN --zarr-output $out > $d/render.out 2>&1; rc=$?
    [ $rc -ne 0 ] && log "RETRY $s/$m att=$att rc=$rc"
  done
  local t1=$(date +%s) chunks=$(find $out/0 -type f 2>/dev/null | wc -l) bytes=$(du -sb $out 2>/dev/null | cut -f1)
  $PY - <<PY
import json
json.dump({"scroll":"$s","mesh":"$m","rc":$rc,"attempts":$att,"wall_s":$((t1-t0)),"level0_chunks":$chunks,"bytes":${bytes:-0},
 "normals_flipped":True,"compressor":"$comp","voxel_size_um":$vs,"volume_id":"$vid","volume_url":"$url","num_slices":31,"slice_step":1,
 "appimage":"VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage","appimage_sha256":"$APPSHA","villa_commit":"$VILLA","meshes_commit":"$MESHES",
 "command":"vc_render_tifxyz --volume stub.zarr --remote-url $url --segmentation meshes/$s/$m --scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 8 --voxel-size $vs --voxel-unit micrometer --flip-normals --zarr-compressor $comp --timeout $TIMEOUT_MIN --zarr-output $out",
 "output":"$out","finished_utc":"$(date -u +%FT%TZ)","host":"$(hostname)"}, open("$side","w"), indent=1)
PY
  log "DONE $s/$m rc=$rc att=$att secs=$((t1-t0)) chunks=$chunks bytes=${bytes:-0}"
}
export -f render_one

log "START queue=$(wc -l < $Q) conc=$CONC comp=$COMP appimage=$APPSHA villa=$VILLA meshes=$MESHES"

# compressor check on the first mesh: 'none' (the verified reproduction setting) versus $COMP must be byte-identical arrays
read -r s m vs vid url kev < $Q
if [ ! -f $W/render/compressor_check.json ]; then
  render_one $s $m $vs $vid $url $kev none $W/render/check_none
  render_one $s $m $vs $vid $url $kev
  $PY - <<PY
import json, zarr, numpy as np, glob
a=zarr.open(glob.glob("$W/render/check_none/surface-volumes/*.zarr")[0], mode="r")["0"][:]
b=zarr.open(glob.glob("$R/$s/$m/surface-volumes/*.zarr")[0], mode="r")["0"][:]
eq=bool(np.array_equal(a,b)); r={"mesh":"$s/$m","shape":list(a.shape),"none_vs_$COMP":"identical" if eq else "DIFFERENT","nonzero_frac":float((a!=0).mean())}
json.dump(r, open("$W/render/compressor_check.json","w"), indent=1); print(r)
raise SystemExit(0 if eq else 1)
PY
  [ $? -ne 0 ] && { log "ABORT compressor check failed"; exit 1; }
  rm -rf $W/render/check_none; log "compressor check ok"
fi

# main loop, grouped by scroll + z-window (field 2 is zNNNN_wNNN)
prev=""
while read -r s m vs vid url kev; do
  g="$s/${m%%_*}"
  if [ "$g" != "$prev" ]; then
    if [ -n "$prev" ]; then wait; use=$(df --output=pcent / | tail -1 | tr -dc 0-9); log "GROUP DONE $prev disk=${use}% cache=$(du -sh /workspace/remote_cache | cut -f1)"; find /workspace/remote_cache -mindepth 1 -delete; fi
    prev=$g; log "GROUP START $g"
  fi
  while [ $(jobs -rp | wc -l) -ge $CONC ]; do sleep 5; done
  render_one $s $m $vs $vid $url $kev &
done < $Q
wait
log "ALL DONE ok=$(grep -c 'rc=0' $P) fail=$(grep 'DONE' $P | grep -vc 'rc=0') size=$(du -sh $R | cut -f1)"
find /workspace/remote_cache -mindepth 1 -delete
[ "${STOP_AT_END:-0}" = "1" ] && runpodctl stop pod ${RUNPOD_POD_ID:-qeg3surfkcuqin}
