#!/usr/bin/env bash
# job.sh: (1) Hecate 3D depth profiles on known ink, pre-registered as prereg-hecate3d-v1/v2;
#         (2) villa#1830 proof, PR branch vs its base commit on a short PHerc0826 fit. Ends by removing the pod.
set -u
W=/workspace; J=$W/job; O=$J/out; L=$J/progress.log; mkdir -p $O $J/tmp $W/vc3d_cfg
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
export HF_TOKEN=$(cat $J/.hf_token) TMPDIR=$J/tmp OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 \
       WANDB_MODE=disabled APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=$W/vc3d_cfg
PR_HEAD=de41bfba9f94a2a9cdbc0e2470d26058a4c4452a; BASE=b1ef996e357de0b2f24fb30198c6d9c32611d4fb
PIN=d9193657506a795e1048adeb2950454809fabf78cb5f9e8bcc076f6afd1fdb4a; PSC=0c966f8f11f92cffb09dbc6320a706161405ad0b
S=PHerc0826; V=20250821151701; Z0=6528; Z1=7328; DS=$W/ds/$S; STEPS=${STEPS:-300}
B=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com
log "JOB START steps=$STEPS gpu=$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | head -1)"

# self-removal wrapper: ssh-launched jobs lack the API key, PID 1 has it
REAL=$(command -v runpodctl); [ "$REAL" = /usr/local/bin/runpodctl ] && REAL=/usr/bin/runpodctl
cat > /usr/local/bin/runpodctl <<SH
#!/usr/bin/env bash
export RUNPOD_API_KEY=\$(tr '\\0' '\\n' < /proc/1/environ | sed -n 's/^RUNPOD_API_KEY=//p')
exec $REAL "\$@"
SH
chmod +x /usr/local/bin/runpodctl; log "wrapper -> $REAL"

apt-get update -qq > $J/apt.out 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential cmake ninja-build libfuse2 >> $J/apt.out 2>&1
log "apt rc=$?"; python3 -m pip install -q awscli >> $J/apt.out 2>&1; log "awscli rc=$?"

# ---------- villa setup + PHerc0826 inputs, in the background while the GPU does Hecate ----------
villa_setup() {
  git clone -q --depth 1 -b feat/spiral-scroll-winding-count https://github.com/rodriguescarson/villa.git $W/villa_pr
  git -C $W/villa_pr rev-parse HEAD > $O/pr_head.txt
  mkdir -p $W/villa_base && cd $W/villa_base && git init -q && git remote add origin https://github.com/ScrollPrize/villa.git \
    && git fetch -q --depth 1 origin $BASE && git checkout -q FETCH_HEAD && git rev-parse HEAD > $O/base_head.txt
  log "villa pr=$(cat $O/pr_head.txt) (want $PR_HEAD) base=$(cat $O/base_head.txt)"
  cd $W/villa_pr/spiral-fitting && uv sync > $J/uv_spiral.out 2>&1; log "uv sync rc=$?"
  .venv/bin/python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available())" >> $L 2>&1
  mkdir -p $DS/tracks $DS/lasagna_inputs
  UMB=$(curl -s "$B/?prefix=$S/representations/umbilicus/" | grep -o "<Key>[^<]*</Key>" | sed 's/<[^>]*>//g' | head -1)
  curl -sfL -o $DS/umbilicus.json "$B/$UMB"; log "umbilicus $UMB rc=$?"
  LAS=s3://vesuvius-challenge-open-data/$S/representations/predictions/lasagna/$V-lasagna-20260419180421
  aws s3 ls --no-sign-request $LAS/ > $J/lasagna_ls.txt 2>&1
  c0=$(( Z0 / 4 / 32 - 1 )); c1=$(( (Z1 + 3) / 4 / 32 + 1 ))
  for n in nx ny grad_mag; do
    src=$(grep -o "[^ ]*_$n\.ome\.zarr/" $J/lasagna_ls.txt | head -1); [ -z "$src" ] && src="${S}_$n.ome.zarr/"
    inc=(--exclude '*' --include '.zattrs' --include '.zgroup' --include '2/.zarray' --include '2/.zattrs')
    for c in $(seq $c0 $c1); do inc+=(--include "2/$c/*"); done
    aws s3 sync --no-sign-request --only-show-errors "$LAS/$src" "$DS/lasagna_inputs/las_008_$n.ome.zarr/" "${inc[@]}" > $J/sync_$n.out 2>&1
    log "lasagna $n rc=$? files=$(find $DS/lasagna_inputs/las_008_$n.ome.zarr -type f | wc -l)"
  done
  T=https://dl.ash2txt.org/datasets/spiral_datasets/$S/$V/tracks; DBM=${S}_${V}_surface_m7_L0_th0.2.dbm
  for f in ${S}_${V}_surface_m7_L0_th0.2.extract.json $DBM $DBM.crossings.npz; do
    curl -sfL -o $DS/tracks/$f "$T/$f"; log "tracks $f rc=$? bytes=$(stat -c %s $DS/tracks/$f 2>/dev/null)"
  done
  # the crossings sidecar is keyed on the DBM's mtime; a fresh download changes it
  .venv/bin/python - $DS/tracks/$DBM >> $L 2>&1 <<'PY'
