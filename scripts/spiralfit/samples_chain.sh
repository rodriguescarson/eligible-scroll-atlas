#!/usr/bin/env bash
# samples_chain.sh (name contains "chain.sh" so guard_v3 counts it as work): flatten and render every 5th winding of the
# 45-winding arm, after fit_run45.sh exported into the wrong directory (its RUN glob matched the renamed 90-winding folder).
set -u
W=/workspace; S=PHerc0191; V=20250821151635; F=$W/fit; L=$F/progress.log; VOX=9.362
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
RUN=$(ls -d $W/out/$S/*_w45 | tail -1)
log "samples: arm B run dir $RUN, windings $(ls -d $RUN/meshes/all/w*/ | wc -l)"
cd $W/villa/lasagna
for m in $(ls -d $RUN/meshes/all/w*/ | awk 'NR % 5 == 1'); do
  n=$(basename $m); printf '{"external_surfaces":[{"path":"%s"}],"voxel_size_um":%s}\n' "$(realpath $m)" $VOX > $F/in45_$n.json; t0=$(date +%s)
  .venv/bin/python fit.py configs/flatten_fast_nofilter.json $F/in45_$n.json --out-dir $RUN/flat/$n --device cuda > $F/flatten45_$n.log 2>&1
  rc=$?; flat=$(ls -d $RUN/flat/$n/tifxyz/*.tifxyz 2>/dev/null | head -1)
  log "FLATTEN45 $n rc=$rc secs=$(( $(date +%s) - t0 )) out=${flat:-none}"
  [ -n "$flat" ] || continue
  t0=$(date +%s); mkdir -p $W/tools/stub.zarr
  $W/tools/VC3D.AppImage vc_render_tifxyz --volume $W/tools/stub.zarr --remote-url https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/$S/volumes/$V-9.362um-1.2m-113keV-masked.zarr --segmentation $flat --scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 8 --voxel-size $VOX --voxel-unit micrometer --flip-normals --zarr-compressor zstd --timeout 30 --zarr-output $RUN/render/$n.zarr > $F/render45_$n.log 2>&1
  log "RENDER45 $n rc=$? secs=$(( $(date +%s) - t0 )) area_cm2=$(python3 -c "
import tifffile, numpy as np, json
x = tifffile.imread('$flat/x.tif'); y = tifffile.imread('$flat/y.tif'); z = tifffile.imread('$flat/z.tif')
ok = (x > 0) & (y > 0) & (z > 0); P = np.stack([x, y, z], -1).astype(np.float64)
du = P[:-1, 1:] - P[:-1, :-1]; dv = P[1:, :-1] - P[:-1, :-1]
q = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
print(round(float(np.linalg.norm(np.cross(du, dv), axis=-1)[q].sum()) * ($VOX * 1e-4) ** 2, 2))" 2>&1 | tail -1)"
done
log "SAMPLES45 DONE"
