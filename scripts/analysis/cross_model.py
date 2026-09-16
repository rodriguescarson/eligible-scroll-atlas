# cross_model.py: for the Hecate top 10, what did the pre-registered ink_9um screens say?
import json
from huggingface_hub import hf_hub_download
R = "rodriguescarson/eligible-scroll-atlas-held"
TOK = open("/workspace/atlas/.hf_token").read().strip()
TOP = ["PHerc0813/z13088_w040", "PHerc0813/z12496_w060", "PHerc0211/z11520_w020", "PHerc0211/z7920_w020",
       "PHerc0800/z9872_w020", "PHerc0211/z9120_w020", "PHerc0813/z11904_w060", "PHerc0211/z9712_w080",
       "PHerc0813/z13696_w040", "PHerc0813/z5888_w020"]
first = True
for m in TOP:
    path = f"screens_all/{m}/ink-detection/screens_all.json"
    try:
        p = hf_hub_download(R, path, repo_type="dataset", token=TOK, local_dir="/tmp/screens")
        d = json.load(open(p))
    except Exception as e:
        print(f"{m}: not available ({str(e)[:60]})"); continue
    if first:
        print("STRUCTURE:", json.dumps(d, default=str)[:600]); first = False
    def dig(obj, *names):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in names and not isinstance(v, (dict, list)): yield k, v
                else: yield from dig(v, *names)
        elif isinstance(obj, list):
            for v in obj: yield from dig(v, *names)
    vals = {}
    for k, v in dig(d, "S1", "s1", "pass", "pass_v2", "S3", "S4", "thr", "threshold"):
        vals.setdefault(k, []).append(v)
    print(f"{m}: " + " ".join(f"{k}={v[:3]}" for k, v in sorted(vals.items()))[:220])
