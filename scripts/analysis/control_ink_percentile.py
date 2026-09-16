# control_ink_percentile.py: same calibration for the ink model. Where do the known-ink controls sit in the 340-mesh
# ink_9um S1 distribution at the pre-registered variant (raw 0.627 = uint8 >= 160)?
import glob, json
from huggingface_hub import HfApi, hf_hub_download
R = "rodriguescarson/eligible-scroll-atlas-held"
TOK = open("/workspace/atlas/.hf_token").read().strip(); api = HfApi(token=TOK)
pop = []
for p in glob.glob("/workspace/screens_all/screens_all/*/*/ink-detection/screens_all.json"):
    try: v = json.load(open(p)).get("variants", {}).get("0.627")
    except Exception: continue
    if v: pop.append(v.get("S1", 0.0))
pop.sort()
pct = lambda x: 100.0 * sum(1 for y in pop if y <= x) / len(pop)
print("ink population meshes:", len(pop), "| median %.4f p90 %.4f p99 %.4f max %.4f" % (pop[len(pop)//2], pop[int(.9*len(pop))], pop[int(.99*len(pop))], pop[-1]))
fs = api.list_repo_files(R, repo_type="dataset")
cands = [f for f in fs if f.endswith(".json") and "screens" in f and (f.startswith("c96b/") or f.startswith("c96c/"))]
print("control screens files:", len(cands))
for f in sorted(cands):
    if "0.75" in f or "thr0.75" in f: continue
    try:
        p = hf_hub_download(R, f, repo_type="dataset", token=TOK, local_dir="/tmp/ctlink"); d = json.load(open(p))
    except Exception as e:
        print(" ", f, "unreadable", str(e)[:50]); continue
    v = d.get("variants", {}).get("0.627") or d
    s1, rev = v.get("S1"), v.get("S1_reverse")
    if s1 is None: print(" ", f, "keys:", sorted(v.keys())[:10]); continue
    print("  %-46s S1 %.4f rev %.4f  pass %s/%s  -> %.1f pct of the eligible-mesh ink population"
          % (f.split("/")[1] + "/" + f.split("/")[-1], s1, rev or 0.0, v.get("pass"), v.get("pass_v2"), pct(s1)))
