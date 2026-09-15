#!/usr/bin/env bash
# planted-window control: 4 cm2 of the w043 render spliced into PHerc0813/z6496_w040 (largest 9.362 um canvas so the window is a minority of the valid area), then the identical recipe
cd /workspace/atlas/planted2; W=/workspace/atlas; PY=$W/villa/vesuvius/.venv/bin/python; CK=$W/checkpoints
T=$(ls -d $W/renders/PHerc0813/z4704_w100/surface-volumes/*.zarr | head -1)
echo "START $(date -u +%FT%TZ) target=$T" >> progress.log
$PY $W/plant_control.py --control-zarr $W/control/w043.zarr --control-maps $W/control --target-zarr $T --out . > plant.out 2>&1 || { echo "PLANT FAILED" >> progress.log; exit 1; }
mkdir -p ink-detection
$PY $W/prep_mesh.py spliced.zarr padded.zarr ink-detection/valid_mask.tif > prep.out 2>&1 || { echo "PREP FAILED" >> progress.log; exit 1; }
for ck in $CK/ink_9um/hybrid_3d2d-seed43/step-060000.pth $CK/ink_9um/hybrid_3d2d-seed42/step-020000.pth $CK/soup42_early3.pth; do
  tag=$(basename $ck .pth); t0=$(date +%s)
  $PY -m vesuvius.ink_detection.inference.infer padded.zarr $ck ink-detection/spliced-ink9um-$tag.tif --mask-path ink-detection/valid_mask.tif --overlap 0.5 --blend-mode hann --direction both --batch-size 16 --no-compile > infer_$tag.out 2>&1
  echo "DONE $tag rc=$? secs=$(( $(date +%s) - t0 ))" >> progress.log
done
rm -rf padded.zarr
$PY $W/plant_eval.py . > plant_eval.out 2>&1; echo "EVAL rc=$?" >> progress.log
echo "ALL DONE $(date -u +%FT%TZ)" >> progress.log
