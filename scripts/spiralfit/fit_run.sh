#!/usr/bin/env bash
# fit_run.sh: one PHerc0826 window with the tracks config, export every winding, flatten and render every 10th winding.
set -u
W=/workspace; S=PHerc0826; V=20250821151701; F=$W/fit; L=$F/progress.log; DS=$W/ds/$S; VOX=9.362
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
read Z0 Z1 < $F/window.txt
export WANDB_MODE=disabled FIT_SPIRAL_OUT_DIR=$W/out/$S APPIMAGE_EXTRACT_AND_RUN=1
cd $W/villa/spiral-fitting && cp $F/export_all_windings.py .
export FIT_SPIRAL_CONFIG_OVERRIDES="{\"z_begin\": $Z0, \"z_end\": $Z1, \"optimizer_num_training_steps\": ${STEPS:-30000}, \"input_disable_patches\": true, \"input_use_tracks\": true, \"input_use_outer_shell\": false, \"loss_weight_shell_outer\": 0, \"loss_weight_shell_patch_radius\": 0, \"dense_spacing_mode\": \"grad_mag\", \"loss_weight_dense_spacing\": 0, \"shell_outer_winding_idx\": 90, \"model_gap_expander_num_windings\": 90, \"output_first_winding\": 0}"
log "FIT START window [$Z0,$Z1) steps ${STEPS:-30000}"
t0=$(date +%s)
uv run --no-sync python fit_spiral.py --dataset $DS --cache $W/spiral_cache > $F/fit_B.log 2>&1; rc=$?
log "FIT rc=$rc secs=$(( $(date +%s) - t0 )) | $(grep -E 'winding range|z-range|Traceback|Error' $F/fit_B.log | tail -3 | tr '\n' ' ' | cut -c1-300)"
RUN=$(ls -d $W/out/$S/*_slice-${Z0}-${Z1}_* 2>/dev/null | tail -1)
log "run dir ${RUN:-none}; fitted meshes $(ls $RUN/meshes/fitted 2>/dev/null | wc -l)"
[ -f "$RUN/checkpoint_fitted.ckpt" ] || { log "no checkpoint, stopping here"; exit 1; }
t0=$(date +%s)
uv run --no-sync python export_all_windings.py $RUN/checkpoint_fitted.ckpt $DS/umbilicus.json $RUN/meshes/all --voxel-size-um $VOX > $F/export.log 2>&1
log "EXPORT rc=$? windings=$(ls $RUN/meshes/all 2>/dev/null | wc -l) secs=$(( $(date +%s) - t0 )) | $(tail -1 $F/export.log | cut -c1-160)"
cd $W/villa/lasagna
for m in $(ls -d $RUN/meshes/all/w*/ 2>/dev/null | awk 'NR % 10 == 1'); do
  n=$(basename $m); printf '{"external_surfaces":[{"path":"%s"}],"voxel_size_um":%s}\n' "$(realpath $m)" $VOX > $F/in_$n.json; t0=$(date +%s)
  .venv/bin/python fit.py configs/flatten_fast_nofilter.json $F/in_$n.json --out-dir $RUN/flat/$n --device cuda > $F/flatten_$n.log 2>&1
  rc=$?; flat=$(ls -d $RUN/flat/$n/tifxyz/*.tifxyz 2>/dev/null | head -1)
  log "FLATTEN $n rc=$rc secs=$(( $(date +%s) - t0 )) out=${flat:-none} | $(grep -E 'Traceback|Error' $F/flatten_$n.log | tail -1 | cut -c1-120)"
  [ -n "$flat" ] || continue
  t0=$(date +%s); mkdir -p $W/tools/stub.zarr
  $W/tools/VC3D.AppImage vc_render_tifxyz --volume $W/tools/stub.zarr --remote-url https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/$S/volumes/$V-9.362um-1.2m-113keV-masked.zarr --segmentation $flat --scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 8 --voxel-size $VOX --voxel-unit micrometer --flip-normals --zarr-compressor zstd --timeout 30 --zarr-output $RUN/render/$n.zarr > $F/render_$n.log 2>&1
  rc=$?; log "RENDER $n rc=$rc secs=$(( $(date +%s) - t0 )) shape=$(python3 -c "import json;print(json.load(open('$RUN/render/$n.zarr/0/.zarray'))['shape'])" 2>&1 | cut -c1-60) area_cm2=$(python3 -c "
import tifffile, numpy as np, json
x=tifffile.imread('$flat/x.tif'); v=(x>0); m=json.load(open('$flat/meta.json')); s=m.get('scale',[0.05,0.05])[0]
print(round(v.sum()*(1/s)**2*($VOX*1e-4)**2, 2))" 2>&1 | tail -1)"
done
log "FIT_RUN DONE"
