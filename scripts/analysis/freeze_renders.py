# freeze_renders.py: stop hecate_all.sh's render loop on pod 3 (not its inference loop), keep the meshes already rendered,
# mark renders done so inference finishes, uploads and removes the pod, and write the queue of meshes left for other pods.
import os, signal, time, shutil, glob, collections
H96 = "/workspace/atlas/h96"; Q = "/workspace/atlas/render/queue.txt"
def cmd(p):
    try: return open(f"/proc/{p}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
    except Exception: return ""
def children(p):
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit(): continue
        try:
            ppid = int(open(f"/proc/{d}/stat").read().rsplit(")", 1)[1].split()[1])
        except Exception: continue
        if ppid == p: out.append(int(d))
    return out
def descendants(p):
    out, stack = [], [p]
    while stack:
        q = stack.pop(); c = children(q); out += c; stack += c
    return out
me = os.getpid()
tops = [int(d) for d in os.listdir("/proc") if d.isdigit() and "hecate_all.sh" in cmd(int(d)) and int(d) != me]
parent = min(tops, key=lambda p: os.stat(f"/proc/{p}").st_ctime)
render_loops = []
for c in children(parent):
    if "hecate_all.sh" not in cmd(c): continue
    desc = [cmd(x) for x in descendants(c)]
    if any("vc_render_tifxyz" in x or "sleep 20" in x for x in desc) and not any("hecate.py" in x for x in desc):
        render_loops.append(c)
print("parent", parent, "render loop subshells", render_loops)
for r in render_loops:
    for p in [r] + descendants(r):
        try: os.kill(p, signal.SIGTERM)
        except Exception: pass
time.sleep(5)
for r in render_loops:
    for p in [r] + descendants(r):
        try: os.kill(p, signal.SIGKILL)
        except Exception: pass
kept, dropped = set(), []
for d in glob.glob(f"{H96}/renders/*/*"):
    key = "/".join(d.split("/")[-2:])
    if any(os.path.exists(f"{d}/{m}") for m in (".ready", ".running", ".done")): kept.add(key)
    else: shutil.rmtree(d, ignore_errors=True); dropped.append(key)
open(f"{H96}/RENDERS_DONE", "w").write("frozen by freeze_renders.py; remaining queue handed to other pods\n")
rest = [l for l in open(Q) if "/".join(l.split()[:2]) not in kept]
open(f"{H96}/queue_remaining.txt", "w").writelines(rest)
open(f"{H96}/kept_on_pod3.txt", "w").write("\n".join(sorted(kept)) + "\n")
with open(f"{H96}/progress.log", "a") as f:
    f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + f" FROZEN: render loop stopped; keeping {len(kept)} meshes on this pod, dropped {len(dropped)} partial renders, {len(rest)} meshes handed off\n")
print("kept", len(kept), "dropped partial", dropped, "remaining", len(rest), dict(collections.Counter(l.split()[0] for l in rest)))
print("vc_render still running:", sum(1 for d in os.listdir('/proc') if d.isdigit() and 'vc_render_tifxyz --volume' in cmd(int(d))), "| hecate.py running:", sum(1 for d in os.listdir('/proc') if d.isdigit() and 'hecate.py --checkpoint' in cmd(int(d))))
