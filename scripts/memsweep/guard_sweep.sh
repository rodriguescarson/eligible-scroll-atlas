#!/usr/bin/env bash
# guard_sweep.sh <pod id>: this pod holds no dataset token, so results leave only by scp. Remove the pod when the sweep is done
# AND the results have been fetched (a FETCHED marker), or when nothing has run for 45 minutes, so it never sits idle.
set -u
POD=$1; W=/workspace/sweep; L=$W/progress.log
log(){ echo "$(date -u +%FT%TZ) guard: $*" >> $L; }
log "armed for $POD"
idle=0
while true; do
  if grep -q "SWEEP DONE" $L 2>/dev/null || [ -f $W/SWEEP_DONE ]; then break; fi
  if pgrep -f "sweep.py|one_run.py|setup.sh|pip install|hf_hub_download" > /dev/null; then idle=0; else idle=$((idle + 60)); fi
  if [ $idle -ge 2700 ]; then log "nothing running for 45 min; removing"; runpodctl remove pod $POD || runpodctl stop pod $POD; exit 0; fi
  sleep 60
done
log "sweep finished; waiting up to 60 min for the results to be fetched"
for i in $(seq 1 60); do [ -f $W/FETCHED ] && break; sleep 60; done
log "removing pod (fetched=$([ -f $W/FETCHED ] && echo yes || echo timeout))"
runpodctl remove pod $POD || runpodctl stop pod $POD
