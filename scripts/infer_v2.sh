#!/usr/bin/env bash
# infer_v2.sh: per scroll, folder-mode inference with the three checkpoint files running concurrently on one GPU
# (one model load per checkpoint per scroll instead of per mesh). Padded zero-copy views (padview.py); the eroded valid mask
# is applied at scoring (screens.py), block selection uses infer's own nonzero occupancy scan. Outputs are renamed into
# renders/<scroll>/<mesh>/ink-detection/ with the same names infer_all.sh used, plus valid_mask.tif, ds8 previews, infer.json.
# usage: setsid nohup bash infer_v2.sh > /workspace/atlas/log/infer_v2.out 2>&1 &
set -u
W=/workspace/atlas; R=$W/renders; Q=$W/render/queue.txt; P=$W/infer/progress.log; T=$W/tmp_v2
PY=$W/villa/vesuvius/.venv/bin/python; CK=$W/checkpoints
BATCH=${BATCH:-16}; WORKERS=${WORKERS:-2}
# the host reports 96 cores; OpenBLAS in every DataLoader worker tried 64 threads each and hit the container's thread limit
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
VILLA=$(git -C $W/villa rev-parse HEAD)
mkdir -p $W/infer $T
log(){ echo "$(date -u +%FT%TZ) $*" >> $P; }
log "START v2 folder-mode batch=$BATCH workers=$WORKERS villa=$VILLA"
for scroll in $(awk '{print $1}' $Q | uniq); do
  # wait until every render of this scroll is done (render_all.sh writes render.json per mesh)
  while true; do
    missing=0; while read -r s m vs vid url kev; do [ "$s" = "$scroll" ] || continue; [ -f $R/$s/$m/render.json ] || missing=$((missing+1)); done < $Q
    [ $missing -eq 0 ] && break; grep -q "ALL DONE" $W/render/progress.log && break; sleep 60
  done
  F=$T/$scroll; rm -rf $F; mkdir -p $F; n=0
  while read -r s m vs vid url kev; do
    [ "$s" = "$scroll" ] || continue
    [ -f $R/$s/$m/ink-detection/infer.json ] && continue
    grep -q '"rc": 0' $R/$s/$m/render.json 2>/dev/null || { log "RENDERFAIL $s/$m"; continue; }
    zr=$(ls -d $R/$s/$m/surface-volumes/*.zarr | head -1); mkdir -p $F/$m
    $PY $W/padview.py $zr $F/$m/$m.zarr > $F/$m/padview.json 2>$F/$m/padview.err || { log "PADFAIL $s/$m $(tail -1 $F/$m/padview.err)"; rm -rf $F/$m; continue; }
    n=$((n+1))
  done < $Q
  [ $n -eq 0 ] && { log "SCROLL $scroll nothing to do"; continue; }
  log "SCROLL $scroll start meshes=$n"; t0=$(date +%s)
  for ck in $CK/ink_9um/hybrid_3d2d-seed43/step-060000.pth $CK/ink_9um/hybrid_3d2d-seed42/step-020000.pth $CK/soup42_early3.pth; do
    $PY -m vesuvius.ink_detection.inference.infer --folder $F --checkpoint-path $ck --direction both --overlap 0.5 --blend-mode hann --batch-size $BATCH --num-workers $WORKERS --no-compile --output-prefix atlas > $F/infer_$(basename $ck .pth).out 2>&1 &
  done
  wait
  log "SCROLL $scroll inference done secs=$(( $(date +%s) - t0 ))"
  # post: rename, mask, previews, receipts
  $PY - "$scroll" "$F" <<'PY'
import glob, json, os, re, shutil, sys, time, numpy as np, tifffile, zarr
from PIL import Image
from scipy import ndimage
scroll, F = sys.argv[1], sys.argv[2]; R = "/workspace/atlas/renders"; TAG = {"step-060000": "s43_060k", "step-020000": "s42_020k", "soup42_early3": "soup42_early3"}
villa = open("/workspace/atlas/villa/.git/HEAD").read().strip()
for md in sorted(glob.glob(os.path.join(F, "*"))):
    if not os.path.isdir(md): continue
    m = os.path.basename(md); out = os.path.join(R, scroll, m, "ink-detection"); os.makedirs(out, exist_ok=True)
    zr = glob.glob(os.path.join(R, scroll, m, "surface-volumes", "*.zarr"))[0]; vid = re.search(r"volume-(\d+)\.zarr", zr).group(1)
    preds = sorted(glob.glob(os.path.join(md, "preds", "*.tif"))); runs = []
    for p in preds:
        mm = re.match(r"atlas_" + re.escape(m) + r"_(.+)_(forward|reverse)_\d+\.tif$", os.path.basename(p))
        if not mm: continue
        tag = TAG.get(mm.group(1), mm.group(1)); name = f"{scroll}-{m}-{vid}-ink9um-{tag}" + ("_reverse" if mm.group(2) == "reverse" else "") + ".tif"
        shutil.move(p, os.path.join(out, name)); runs.append({"tag": tag, "direction": mm.group(2), "file": name})
    a = zarr.open(zr, mode="r")["0"]; valid = np.zeros(a.shape[1:], bool)
    for y in range(0, a.shape[1], 1024): valid[y:y+1024] = a[:, y:y+1024, :].max(axis=0) > 0
    er = ndimage.binary_erosion(valid, iterations=64, border_value=0)
    tifffile.imwrite(os.path.join(out, "valid_mask.tif"), er.astype(np.uint8) * 255, compression="zlib")
    prev = []
    for f in sorted(glob.glob(os.path.join(out, "*ink9um*.tif"))):
        x = tifffile.imread(f).astype(np.float32); x = x / 255.0 if x.max() > 1.5 else x
        H, Wd = (x.shape[0] // 8) * 8, (x.shape[1] // 8) * 8; ds = x[:H, :Wd].reshape(H // 8, 8, Wd // 8, 8).mean((1, 3))
        Image.fromarray((np.clip((ds - 0.25) / 0.5, 0, 1) * 255).astype(np.uint8)).save(f[:-4] + "-ds8.jpg", quality=85)
        prev.append({"file": os.path.basename(f), "shape": list(x.shape), "mean": float(x.mean()), "p99": float(np.percentile(x, 99)), "frac_ge_0.75": float((x >= 0.75).mean())})
    pv = json.load(open(os.path.join(md, "padview.json")))
    if len(runs) < 6:
        print("INFERFAIL", scroll, m, len(runs), "maps", flush=True); open("/workspace/atlas/infer/progress.log", "a").write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} INFERFAIL {scroll}/{m} maps={len(runs)}\n"); continue
    json.dump({"scroll": scroll, "mesh": m, "volume_id": vid, "mode": "folder, 3 checkpoint files concurrent", "padview": pv,
               "recipe": "overlap 0.5, blend hann, direction both, batch 16, --no-compile, no --mask-path (blocks from infer's nonzero occupancy scan; eroded valid mask applied at scoring)",
               "villa_commit": villa, "runs": runs, "maps": prev, "valid_frac": float(valid.mean()), "eroded_frac": float(er.mean()),
               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(os.path.join(out, "infer.json"), "w"), indent=1)
    print("post", scroll, m, len(runs), "maps", flush=True)
PY
  log "SCROLL $scroll post done maps=$(ls $R/$scroll/*/ink-detection/*ink9um*.tif 2>/dev/null | grep -vc ds8)"
  rm -rf $F
done
log "ALL DONE v2 meshes_with_receipts=$(ls $R/*/*/ink-detection/infer.json | wc -l)"
