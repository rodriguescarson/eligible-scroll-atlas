#!/usr/bin/env bash
# Positive control: the team's published native PHerc0139 w043 surface volume, inferred with the pre-registered recipe.
cd /workspace/atlas/control
U=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0139/segments/20260112000000-w043_2026011217/surface-volumes/9.362um-1.2m-113keV-volume-20250728140407.zarr
PY=/workspace/atlas/villa/vesuvius/.venv/bin/python
CK=/workspace/atlas/checkpoints
echo "START w043 $(date -u +%FT%TZ)" >> progress.log
if [ ! -f w043.zarr/.done ]; then
  t0=$(date +%s)
  $PY - <<PY
import zarr, numpy as np, time
t=time.time()
a=zarr.open(("$U"), mode="r")["0"]
print("src", a.shape, a.dtype, a.chunks, flush=True)
g=zarr.open_group("w043.zarr", mode="w", zarr_format=2)
d=g.create_array("0", shape=a.shape, chunks=a.chunks, dtype=a.dtype, compressors=None)
H=a.shape[1]; step=a.chunks[1]*8
for y in range(0,H,step):
    d[:, y:y+step, :] = a[:, y:y+step, :]
print("copied %.1f GB in %.0fs" % (np.prod(a.shape)/1e9, time.time()-t), flush=True)
PY
  [ $? -eq 0 ] && touch w043.zarr/.done
  echo "COPY rc=$? secs=$(( $(date +%s) - t0 ))" >> progress.log
fi
for ck in $CK/ink_9um/hybrid_3d2d-seed43/step-060000.pth $CK/ink_9um/hybrid_3d2d-seed42/step-020000.pth $CK/soup42_early3.pth; do
  tag=$(basename $(dirname $ck))_$(basename $ck .pth); [ "$tag" = "checkpoints_soup42_early3" ] && tag=soup42_early3
  [ -f w043_${tag}.tif ] && continue
  t0=$(date +%s)
  $PY -m vesuvius.ink_detection.inference.infer w043.zarr $ck w043_${tag}.tif --overlap 0.5 --blend-mode hann --direction both --batch-size 16 --no-compile > infer_${tag}.out 2>&1; rc=$?
  echo "DONE $tag rc=$rc secs=$(( $(date +%s) - t0 )) $(date -u +%FT%TZ)" >> progress.log
done
# ds8 previews: plain 8x block mean of the raw map (the team's convention), rescaled (p-0.25)/0.5 for display only
$PY - <<PY
import glob, numpy as np, tifffile
from PIL import Image
for f in sorted(glob.glob("w043_*.tif")):
    m=tifffile.imread(f).astype(np.float32)
    if m.max()>1.5: m=m/255.0
    H,W=(m.shape[0]//8)*8,(m.shape[1]//8)*8
    ds=m[:H,:W].reshape(H//8,8,W//8,8).mean((1,3))
    disp=np.clip((ds-0.25)/0.5,0,1)
    Image.fromarray((disp*255).astype(np.uint8)).save(f.replace(".tif","-ds8.jpg"), quality=85)
    print(f, m.shape, "mean %.3f p99 %.3f frac>=0.75 %.4f" % (m.mean(), np.percentile(m,99), (m>=0.75).mean()))
PY
echo "ALL DONE $(date -u +%FT%TZ)" >> progress.log
