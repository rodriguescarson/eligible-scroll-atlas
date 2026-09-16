#!/usr/bin/env bash
# idle guard: remove the pod after 45 min with no fitter, flatten, render, download or build process running
POD=$1; L=/workspace/fit/progress.log; idle=0
while true; do
  if pgrep -f "fit_spiral|lasagna/fit.py|vc_render_tifxyz|uv sync|uv pip|aws s3|curl -|bootstrap_venv|export_all_windings|hf upload|huggingface" > /dev/null; then idle=0; else idle=$((idle + 60)); fi
  if [ $idle -ge 2700 ]; then echo "$(date -u +%FT%TZ) guard: idle 45 min, removing pod" >> $L; runpodctl remove pod $POD || runpodctl stop pod $POD; fi
  sleep 60
done
