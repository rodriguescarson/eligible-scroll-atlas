#!/usr/bin/env bash
export APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=/workspace/vc3d_cfg
B=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com
declare -A VOL=( [PHerc0813]="$B/PHerc0813/volumes/20250821151723-9.362um-1.2m-113keV-masked.zarr" [PHerc0211]="$B/PHerc0211/volumes/20250821151803-9.362um-1.2m-113keV-masked.zarr" [PHerc0800]="$B/PHerc0800/volumes/20250521135224-8.640um-1.2m-116keV-masked.zarr" [PHerc0125]="$B/PHerc0125/volumes/20250821151825-9.362um-1.2m-113keV-masked.zarr" )
declare -A VS=( [PHerc0813]=9.362 [PHerc0211]=9.362 [PHerc0800]=8.64 [PHerc0125]=9.362 )
one() { s=$1; m=$2; t0=$(date +%s); c0=$(find /workspace/remote_cache -type f | wc -l)
  /workspace/tools/VC3D.AppImage vc_render_tifxyz --volume /workspace/atlas/bw/stub.zarr --remote-url "${VOL[$s]}" --segmentation /workspace/atlas/meshes/$s/$m --scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 4 --voxel-size ${VS[$s]} --voxel-unit micrometer --flip-normals --zarr-compressor none --timeout 60 --zarr-output /workspace/atlas/bw/${s}_${m}.zarr > ${s}_${m}.out 2>&1; rc=$?
  t1=$(date +%s); c1=$(find /workspace/remote_cache -type f | wc -l); echo "DONE $s/$m rc=$rc secs=$((t1-t0)) chunks_added=$((c1-c0)) $(date -u +%H:%M:%S)" >> progress.log; }
mkdir -p stub.zarr; echo "START single $(date -u +%H:%M:%S)" >> progress.log
one PHerc0813 z12496_w100
echo "START 4way $(date -u +%H:%M:%S)" >> progress.log
one PHerc0211 z9120_w100 & one PHerc0800 z17072_w100 & one PHerc0125 z6944_w080 & one PHerc0813 z11296_w100 & wait
echo "ALL DONE $(date -u +%H:%M:%S)" >> progress.log
