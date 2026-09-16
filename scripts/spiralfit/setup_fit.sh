#!/usr/bin/env bash
# setup_fit.sh: villa spiral-fitting + lasagna environments and PHerc0826 inputs for one test window.
set -u
W=/workspace; S=PHerc0826; V=20250821151701; F=$W/fit; L=$F/progress.log; DS=$W/ds/$S
mkdir -p $F $DS/lasagna_inputs $DS/tracks
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
B=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com
log START
apt-get update -qq > $F/apt.out 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential cmake ninja-build libfuse2 > $F/apt.out 2>&1; log "apt rc=$?"
python3 -m pip install -q awscli >> $F/apt.out 2>&1; log "awscli rc=$? $(aws --version 2>&1 | cut -c1-40)"
uv python install 3.14 > $F/uvpy.out 2>&1; log "uv python 3.14 rc=$?"
cd $W; [ -d villa/.git ] || git clone -q https://github.com/ScrollPrize/villa.git villa
cd villa && git fetch -q origin && git checkout -q origin/main && log "villa $(git rev-parse HEAD)"
cd spiral-fitting && uv sync > $F/uv_spiral.out 2>&1; log "spiral-fitting uv sync rc=$? | $(tail -2 $F/uv_spiral.out | tr '\n' ' ' | cut -c1-200)"
.venv/bin/python -c "import torch; import vc_spiral; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" >> $L 2>&1
cd ../lasagna && uv run --python 3.14 --no-project python scripts/bootstrap_venv.py --venv .venv --backend cu128 > $F/lasagna_venv.out 2>&1; log "lasagna venv rc=$? | $(tail -2 $F/lasagna_venv.out | tr '\n' ' ' | cut -c1-200)"
# inputs
curl -sfL -o $DS/umbilicus.json "$B/$S/representations/umbilicus/$(curl -s "$B/?prefix=$S/representations/umbilicus/" | grep -o "<Key>[^<]*</Key>" | sed 's/<[^>]*>//g' | head -1 | xargs basename)"
read Z0 Z1 < <(python3 - $DS/umbilicus.json <<'PY'
import json, sys, statistics
d = json.load(open(sys.argv[1])); pts = d.get("control_points", d if isinstance(d, list) else [])
zs = sorted(float(p[2]) for p in pts); med = statistics.median(zs); c = int(round(med / 16) * 16)
print(c - 400, c + 400)
PY
)
echo "$Z0 $Z1" > $F/window.txt; log "umbilicus $(python3 -c "import json;d=json.load(open('$DS/umbilicus.json'));print(type(d).__name__, list(d)[:3] if isinstance(d,dict) else len(d))") window [$Z0,$Z1)"
LAS=s3://vesuvius-challenge-open-data/$S/representations/predictions/lasagna/$V-lasagna-20260419180421
aws s3 ls --no-sign-request $LAS/ > $F/lasagna_ls.txt 2>&1; log "lasagna listing: $(tr '\n' ' ' < $F/lasagna_ls.txt | cut -c1-300)"
aws s3 cp --no-sign-request $LAS/$S.lasagna.json $DS/ > /dev/null 2>&1
c0=$(( Z0 / 4 / 32 - 1 )); c1=$(( (Z1 + 3) / 4 / 32 + 1 ))
for n in nx ny grad_mag; do
  src=$(grep -o "[^ ]*_$n\.ome\.zarr/" $F/lasagna_ls.txt | head -1); [ -z "$src" ] && src="${S}_$n.ome.zarr/"
  inc=(--exclude '*' --include '.zattrs' --include '.zgroup' --include '2/.zarray' --include '2/.zattrs')
  for c in $(seq $c0 $c1); do inc+=(--include "2/$c/*"); done
  t0=$(date +%s); aws s3 sync --no-sign-request --only-show-errors "$LAS/$src" "$DS/lasagna_inputs/las_008_$n.ome.zarr/" "${inc[@]}" > $F/sync_$n.out 2>&1
  log "lasagna $n <- $src rc=$? files=$(find $DS/lasagna_inputs/las_008_$n.ome.zarr -type f | wc -l) secs=$(( $(date +%s) - t0 ))"
done
T=https://dl.ash2txt.org/datasets/spiral_datasets/$S/$V/tracks
for f in ${S}_${V}_surface_m7_L0_th0.2.extract.json ${S}_${V}_surface_m7_L0_th0.2.dbm; do
  t0=$(date +%s); curl -sfL -C - -o $DS/tracks/$f "$T/$f"; rc=$?
  log "tracks $f rc=$rc bytes=$(stat -c %s $DS/tracks/$f 2>/dev/null) expected=$(curl -sIL "$T/$f" | grep -i content-length | tail -1 | tr -dc 0-9) secs=$(( $(date +%s) - t0 ))"
done
cat > $DS/spiral-scroll.json <<JSON
{"schema_version": 1, "name": "$S", "voxel_size_um": 9.362, "spiral_outward_sense": "CW",
 "normal_zarr_group": "2", "lasagna_scale": 4,
 "paths": {"tracks_dbm": "tracks/${S}_${V}_surface_m7_L0_th0.2.dbm"}}
JSON
log "SETUP DONE"