import json, os, sys, numpy as np
sys.path.insert(0, os.getcwd()); import tracks
dbm = sys.argv[1]; npz = dbm + ".crossings.npz"
if not os.path.exists(npz): print("crossings: no sidecar, the fit will build it"); raise SystemExit
meta = json.loads(str(np.load(npz, allow_pickle=False)["metadata"].item()))
for name, size, mtime in meta["db_signature"]:
    p = os.path.join(os.path.dirname(dbm), name); st = os.stat(p)
    if st.st_size == size: os.utime(p, ns=(st.st_atime_ns, mtime))
ok = [list(x) for x in tracks._tracks_db_signature(dbm)] == meta["db_signature"]
print(f"crossings signature match={ok} version={meta.get('version')} expected={tracks.TRACK_CROSSING_CACHE_VERSION}")
PY
  common='"schema_version": 1, "name": "PHerc0826", "voxel_size_um": 9.362, "spiral_outward_sense": "CW", "normal_zarr_group": "2", "lasagna_scale": 4, "paths": {"tracks_dbm": "tracks/'$DBM'"}'
  echo "{$common, \"num_windings\": 90}" > $DS/spec_pr.json; echo "{$common}" > $DS/spec_base.json
  cp $DS/spec_pr.json $DS/spec_base.json $O/
  log "VILLA SETUP FINISHED"
}
villa_setup &
VPID=$!

# ---------- (1) Hecate 3D on known ink ----------
HEC=$W/hecate; HPY=$W/hecenv/bin/python
uv venv -q $W/hecenv --python 3.12 && uv pip install -q --python $HPY torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128 >> $J/hec_env.out 2>&1 \
  && uv pip install -q --python $HPY numpy 'zarr<3' numcodecs tifffile pillow scipy huggingface_hub >> $J/hec_env.out 2>&1
log "hecate env rc=$? $($HPY -c 'import torch;print(torch.__version__,torch.cuda.is_available())' 2>&1)"
$HPY - <<'PY' >> $L 2>&1
import os
from huggingface_hub import hf_hub_download
T = os.environ["HF_TOKEN"]; W = "/workspace"
for f in ("hecate.py", "hecate_9.6um.pth"):
    hf_hub_download("scrollprize/hecate", f, local_dir=f"{W}/hecate")
for w in ("w042", "w043"):
    hf_hub_download("rodriguescarson/eligible-scroll-atlas-held", f"c96b/{w}/r96_31.zarr.tar", repo_type="dataset", token=T, local_dir=f"{W}/ctrl")
hf_hub_download("rodriguescarson/eligible-scroll-atlas-held", "tools/VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage", repo_type="dataset", token=T, local_dir=f"{W}/ctrl")
print("downloads ok")
PY
log "hecate.py sha256=$(sha256sum $HEC/hecate.py | cut -c1-16) (want c232c18a1a86cfb9)"
for w in w042 w043; do
  D=$W/h3d/$w; mkdir -p $D; tar -xf $W/ctrl/c96b/$w/r96_31.zarr.tar -C $D
  R=$(find $D -maxdepth 4 -type d -name "*.zarr" | head -1); log "control $w render $R"; t0=$(date +%s)
  timeout 50m $HPY $HEC/hecate.py --checkpoint $HEC/hecate_9.6um.pth --input $R --spacing-um 9.6 \
    --output-3d $D/ink3d.zarr --output $D/ink2d.png --device cuda --precision bf16 --batch-size 32 > $O/hecate_$w.log 2>&1
  log "HECATE $w rc=$? secs=$(( $(date +%s) - t0 ))"
  $HPY $J/hecate_profile.py $w $R $D/ink2d.png $D/ink3d.zarr $O/profile_$w.json >> $L 2>&1; log "PROFILE $w rc=$?"
