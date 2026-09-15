#!/usr/bin/env bash
# kills stale upload loops / hf uploads (never itself) and starts a fresh upload_loop.sh
cd /workspace/atlas
for p in $(pgrep -f "bash upload_loop.sh"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
for p in $(pgrep -f "hf upload-large-folder"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
sleep 2
setsid nohup bash upload_loop.sh > log/upload_loop.out 2>&1 < /dev/null &
disown
sleep 1
echo "loops: $(pgrep -fc 'bash upload_loop.sh')"
