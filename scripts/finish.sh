#!/usr/bin/env bash
# finish.sh: runs after infer_all.sh. Uploads renders + maps to the private HF dataset, verifies, then stops the pod.
# Without a token it refuses to stop (the container disk is the only copy) and says so in the log.
W=/workspace/atlas; P=$W/infer/progress.log
log(){ echo "$(date -u +%FT%TZ) $*" >> $P; }
TOK=$(cat $W/.hf_token 2>/dev/null)
if [ -z "$TOK" ]; then log "FINISH: no HF token at $W/.hf_token; pod left running, nothing uploaded"; exit 0; fi
export HF_TOKEN=$TOK; REPO=${HF_REPO:-rodriguescarson/eligible-scroll-atlas-renders}
uvx --from huggingface_hub hf repo create $REPO --repo-type dataset --private >> $W/log/upload.out 2>&1
uvx --from huggingface_hub hf upload-large-folder $REPO $W/renders --repo-type dataset --num-workers 8 >> $W/log/upload.out 2>&1; rc=$?
log "FINISH: upload rc=$rc"
n_local=$(find $W/renders -type f | wc -l)
n_remote=$(uvx --from huggingface_hub python -c "from huggingface_hub import HfApi; print(len(HfApi().list_repo_files('$REPO', repo_type='dataset')))" 2>/dev/null)
log "FINISH: local files $n_local remote files $n_remote"
if [ $rc -eq 0 ] && [ "${n_remote:-0}" -ge "$n_local" ]; then log "FINISH: verified, stopping pod"; runpodctl stop pod ${RUNPOD_POD_ID:-qeg3surfkcuqin}; else log "FINISH: NOT verified, pod left running"; fi
