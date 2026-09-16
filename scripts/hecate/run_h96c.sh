#!/usr/bin/env bash
# run_h96.sh: pod 3 entry point. Setup (pinned AppImage, meshes, villa env, checkpoints), then hecate_all.sh.
# If setup fails, the pod removes itself instead of idling.
W=/workspace/atlas; mkdir -p $W/log $W/render $W/h96
echo "$(date -u +%FT%TZ) run_h96 START" >> $W/h96/progress.log
bash $W/gpu_setup.sh > $W/log/setup.out 2>&1; rc=$?
echo "$(date -u +%FT%TZ) setup rc=$rc | $(grep -E 'BW|torch|appimage sha|meshes commit|FATAL|SETUP DONE' $W/log/setup.log | tr '\n' ' ' | cut -c1-400)" >> $W/h96/progress.log
if [ $rc -ne 0 ] || grep -q FATAL $W/log/setup.log || [ ! -x $W/tools/VC3D.AppImage ]; then
  echo "$(date -u +%FT%TZ) setup failed, removing pod" >> $W/h96/progress.log; runpodctl remove pod vwj0c2c7bsnlw1 || runpodctl stop pod vwj0c2c7bsnlw1; exit 1
fi
POD=vwj0c2c7bsnlw1 bash $W/hecate_all.sh
