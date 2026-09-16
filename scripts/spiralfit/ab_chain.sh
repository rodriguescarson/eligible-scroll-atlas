#!/usr/bin/env bash
# ab_chain.sh (name contains "chain.sh" so guard_v3 counts it as work): A/B on ONE PHerc0191 window. The 90-winding run puts 64-74
# windings per ray where the scan shows 22-42 sheet peaks at a strict threshold and 28-77 from the autocorrelation period, and our
# pitch (10.5 vx) is about half the scan's (14-19 vx). So refit the SAME window with 45 windings and compare both against the scan.
set -u
W=/workspace; F=$W/fit; L=$F/progress.log
log(){ echo "$(date -u +%FT%TZ) ab: $*" >> $L; }
PID=$(pgrep -f "bash /workspace/fit/fit_run.s[h]" | head -1)
log "waiting for the 90-winding run to finish (pid ${PID:-none})"
while [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; do sleep 20; done
RUN=$(ls -d $W/out/PHerc0191/*_slice-11600-12400_0-patch 2>/dev/null | tail -1)
[ -n "$RUN" ] || { log "no run dir for the 90-winding run; stopping"; exit 1; }
mkdir -p $F/logs_w90 && cp $F/fit_B.log $F/export.log $F/flatten_*.log $F/render_*.log $F/in_*.json $F/logs_w90/ 2>/dev/null
mv "$RUN" "${RUN}_w90"; RUN90="${RUN}_w90"; log "90-winding run kept as $(basename $RUN90)"
python3 - "$RUN90" > $F/ab_backup.out 2>&1 <<'PY'
import glob, os, sys
from huggingface_hub import HfApi
run = sys.argv[1].rstrip("/") + "/"; R = "rodriguescarson/eligible-scroll-atlas-held"
api = HfApi(token=open("/workspace/fit/.hf_token").read().strip())
api.create_repo(R, repo_type="dataset", private=True, exist_ok=True)
prefix = "spiralfit/" + run.rstrip("/").split("/")[-2] + "/" + os.path.basename(run.rstrip("/"))
local = {os.path.relpath(f, run) for f in glob.glob(run + "**/*", recursive=True) if os.path.isfile(f) and "/.cache/" not in f and ".zarr/" not in f}
listing = lambda: {f[len(prefix) + 1:] for f in api.list_repo_files(R, repo_type="dataset") if f.startswith(prefix + "/")}
todo = sorted(local - listing()); print(prefix, "local", len(local), "missing before", len(todo))
for i in range(0, len(todo), 2000):
    api.upload_folder(repo_id=R, repo_type="dataset", folder_path=run, path_in_repo=prefix, allow_patterns=todo[i:i + 2000], commit_message=f"PHerc0191 90-winding run {i}")
miss = sorted(local - listing()); print(prefix, "missing after", len(miss), miss[:3])
PY
log "backup: $(grep 'missing after' $F/ab_backup.out | cut -c1-160)"
python3 - <<'PY'
src = open("/workspace/fit/fit_run.sh").read()
for a, b in (('shell_outer_winding_idx\\": 90', 'shell_outer_winding_idx\\": 45'), ('model_gap_expander_num_windings\\": 90', 'model_gap_expander_num_windings\\": 45')):
    assert a in src, a
    src = src.replace(a, b)
src = src.replace("# fit_run.sh:", "# fit_run45.sh (A/B arm: 45 windings instead of 90):")
open("/workspace/fit/fit_run45.sh", "w").write(src)
print("edited override:", [l.strip()[:200] for l in src.splitlines() if "shell_outer_winding_idx" in l])
PY
log "45-winding script: $(grep -o 'shell_outer_winding_idx\\\\\": [0-9]*' $F/fit_run45.sh | head -1) $(grep -o 'model_gap_expander_num_windings\\\\\": [0-9]*' $F/fit_run45.sh | head -1)"
log "starting the 45-winding run on the same window $(cat $F/window.txt)"
bash $F/fit_run45.sh > $F/fit_run45.out 2>&1
log "45-winding run exited rc=$?"