done
# exploratory: TAUIL's documented false positive, re-rendered with the September recipe
APP=$W/ctrl/tools/VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage; chmod +x $APP
if [ "$(sha256sum $APP | cut -c1-64)" = "$PIN" ]; then
  M=$W/fp_mesh/z12496_w060; mkdir -p $M $W/stub.zarr
  for f in meta.json x.tif y.tif z.tif; do curl -sfL -o $M/$f "https://raw.githubusercontent.com/pscamillo/vesuvius-eligible-meshes/$PSC/meshes/PHerc0813/z12496_w060/$f"; done
  D=$W/h3d/fp_z12496_w060; mkdir -p $D; t0=$(date +%s)
  timeout 20m $APP vc_render_tifxyz --volume $W/stub.zarr --remote-url $B/PHerc0813/volumes/20250821151723-9.362um-1.2m-113keV-masked.zarr \
    --segmentation $M --scale 0.9752083 --group-idx 0 --num-slices 31 --slice-step 1.0254218 --cache-gb 8 --voxel-size 9.362 \
    --voxel-unit micrometer --flip-normals --zarr-compressor zstd --timeout 15 --zarr-output $D/r96.zarr > $O/render_fp.log 2>&1
  log "RENDER fp rc=$? secs=$(( $(date +%s) - t0 ))"
  timeout 30m $HPY $HEC/hecate.py --checkpoint $HEC/hecate_9.6um.pth --input $D/r96.zarr --spacing-um 9.6 \
    --output-3d $D/ink3d.zarr --output $D/ink2d.png --device cuda --precision bf16 --batch-size 32 > $O/hecate_fp.log 2>&1
  log "HECATE fp rc=$?"
  $HPY $J/hecate_profile.py fp_z12496_w060 $D/r96.zarr $D/ink2d.png $D/ink3d.zarr $O/profile_fp_z12496_w060.json >> $L 2>&1; log "PROFILE fp rc=$?"
else log "AppImage sha mismatch, false-positive render skipped"; fi
log "HECATE PART FINISHED"

# ---------- (2) villa#1830 proof ----------
wait $VPID; log "villa setup joined"
OVR='{"z_begin": '$Z0', "z_end": '$Z1', "optimizer_num_training_steps": '$STEPS', "input_disable_patches": true, "input_use_tracks": true, "input_use_outer_shell": false, "input_use_fibers": false, "input_use_pcl_absolute": false, "input_use_pcl_drawn_control_points": false, "input_use_pcl_relative": false, "input_use_pcl_same_winding": false, "input_use_unverified_patches": false, "input_use_verified_patches": false, "input_use_winding_inference": false, "loss_weight_shell_outer": 0, "loss_weight_shell_patch_radius": 0, "dense_spacing_mode": "grad_mag", "loss_weight_dense_spacing": 0}'
echo "$OVR" > $O/overrides.json
VPY=$W/villa_pr/spiral-fitting/.venv/bin/python
for arm in pr base; do
  [ $arm = pr ] && SRC=$W/villa_pr || SRC=$W/villa_base
  cd $SRC/spiral-fitting; t0=$(date +%s)
  FIT_SPIRAL_OUT_DIR=$W/out_$arm FIT_SPIRAL_CONFIG_OVERRIDES="$OVR" timeout 45m $VPY fit_spiral.py \
    --dataset $DS --scroll-spec $DS/spec_$arm.json --cache $W/spiral_cache > $O/fit_$arm.log 2>&1
  log "FIT $arm rc=$? secs=$(( $(date +%s) - t0 ))"
  CK=$(ls $W/out_$arm/*/checkpoint_fitted.ckpt 2>/dev/null | tail -1)
  if [ -n "$CK" ]; then
    mkdir -p $W/export_$arm; timeout 25m $VPY $J/proof_export.py $CK $DS/umbilicus.json $W/export_$arm > $O/export_$arm.log 2>&1
    log "EXPORT $arm rc=$? $(grep -E 'PROOF checkpoint|reconstructing windings' $O/export_$arm.log | tr '\n' ' ')"
  else log "no checkpoint for $arm: $(grep -E 'Error|Traceback' $O/fit_$arm.log | tail -2 | tr '\n' ' ' | cut -c1-240)"; fi
done
grep -h -E "shell_outer_winding_idx|reconstructing windings|PROOF" $O/fit_*.log $O/export_*.log > $O/proof_lines.txt 2>/dev/null
cp $L $O/progress.log
log "Z JOB COMPLETE"; cp $L $O/progress.log
bash $J/finish.sh
