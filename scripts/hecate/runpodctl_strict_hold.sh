#!/usr/bin/env bash
# runpodctl wrapper: (1) read RUNPOD_API_KEY from PID 1 (ssh-launched scripts lack the container env); (2) on remove/stop, hold
# while retry_failed.sh is working (up to 3 h, until RETRY_DONE); (3) require every held map to exist path by path in the private repo.
export RUNPOD_API_KEY="$(tr '\0' '\n' < /proc/1/environ | sed -n 's/^RUNPOD_API_KEY=//p')"
if [ "${1:-}" = remove ] || [ "${1:-}" = stop ]; then
  H96=/workspace/atlas/h96; PY=/workspace/atlas/villa/vesuvius/.venv/bin/python
  for i in $(seq 1 180); do [ -f $H96/RETRY_DONE ] && break; pgrep -f "bash $H96/retry_faile[d].sh" > /dev/null || break; sleep 60; done
  echo "$(date -u +%FT%TZ) wrapper: retry hold released (RETRY_DONE=$([ -f $H96/RETRY_DONE ] && echo yes || echo no))" >> $H96/progress.log
  rm -f $H96/strict_verified
  for try in 1 2 3; do
    $PY $H96/strict_verify.py --fix > $H96/strict_verify.out 2>&1
    [ "$(cat $H96/strict_verified 2>/dev/null)" = ok ] && break; sleep 300
  done
  $PY - >> $H96/strict_verify.out 2>&1 <<PY
from huggingface_hub import HfApi
api = HfApi(token=open("/workspace/atlas/.hf_token").read().strip())
for f in ("progress.log", "stats.jsonl", "stats.err"):
    try: api.upload_file(path_or_fileobj="$H96/" + f, path_in_repo="h96/" + f.replace(".", "_$(hostname)."), repo_id="rodriguescarson/eligible-scroll-atlas-held", repo_type="dataset")
    except Exception as e: print("log upload", f, e)
PY
  echo "$(date -u +%FT%TZ) wrapper strict verify: $(cat $H96/strict_verified 2>/dev/null || echo error) | $(grep -E '^(hold|after)' $H96/strict_verify.out | tr '\n' ' ' | cut -c1-200)" >> $H96/progress.log
  [ "$(cat $H96/strict_verified 2>/dev/null)" = ok ] || { echo "$(date -u +%FT%TZ) strict verify failed: not running runpodctl $*" >> $H96/progress.log; exit 1; }
fi
exec /usr/bin/runpodctl "$@"
