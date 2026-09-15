#!/usr/bin/env bash
# gpu_setup.sh: idempotent environment for the eligible-scroll-atlas render + inference stage.
# Run on a fresh runpod/base:1.2.0-ubuntu2204 pod:  setsid nohup bash gpu_setup.sh > /workspace/atlas/log/setup.out 2>&1 &
set -u
W=/workspace/atlas
mkdir -p $W/log $W/checkpoints $W/tools $W/control $W/renders
LOG=$W/log/setup.log
step(){ echo "$(date -u +%FT%TZ) $*" | tee -a $LOG; }
step "SETUP START host=$(hostname) pod=${RUNPOD_POD_ID:-?} dc=${RUNPOD_DC_ID:-?}"

# 0. raw S3 bandwidth, 128 chunks of the PHerc0813 masked volume, 32 parallel (about 150 MB)
V=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0813/volumes/20250821151723-9.362um-1.2m-113keV-masked.zarr
rm -rf /tmp/bw && mkdir -p /tmp/bw && cd /tmp/bw && t0=$(date +%s.%N)
for y in 10 11 13 14; do for x in $(seq 20 51); do curl -s -o c_${y}_$x "$V/0/103/$y/$x" & done; wait; done
t1=$(date +%s.%N); B=$(du -cb c_* | tail -1 | cut -f1)
step "BW $(python3 -c "b=$B; t=$t1-$t0; print(f'{b/1e6:.0f} MB in {t:.1f}s = {b/1e6/t:.1f} MB/s')")"
rm -rf /tmp/bw

# 1. VC3D AppImage (same release asset as the PHerc0800 reproduction) + remote cache config
cd $W/tools
if [ ! -f VC3D.AppImage ]; then
  curl -sL -o VC3D.AppImage https://github.com/ScrollPrize/villa/releases/download/latest/VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage && chmod +x VC3D.AppImage
fi
step "appimage sha256 $(sha256sum VC3D.AppImage | cut -c1-64)"
mkdir -p /workspace/vc3d_cfg /workspace/remote_cache
printf '[viewer]\nremote_cache_dir=/workspace/remote_cache\n' > /workspace/vc3d_cfg/VC3D.ini

# 2. the 340 eligible meshes (pscamillo), pinned commit
if [ ! -d $W/meshes-repo/.git ]; then git clone -q --depth 1 https://github.com/pscamillo/vesuvius-eligible-meshes $W/meshes-repo; fi
ln -sfn $W/meshes-repo/meshes $W/meshes
step "meshes commit $(git -C $W/meshes-repo rev-parse HEAD) dirs $(find $W/meshes/ -name meta.json | wc -l)"

# 3. villa main: vesuvius package with the ink_detection extra, CUDA torch
cd $W
if [ ! -d villa/.git ]; then git clone -q --depth 1 --branch main https://github.com/ScrollPrize/villa villa; fi
step "villa commit $(git -C villa rev-parse HEAD)"
cd villa/vesuvius
uv sync --frozen --extra models --extra label-transfer --no-install-package volume-cartographer > $W/log/uv_sync.out 2>&1; step "uv sync rc=$? $(tail -1 $W/log/uv_sync.out)"
CUDA=$(.venv/bin/python -c 'import torch;print(int(torch.cuda.is_available()))' 2>/dev/null || echo 0)
if [ "$CUDA" != "1" ]; then
  TV=$(.venv/bin/python -c 'import torch;print(torch.__version__.split("+")[0])')
  VV=$(.venv/bin/python -c 'import torchvision;print(torchvision.__version__.split("+")[0])' 2>/dev/null || echo "")
  SPEC="torch==${TV}+cu126"; [ -n "$VV" ] && SPEC="$SPEC torchvision==${VV}+cu126"
  uv pip install --python .venv/bin/python --reinstall $SPEC --index https://download.pytorch.org/whl/cu126 --index-strategy unsafe-best-match > $W/log/torch_cu.out 2>&1; step "torch cu126 reinstall rc=$? ($SPEC)"
fi
.venv/bin/python -c 'import torch, vesuvius.ink_detection; print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-", torch.cuda.get_arch_list())' 2>&1 | tee -a $LOG
.venv/bin/python -m vesuvius.ink_detection.inference.infer --help > $W/log/infer_help.txt 2>&1; step "infer --help rc=$?"

# 4. checkpoints from the public release
cd $W
uvx --from huggingface_hub hf download scrollprize/ink_9um --include 'hybrid_3d2d-seed42/step-010000.pth' 'hybrid_3d2d-seed42/step-020000.pth' 'hybrid_3d2d-seed42/step-030000.pth' 'hybrid_3d2d-seed43/step-060000.pth' --local-dir checkpoints/ink_9um > $W/log/hf_download.out 2>&1; step "hf download rc=$?"
sha256sum checkpoints/ink_9um/*/*.pth | tee -a $LOG

# 5. the seed42 10k/20k/30k weight soup (inkbench soup.py recipe, "soup_s42_early3")
$W/villa/vesuvius/.venv/bin/python $W/soup42.py 2>&1 | tee -a $LOG
step "SETUP DONE"
