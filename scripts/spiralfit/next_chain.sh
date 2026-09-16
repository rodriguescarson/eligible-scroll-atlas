#!/usr/bin/env bash
# next_chain.sh (name contains "chain.sh" so guard_v3 counts it as work): wait for the running fit_run.sh, archive that window's
# logs (fit_run.sh overwrites them), back up the finished run dir path by path to spiralfit/<scroll>/<run>/ in the private repo,
# then fit the window in window_next.txt. No window_next.txt: exit and leave backup + removal to guard_v3.
set -u
W=/workspace; F=$W/fit; L=$F/progress.log
log(){ echo "$(date -u +%FT%TZ) chain: $*" >> $L; }
PID=$(pgrep -f "bash /workspace/fit/fit_run.s[h]" | head -1)
log "waiting for fit_run.sh pid ${PID:-none}"
while [ -n "$PID" ] && kill -0 $PID 2>/dev/null; do sleep 20; done
read Z0 Z1 < $F/window.txt
A=$F/logs_${Z0}_${Z1}; mkdir -p $A; cp $F/fit_B.log $F/export.log $F/flatten_*.log $F/render_*.log $F/in_*.json $A/ 2>/dev/null
RUN=$(ls -d $W/out/*/*_slice-${Z0}-${Z1}_* 2>/dev/null | tail -1)
log "window [$Z0,$Z1) logs archived to $A; backing up ${RUN:-none}"
for z in $RUN/render/*.zarr; do [ -d "$z" ] && tar -cf "$z.tar" -C "$(dirname $z)" "$(basename $z)" && rm -rf "$z"; done
python3 - "$RUN" > $F/chain_upload_${Z0}.out 2>&1 <<'PY'
import glob, os, sys
from huggingface_hub import HfApi
run = sys.argv[1].rstrip("/") + "/"; R = "rodriguescarson/eligible-scroll-atlas-held"
api = HfApi(token=open("/workspace/fit/.hf_token").read().strip())
prefix = "spiralfit/" + run.rstrip("/").split("/")[-2] + "/" + os.path.basename(run.rstrip("/"))
local = {os.path.relpath(f, run) for f in glob.glob(run + "**/*", recursive=True) if os.path.isfile(f) and "/.cache/" not in f and ".zarr/" not in f}
listing = lambda: {f[len(prefix) + 1:] for f in api.list_repo_files(R, repo_type="dataset") if f.startswith(prefix + "/")}
todo = sorted(local - listing()); print(prefix, "local", len(local), "missing before", len(todo))
for i in range(0, len(todo), 2000):
    api.upload_folder(repo_id=R, repo_type="dataset", folder_path=run, path_in_repo=prefix, allow_patterns=todo[i:i + 2000], commit_message=f"spiral fit backup {prefix} {i}")
miss = sorted(local - listing()); print(prefix, "missing after", len(miss), miss[:3])
PY
log "backup: $(grep 'missing after' $F/chain_upload_${Z0}.out | cut -c1-200 || tail -1 $F/chain_upload_${Z0}.out)"
if [ -f $F/window_next.txt ]; then
  cp $F/window_next.txt $F/window.txt; rm -f $F/window_next.txt; read Z0 Z1 < $F/window.txt
  log "starting next window [$Z0,$Z1)"
  cd $F && bash /workspace/fit/fit_run.sh > $F/fit_run_${Z0}.out 2>&1
  log "window [$Z0,$Z1) fit_run.sh exited rc=$?"
else
  log "no window_next.txt: nothing chained"
fi
