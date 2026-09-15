#!/usr/bin/env bash
# upload_loop.sh: incremental, resumable upload of /workspace/atlas/renders to the HF dataset repo (public; renders are inputs,
# the analysis is held separately). Waits for /workspace/atlas/.hf_token to appear, then re-runs hf upload-large-folder every
# 10 min (it skips files already uploaded) until infer_all.sh has written ALL DONE and one final pass has completed. Then it
# verifies the remote file count against the local one and stops the pod only if they match.
W=/workspace/atlas; P=$W/infer/progress.log; L=$W/log/upload.log
log(){ echo "$(date -u +%FT%TZ) $*" >> $L; }
REPO=${HF_REPO:-rodriguescarson/eligible-scroll-atlas-renders}
until [ -s $W/.hf_token ]; do sleep 60; done
export HF_TOKEN=$(cat $W/.hf_token); export HF_HUB_ENABLE_HF_TRANSFER=0
uvx --from huggingface_hub hf repo create $REPO --repo-type dataset >> $L 2>&1
log "repo ready $REPO"
while true; do
  uvx --from huggingface_hub hf upload-large-folder $REPO $W/renders --repo-type dataset --num-workers 6 --exclude "*/screens.json" --exclude "*/plant_eval.json" >> $W/log/upload_pass.out 2>&1; rc=$?
  log "pass rc=$rc local_files=$(find $W/renders -type f | wc -l) size=$(du -sh $W/renders | cut -f1)"
  if grep -q "ALL DONE" $P 2>/dev/null; then
    uvx --from huggingface_hub hf upload-large-folder $REPO $W/renders --repo-type dataset --num-workers 6 --exclude "*/screens.json" --exclude "*/plant_eval.json" >> $W/log/upload_pass.out 2>&1; rc=$?
    n_local=$(find $W/renders -type f | wc -l)
    n_remote=$(uvx --from huggingface_hub python -c "from huggingface_hub import HfApi; print(len(HfApi().list_repo_files('$REPO', repo_type='dataset')))" 2>/dev/null)
    log "FINAL rc=$rc local=$n_local remote=$n_remote"
    if [ $rc -eq 0 ] && [ "${n_remote:-0}" -ge "$n_local" ]; then log "verified, stopping pod"; runpodctl stop pod ${RUNPOD_POD_ID:-qeg3surfkcuqin}; exit 0; fi
    log "NOT verified; pod left running"; exit 1
  fi
  sleep 600
done
