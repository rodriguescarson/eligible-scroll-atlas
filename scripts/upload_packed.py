"""upload_packed.py: incremental upload of the atlas to the public HF dataset repo, within the Hub's file-count limits
(<100k files per repo; the raw zarr layout is 580k chunk files). Per mesh: <scroll>/<mesh>/surface-volumes.tar (the zarr
plus render.json; untar inside <scroll>/<mesh>/ to get the team's layout), uploaded as soon as the render exists. The
ink-detection outputs (maps, previews, mask, infer.json) are uploaded loose with upload_large_folder, screens.json and
plant_eval.json excluded. Loops every 10 min; after infer_all/v2 writes ALL DONE and everything is verified remote, it
stops the pod. State in /workspace/atlas/upload/uploaded.txt."""
import glob, json, os, subprocess, sys, time
from huggingface_hub import HfApi
W = "/workspace/atlas"; R = f"{W}/renders"; ST = f"{W}/upload"; os.makedirs(f"{ST}/stage", exist_ok=True)
REPO = os.environ.get("HF_REPO", "rodriguescarson/eligible-scroll-atlas-renders")
LOG = f"{W}/log/upload.log"; DONE = f"{ST}/uploaded.txt"
def log(m):
    open(LOG, "a").write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {m}\n")
api = HfApi(token=open(f"{W}/.hf_token").read().strip())
api.create_repo(REPO, repo_type="dataset", exist_ok=True)
log(f"repo ready {REPO}")
queue = [l.split() for l in open(f"{W}/render/queue.txt")]
while True:
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()
    n_new = 0
    for s, m, *_ in queue:
        key = f"{s}/{m}"; d = f"{R}/{s}/{m}"
        if key in done or not os.path.exists(f"{d}/render.json"): continue
        if '"rc": 0' not in open(f"{d}/render.json").read(): continue
        tar = f"{ST}/stage/{s}_{m}.tar"
        try:
            subprocess.run(["tar", "-cf", tar, "-C", d, "surface-volumes", "render.json"], check=True)
            api.upload_file(path_or_fileobj=tar, path_in_repo=f"{s}/{m}/surface-volumes.tar", repo_id=REPO, repo_type="dataset",
                            commit_message=f"render {key}")
            open(DONE, "a").write(key + "\n"); n_new += 1
        except Exception as e:
            log(f"FAIL {key}: {str(e)[:200]}")
        finally:
            if os.path.exists(tar): os.remove(tar)
    log(f"render tars: +{n_new}, total {len(done) + n_new}")
    try:
        api.upload_large_folder(repo_id=REPO, folder_path=R, repo_type="dataset", num_workers=4,
                                allow_patterns=["README.md", "*/ink-detection/*"], ignore_patterns=["*/screens.json", "*/plant_eval.json", "*/infer_*.out", "*/prep.err"])
        log("ink-detection folder pass ok")
    except Exception as e:
        log(f"ink-detection folder pass FAILED: {str(e)[:300]}")
    finished = os.path.exists(f"{W}/infer/progress.log") and "ALL DONE" in open(f"{W}/infer/progress.log").read()
    if finished:
        remote = api.list_repo_files(REPO, repo_type="dataset")
        n_tar = sum(1 for f in remote if f.endswith("surface-volumes.tar")); n_rec = sum(1 for f in remote if f.endswith("ink-detection/infer.json"))
        n_local_rec = len(glob.glob(f"{R}/*/*/ink-detection/infer.json")); n_local_ok = sum(1 for s, m, *_ in queue if '"rc": 0' in open(f"{R}/{s}/{m}/render.json").read())
        log(f"FINAL check: tars remote {n_tar} / local ok {n_local_ok}; receipts remote {n_rec} / local {n_local_rec}")
        if n_tar >= n_local_ok and n_rec >= n_local_rec:
            log("verified, stopping pod"); subprocess.run(["runpodctl", "stop", "pod", os.environ.get("RUNPOD_POD_ID", "qeg3surfkcuqin")]); sys.exit(0)
    time.sleep(600)
