# held_ranks.py <stats.jsonl>...: where the ink-screen passers sit in the Hecate distribution, and per-scroll breakdown.
import json, math, sys
from collections import defaultdict
HELD = ["PHerc0813/z13088_w040", "PHerc0813/z12496_w060", "PHerc0813/z7696_w020", "PHerc0813/z5888_w020", "PHerc0358/z11280_w020"]
NOTE = {"PHerc0813/z12496_w060": "TAUIL's known false positive"}
# a mesh first scored in the candidate run can later appear in the main pass; label by what the files actually contain
rows = {}
for a in sys.argv[1:]:
    for line in open(a):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        f, v = r.get("fwd"), r.get("rev")
        if isinstance(f, dict) and isinstance(v, dict) and "ge_0.75" in f:
            rows[r["mesh"]] = (f["ge_0.75"], v["ge_0.75"])
order = sorted(rows.items(), key=lambda kv: -kv[1][0])
rank = {k: i + 1 for i, (k, _) in enumerate(order)}
N = len(order)
print("meshes scored:", N)
print("\nheld ink-screen passers in the Hecate forward >=0.75 ranking:")
in_top10 = 0
for h in HELD:
    if h in rows:
        f, v = rows[h]; r = rank[h]
        if r <= 10: in_top10 += 1
        print("  %-26s rank %3d of %d (top %.1f%%)  fwd %.4f  rev %.4f  ratio %5.1f  %s" % (h, r, N, 100.0 * r / N, f, v, (f + 1e-4) / (v + 1e-4), NOTE.get(h, "")))
    else:
        print("  %-26s not scored in these files  %s" % (h, NOTE.get(h, "")))
scored = [h for h in HELD if h in rows]
if scored:
    K, n, k = 10, len(scored), in_top10
    p = sum(math.comb(K, i) * math.comb(N - K, n - i) / math.comb(N, n) for i in range(k, min(n, K) + 1))
    print("\n  %d of %d scored held meshes are in the top 10 of %d; probability if ranks were random: %.2g" % (k, n, N, p))
print("\nper scroll (forward >=0.75):")
by = defaultdict(list)
for m, (f, v) in rows.items(): by[m.split("/")[0]].append(f)
for s in sorted(by):
    vals = sorted(by[s]); med = vals[len(vals) // 2]
    print("  %-10s n %3d  median %.4f  max %.4f  in top 10: %d" % (s, len(vals), med, vals[-1], sum(1 for m in rows if m.split("/")[0] == s and rank[m] <= 10)))
