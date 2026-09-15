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
# HOLD_MAPS: while this file exists no ink-detection file is published (PREREG: a mesh that passes the screens
# is not shown publicly). If inference has finished and the hold is still in place 3 h later, everything is
# uploaded to a PRIVATE repo instead and the pod stops, so the only copy never sits on an idle pod.
DONE_H = f"{ST}/uploaded_held.txt"
HOLD = f"{ST}/HOLD_MAPS"; HELD_REPO = os.environ.get("HF_HELD_REPO", "rodriguescarson/eligible-scroll-atlas-held")
def log(m): open(LOG, "a").write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {m}\n")
def readset(p): return set(open(p).read().split()) if os.path.exists(p) else set()
api = HfApi(token=open(f"{W}/.hf_token").read().strip())

def commit(ops, msg, repo=None):
    """create_commit with rate-limit handling; returns True on success."""
    for attempt in range(6):
        try:
            api.create_commit(repo_id=repo or REPO, repo_type="dataset", operations=ops, commit_message=msg); return True
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
    finished = os.path.exists(f"{W}/infer/progress.log") and "ALL DONE" in open(f"{W}/infer/progress.log").read()
    donef = readset(DONE_F); doneh = readset(DONE_H)
    cands = [p for p in glob.glob(f"{R}/*/*/ink-detection/*") if ALLOW.search(p)]
    cleared = lambda p: os.path.exists(os.path.join(os.path.dirname(p), ".cleared"))
    held = lambda p: os.path.exists(os.path.join(os.path.dirname(p), ".held"))
    # HOLD_MAPS: only meshes screened clean under all four variants go public; a mesh passing any variant goes private
    files = [p for p in cands if (cleared(p) or not os.path.exists(HOLD)) and os.path.relpath(p, R) not in donef]
    hfiles = [p for p in cands if held(p) and os.path.relpath(p, R) not in doneh]
    if os.path.exists(f"{R}/README.md") and "README.md" not in donef: files.append(f"{R}/README.md")
    n_f = 0
    for i in range(0, len(files), 300):
        batch = files[i:i + 300]
        ops = [CommitOperationAdd(path_in_repo=os.path.relpath(p, R), path_or_fileobj=p) for p in batch]
        if commit(ops, f"ink-detection files (screened) {i}..{i + len(batch)}"):
            with open(DONE_F, "a") as f: f.write("".join(os.path.relpath(p, R) + "\n" for p in batch))
            n_f += len(batch)
    n_h = 0
    if hfiles:
        api.create_repo(HELD_REPO, repo_type="dataset", private=True, exist_ok=True)
        for i in range(0, len(hfiles), 300):
            batch = hfiles[i:i + 300]
            ops = [CommitOperationAdd(path_in_repo=os.path.relpath(p, R), path_or_fileobj=p) for p in batch]
            if commit(ops, f"held ink-detection files {i}..{i + len(batch)}", repo=HELD_REPO):
                with open(DONE_H, "a") as f: f.write("".join(os.path.relpath(p, R) + "\n" for p in batch))
                n_h += len(batch)
        log(f"HELD (private) files: +{n_h}")
    log(f"ink-detection files: +{n_f}, total {len(donef) + n_f}")
    receipts = glob.glob(f"{R}/*/*/ink-detection/infer.json")
    unmarked = [j for j in receipts if not (os.path.exists(os.path.join(os.path.dirname(j), ".cleared")) or os.path.exists(os.path.join(os.path.dirname(j), ".held")))]
    fa = f"{ST}/finished_at"
    if finished and not os.path.exists(fa): open(fa, "w").write(str(time.time()))
    stale = finished and time.time() - float(open(fa).read()) > 3 * 3600
    if finished and (not unmarked or stale) and not pending[n_new:] and not files[n_f:] and not hfiles[n_h:]:
        if unmarked:
            log(f"{len(unmarked)} receipts never screened 3 h after inference ended: uploading their files privately")
            api.create_repo(HELD_REPO, repo_type="dataset", private=True, exist_ok=True)
            api.upload_large_folder(repo_id=HELD_REPO, folder_path=R, repo_type="dataset", num_workers=4, allow_patterns=[os.path.relpath(os.path.dirname(j), R) + "/*" for j in unmarked])
        # analysis, controls, logs and per-mesh screen scores: private backup before the pod goes away
        api.create_repo(HELD_REPO, repo_type="dataset", private=True, exist_ok=True)
        for sub in ("analysis", "control", "planted", "planted2", "hecate_test", "orient", "log", "infer", "render", "upload"):
            if os.path.isdir(f"{W}/{sub}"):
                api.upload_large_folder(repo_id=HELD_REPO, folder_path=f"{W}/{sub}", repo_type="dataset", num_workers=4, ignore_patterns=["*.zarr/*", "*.tar"])
        ops = [CommitOperationAdd(path_in_repo=f"screens_all/{os.path.relpath(p, R)}", path_or_fileobj=p) for p in glob.glob(f"{R}/*/*/ink-detection/screens_all.json")]
        for i in range(0, len(ops), 300): commit(ops[i:i + 300], f"per-mesh screen scores {i}", repo=HELD_REPO)
        remote = api.list_repo_files(REPO, repo_type="dataset"); hremote = api.list_repo_files(HELD_REPO, repo_type="dataset")
        n_tar = sum(1 for f in remote if f.endswith("surface-volumes.tar")); n_pub = sum(1 for f in remote if f.endswith("ink-detection/infer.json"))
        n_priv = sum(1 for f in hremote if f.endswith("ink-detection/infer.json")); n_sc = sum(1 for f in hremote if f.endswith("screens_all.json"))
        n_clear = sum(1 for j in receipts if os.path.exists(os.path.join(os.path.dirname(j), ".cleared")))
        log(f"FINAL check: tars {n_tar}/{len(readset(DONE))}; public receipts {n_pub}/{n_clear}; private receipts {n_priv}/{len(receipts) - n_clear}; screens {n_sc}/{len(receipts) - len(unmarked)}")
        if n_tar >= len(readset(DONE)) and n_pub >= n_clear and n_priv >= len(receipts) - n_clear and n_sc >= len(receipts) - len(unmarked):
            log("verified, removing pod"); r = subprocess.run(["runpodctl", "remove", "pod", os.environ.get("RUNPOD_POD_ID", "qeg3surfkcuqin")])
            if r.returncode != 0: subprocess.run(["runpodctl", "stop", "pod", os.environ.get("RUNPOD_POD_ID", "qeg3surfkcuqin")])
            sys.exit(0)
    time.sleep(600)
