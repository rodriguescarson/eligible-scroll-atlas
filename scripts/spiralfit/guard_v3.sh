#!/usr/bin/env bash
# guard_v3.sh <pod id>: replaces guard_v2 (45 min idle grace; uploaded run dirs to the repo ROOT, so a second fit would overwrite
# the first; "verified" compared against the whole repo's file count, so it always passed).
# Now: 15 min with no fit/flatten/render/export process once FIT_RUN DONE is logged (45 min before that), then every run dir goes to
# spiralfit/<scroll>/<run>/ and is verified path by path (3 tries); the pod is removed only when nothing is missing.
POD=$1; W=/workspace; F=$W/fit; L=$F/progress.log; idle=0
log(){ echo "$(date -u +%FT%TZ) guard3: $*" >> $L; }
PAT="fit_spiral|lasagna/fit.py|vc_render_tifxyz|uv sync|uv pip|aws s3|curl -|bootstrap_venv|export_all_windings|refit.sh|fit_run.sh|chain.sh"
log "start"
while true; do
  if pgrep -f "$PAT" > /dev/null; then idle=0; else idle=$((idle + 60)); fi
  lim=2700; grep -q "FIT_RUN DONE" $L && lim=900
  [ $idle -ge $lim ] && break
  sleep 60
done
log "idle ${idle}s: backing up before removal"
for z in $W/out/*/*/render/*.zarr; do [ -d "$z" ] && tar -cf "$z.tar" -C "$(dirname $z)" "$(basename $z)" && rm -rf "$z"; done
python3 -m pip install -q huggingface_hub >> $F/guard_pip.out 2>&1
for try in 1 2 3; do
  python3 - <<PY > $F/guard3_upload.out 2>&1
import glob, os
from huggingface_hub import HfApi
api = HfApi(token=open("$F/.hf_token").read().strip()); R = "rodriguescarson/eligible-scroll-atlas-held"
api.create_repo(R, repo_type="dataset", private=True, exist_ok=True)
api.upload_folder(repo_id=R, repo_type="dataset", folder_path="$F", path_in_repo="spiralfit/fit_logs", allow_patterns=["*.log", "*.out", "*.txt", "*.json", "*.sh", "*.py"], ignore_patterns=[".hf_token"])
missing_total = 0
for run in sorted(glob.glob("$W/out/*/*/")):
    scroll = run.rstrip("/").split("/")[-2]; prefix = f"spiralfit/{scroll}/" + os.path.basename(run.rstrip("/"))
    local = {os.path.relpath(f, run) for f in glob.glob(run + "**/*", recursive=True) if os.path.isfile(f) and "/.cache/" not in f and ".zarr/" not in f}
    listing = lambda: {f[len(prefix) + 1:] for f in api.list_repo_files(R, repo_type="dataset") if f.startswith(prefix + "/")}
    todo = sorted(local - listing()); print(prefix, "local", len(local), "missing before", len(todo))
    for i in range(0, len(todo), 2000):
        api.upload_folder(repo_id=R, repo_type="dataset", folder_path=run, path_in_repo=prefix, allow_patterns=todo[i:i + 2000], commit_message=f"spiral fit backup {prefix} {i}")
    miss = sorted(local - listing()); missing_total += len(miss); print(prefix, "missing after", len(miss), miss[:3])
open("$F/guard3_verified", "w").write("ok" if missing_total == 0 else "short")
PY
  [ "$(cat $F/guard3_verified 2>/dev/null)" = ok ] && break
  log "backup try $try not verified: $(tail -2 $F/guard3_upload.out | tr '\n' ' ' | cut -c1-200)"; sleep 300
done
if [ "$(cat $F/guard3_verified 2>/dev/null)" = ok ]; then
  log "backup verified ($(grep 'missing after' $F/guard3_upload.out | tr '\n' ' ' | cut -c1-240)); removing pod"; runpodctl remove pod $POD || runpodctl stop pod $POD
else
  log "backup NOT verified after 3 tries; pod left running for a manual check"
fi
