# backup_run.py <run_dir>: verified upload of one fit run to spiralfit/<scroll>/<run>/ in the private dataset.
import glob, os, sys, time
from huggingface_hub import HfApi
run = sys.argv[1].rstrip("/") + "/"; R = "rodriguescarson/eligible-scroll-atlas-held"
api = HfApi(token=open("/workspace/fit/.hf_token").read().strip())
prefix = "spiralfit/" + run.rstrip("/").split("/")[-2] + "/" + os.path.basename(run.rstrip("/"))
t0 = time.time()
local = {os.path.relpath(f, run) for f in glob.glob(run + "**/*", recursive=True) if os.path.isfile(f) and "/.cache/" not in f and ".zarr/" not in f}
print("local files", len(local), "listed in %.1fs" % (time.time() - t0), flush=True)
listing = lambda: {f[len(prefix) + 1:] for f in api.list_repo_files(R, repo_type="dataset") if f.startswith(prefix + "/")}
t0 = time.time(); todo = sorted(local - listing()); print("missing before", len(todo), "remote listed in %.1fs" % (time.time() - t0), flush=True)
for i in range(0, len(todo), 500):
    t0 = time.time()
    api.upload_folder(repo_id=R, repo_type="dataset", folder_path=run, path_in_repo=prefix, allow_patterns=todo[i:i + 500], commit_message=f"{prefix} batch {i}")
    print("batch", i, "of", len(todo), "in %.1fs" % (time.time() - t0), flush=True)
miss = sorted(local - listing()); print("missing after", len(miss), miss[:3], flush=True)
