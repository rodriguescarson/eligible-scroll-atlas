# cross_pop.py: population-level agreement between Hecate 9.6 um and the pre-registered ink_9um screens.
# Joins every mesh scored by Hecate to its screens_all.json (variant 0.627, the TAUIL scale) and asks whether the two models
# rank surfaces the same way, rather than comparing a handful of top meshes.
import json, math, glob, os
from huggingface_hub import snapshot_download
R = "rodriguescarson/eligible-scroll-atlas-held"
TOK = open("/workspace/atlas/.hf_token").read().strip() if os.path.exists("/workspace/atlas/.hf_token") else None
hec = {}
import sys
STATS = [a for a in sys.argv[1:] if a.endswith((".jsonl",))] or ["/tmp/hecate_all.jsonl"]
SCREENS = next((a for a in sys.argv[1:] if not a.endswith(".jsonl")), "/workspace/screens_all/screens_all")
for line in (l for f in STATS for l in open(f)):
    line = line.strip()
    if not line: continue
    try: r = json.loads(line)
    except Exception: continue
    f, v = r.get("fwd"), r.get("rev")
    if isinstance(f, dict) and isinstance(v, dict) and "ge_0.75" in f:
        hec[r["mesh"]] = (f["ge_0.75"], v["ge_0.75"])
print("hecate meshes:", len(hec))
if os.path.isdir(SCREENS):
    files = glob.glob(f"{SCREENS}/*/*/ink-detection/screens_all.json")
else:
    d = snapshot_download(R, repo_type="dataset", token=TOK, local_dir="/workspace/screens_all",
                          allow_patterns=["screens_all/*/*/ink-detection/screens_all.json"])
    files = glob.glob(f"{d}/screens_all/*/*/ink-detection/screens_all.json")
print("screens files:", len(files))
ink = {}
for p in files:
    try: j = json.load(open(p))
    except Exception: continue
    v = j.get("variants", {}).get("0.627")
    if not v: continue
    ink[f"{j['scroll']}/{j['mesh']}"] = (v.get("S1", 0.0), v.get("S1_reverse", 0.0), bool(v.get("pass")), bool(v.get("pass_v2")))
print("ink meshes:", len(ink))
both = sorted(set(hec) & set(ink))
print("joined:", len(both))
def ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i]); r = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]: j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1): r[order[k]] = avg
        i = j + 1
    return r
def pearson(a, b):
    n = len(a); ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0: return float("nan")
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)
hf = [hec[m][0] for m in both]; hr = [hec[m][1] for m in both]
hratio = [math.log((hec[m][0] + 1e-4) / (hec[m][1] + 1e-4)) for m in both]
i_s1 = [ink[m][0] for m in both]; i_diff = [ink[m][0] - ink[m][1] for m in both]
print("\nSpearman correlations over %d meshes:" % len(both))
print("  hecate fwd>=0.75      vs ink S1            %.3f" % pearson(ranks(hf), ranks(i_s1)))
print("  hecate fwd>=0.75      vs ink S1 fwd-rev    %.3f" % pearson(ranks(hf), ranks(i_diff)))
print("  hecate log fwd/rev    vs ink S1 fwd-rev    %.3f" % pearson(ranks(hratio), ranks(i_diff)))
for N in (10, 20, 50):
    th = set(sorted(both, key=lambda m: -hec[m][0])[:N]); ti = set(sorted(both, key=lambda m: -ink[m][0])[:N])
    exp = N * N / len(both)
    print("  top %-3d sets overlap %2d of %d (expected %.1f by chance)" % (N, len(th & ti), N, exp))
p = [m for m in both if ink[m][2]]
print("\nink-rule passers among joined meshes: %d" % len(p))
for m in p:
    r = sorted(both, key=lambda x: -hec[x][0]).index(m) + 1
    print("   %-26s hecate rank %3d/%d  fwd %.4f rev %.4f | ink S1 %.4f rev %.4f" % (m, r, len(both), hec[m][0], hec[m][1], ink[m][0], ink[m][1]))
np_ = [m for m in both if not ink[m][2]]
mean = lambda v: sum(v) / len(v) if v else float("nan")
print("\nmean hecate fwd>=0.75: ink-pass %.4f (n %d) vs ink-fail %.4f (n %d)" % (mean([hec[m][0] for m in p]), len(p), mean([hec[m][0] for m in np_]), len(np_)))
