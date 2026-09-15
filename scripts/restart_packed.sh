#!/usr/bin/env bash
cd /workspace/atlas
for p in $(pgrep -f "upload_packed.py"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
sleep 2; rm -f upload/stage/*.tar
setsid nohup villa/vesuvius/.venv/bin/python upload_packed.py > log/upload_packed.out 2>&1 < /dev/null &
disown; sleep 3; echo "packed uploader: $(pgrep -fc 'upload_packed.py') uploaded so far: $(wc -l < upload/uploaded.txt)"
