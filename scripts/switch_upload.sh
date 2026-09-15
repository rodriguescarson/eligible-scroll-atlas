#!/usr/bin/env bash
# stop the chunk-level upload loop and its hf process (never itself), recreate the repo empty, start the packed uploader
cd /workspace/atlas
for p in $(pgrep -f "bash upload_loop.sh"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
for p in $(pgrep -f "hf upload-large-folder"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
sleep 3
export HF_TOKEN=$(cat .hf_token)
uvx --from huggingface_hub hf repo delete rodriguescarson/eligible-scroll-atlas-renders --repo-type dataset -y >> log/upload.log 2>&1
rm -rf renders/.cache
villa/vesuvius/.venv/bin/python -c "import huggingface_hub; print('hf_hub', huggingface_hub.__version__)"
setsid nohup villa/vesuvius/.venv/bin/python upload_packed.py > log/upload_packed.out 2>&1 < /dev/null &
disown; sleep 20; echo "packed uploader: $(pgrep -fc 'upload_packed.py')"; tail -3 log/upload.log; tail -3 log/upload_packed.out
