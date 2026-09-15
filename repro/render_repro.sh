#!/usr/bin/env bash
export APPIMAGE_EXTRACT_AND_RUN=1 VC3D_CONFIG_DIR=/workspace/vc3d_cfg
VOL=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0800/volumes/20250521135224-8.640um-1.2m-116keV-masked.zarr
for v in plain flip; do
  F=""; [ $v = flip ] && F="--flip-normals"
  echo "START $v $(date -u +%H:%M:%S)" >> progress.log
  /workspace/tools/VC3D.AppImage vc_render_tifxyz --volume /workspace/atlas/repro/vol_stub.zarr --remote-url "$VOL" --segmentation /workspace/atlas/repro/team_mesh --scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 8 --voxel-size 8.64 --voxel-unit micrometer $F --zarr-compressor none --timeout 60 --zarr-output /workspace/atlas/repro/render_$v.zarr > render_$v.out 2>&1 || echo "FAILED $v rc=$?" >> progress.log
  echo "DONE $v $(date -u +%H:%M:%S)" >> progress.log
done
echo "ALL DONE $(date -u +%H:%M:%S)" >> progress.log
