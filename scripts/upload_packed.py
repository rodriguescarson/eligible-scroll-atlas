"""upload_packed.py: incremental upload of the atlas to the public HF dataset repo within the Hub's limits
(free plan: 128 repository commits per hour, 1000 api requests per 5 min, <100k files per repo; the raw zarr layout is
580k chunk files). Per mesh: <scroll>/<mesh>/surface-volumes.tar (zarr + render.json; untar inside <scroll>/<mesh>/ for the
team's layout), committed 25 tars at a time. ink-detection outputs (maps, previews, mask, infer.json) committed 300 files at
a time; screens.json and plant_eval.json never uploaded. One pass every 10 min. After the inference log says ALL DONE and
the remote counts match, the pod is stopped. State: /workspace/atlas/upload/uploaded.txt (meshes), uploaded_files.txt."""
import glob, os, re, subprocess, sys, time
from huggingface_hub import HfApi, CommitOperationAdd
W = "/workspace/atlas"; R = f"{W}/renders"; ST = f"{W}/upload"; os.makedirs(f"{ST}/stage", exist_ok=True)
REPO = os.environ.get("HF_REPO", "rodriguescarson/eligible-scroll-atlas-renders")
LOG = f"{W}/log/upload.log"; DONE = f"{ST}/uploaded.txt"; DONE_F = f"{ST}/uploaded_files.txt"
def log(m): open(LOG, "a").write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {m}\n")
def readset(p): return set(open(p).read().split()) if os.path.exists(p) else set()
api = HfApi(token=open(f"{W}/.hf_token").read().strip())

def commit(ops, msg):
    """create_commit with rate-limit handling; returns True on success."""
    for attempt in range(6):
        try:
            api.create_commit(repo_id=REPO, repo_type="dataset", operations=ops, commit_message=msg); return True
        except Exception as e:
            s = str(e); m = re.search(r"retry this action in (\d+) minute", s)
            if m: wait = int(m.group(1)) * 60 + 30; log(f"commit limit: sleeping {wait}s ({msg})"); time.sleep(wait); continue
            if "429" in s: log(f"api limit: sleeping 320s ({msg})"); time.sleep(320); continue
            log(f"FAIL {msg}: {s[:200]}"); return False
    return False

for attempt in range(20):
    try: api.create_repo(REPO, repo_type="dataset", exist_ok=True); break
    except Exception as e: log(f"create_repo retry {attempt + 1}: {str(e)[:120]}"); time.sleep(90)
log(f"repo ready {REPO}")
queue = [l.split() for l in open(f"{W}/render/queue.txt")]
ALLOW = re.compile(r"/ink-detection/(.*ink9um.*\.tif|.*-ds8\.jpg|valid_mask\.tif|infer\.json)$")
while True:
    done = readset(DONE); pending = []
    for s, m, *_ in queue:
        key = f"{s}/{m}"; d = f"{R}/{s}/{m}"
        if key in done or not os.path.exists(f"{d}/render.json") or '"rc": 0' not in open(f"{d}/render.json").read(): continue
        pending.append((key, d))
    n_new = 0
    for i in range(0, len(pending), 25):
        batch = pending[i:i + 25]; ops = []; tars = []
        for key, d in batch:
            tar = f"{ST}/stage/{key.replace('/', '_')}.tar"
            subprocess.run(["tar", "-cf", tar, "-C", d, "surface-volumes", "render.json"], check=True)
            ops.append(CommitOperationAdd(path_in_repo=f"{key}/surface-volumes.tar", path_or_fileobj=tar)); tars.append(tar)
        if commit(ops, f"renders {batch[0][0]} .. {batch[-1][0]} ({len(batch)})"):
            with open(DONE, "a") as f: f.write("".join(k + "\n" for k, _ in batch))
            n_new += len(batch)
        for t in tars: os.remove(t)
    log(f"render tars: +{n_new}, total {len(done) + n_new} of {len(queue)}")
    donef = readset(DONE_F)
    files = [p for p in glob.glob(f"{R}/*/*/ink-detection/*") if ALLOW.search(p) and os.path.relpath(p, R) not in donef]
    if os.path.exists(f"{R}/README.md") and "README.md" not in donef: files.append(f"{R}/README.md")
    n_f = 0
    for i in range(0, len(files), 300):
        batch = files[i:i + 300]
        ops = [CommitOperationAdd(path_in_repo=os.path.relpath(p, R), path_or_fileobj=p) for p in batch]
        if commit(ops, f"ink-detection files {i}..{i + len(batch)}"):
            with open(DONE_F, "a") as f: f.write("".join(os.path.relpath(p, R) + "\n" for p in batch))
            n_f += len(batch)
    log(f"ink-detection files: +{n_f}, total {len(donef) + n_f}")
    finished = os.path.exists(f"{W}/infer/progress.log") and "ALL DONE" in open(f"{W}/infer/progress.log").read()
    if finished and not pending[n_new:] and not files[n_f:]:
        remote = api.list_repo_files(REPO, repo_type="dataset")
        n_tar = sum(1 for f in remote if f.endswith("surface-volumes.tar")); n_rec = sum(1 for f in remote if f.endswith("ink-detection/infer.json"))
        n_local_rec = len(glob.glob(f"{R}/*/*/ink-detection/infer.json")); n_local_ok = len(readset(DONE))
        log(f"FINAL check: tars remote {n_tar} / local ok {n_local_ok}; receipts remote {n_rec} / local {n_local_rec}")
        if n_tar >= n_local_ok and n_rec >= n_local_rec:
            log("verified, stopping pod"); subprocess.run(["runpodctl", "stop", "pod", os.environ.get("RUNPOD_POD_ID", "qeg3surfkcuqin")]); sys.exit(0)
    time.sleep(600)
