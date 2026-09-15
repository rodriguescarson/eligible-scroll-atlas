#!/usr/bin/env bash
# stop the v2 loop and its inference children (never itself), drop receipts with no maps, relaunch
cd /workspace/atlas
for p in $(pgrep -f "bash infer_v2.sh"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
for p in $(pgrep -f "inference.infer --folder"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null; done
sleep 3
n=0; for j in renders/*/*/ink-detection/infer.json; do grep -q '"runs": \[\]' "$j" && { rm -f "$j"; n=$((n+1)); }; done
echo "removed $n empty receipts; remaining receipts: $(ls renders/*/*/ink-detection/infer.json 2>/dev/null | wc -l)"
rm -rf tmp_v2
setsid nohup bash infer_v2.sh > log/infer_v2.out 2>&1 < /dev/null &
disown; sleep 1; echo "v2 loops: $(pgrep -fc 'bash infer_v2.sh')"
