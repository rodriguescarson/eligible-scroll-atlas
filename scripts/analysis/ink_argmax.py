# ink_argmax.py: which meshes actually hold the top ink S1 values, at the pre-registered variant. Verifies the claim that the
# known false positive is the population maximum.
import glob, json
rows = []
for p in glob.glob("/workspace/screens_all/screens_all/*/*/ink-detection/screens_all.json"):
    try: d = json.load(open(p))
    except Exception: continue
    v = d.get("variants", {}).get("0.627")
    if not v: continue
    rows.append((v.get("S1", 0.0), f"{d['scroll']}/{d['mesh']}", v.get("S1_reverse", 0.0), bool(v.get("pass")), bool(v.get("pass_v2"))))
rows.sort(reverse=True)
print("meshes:", len(rows))
print("top 8 by ink S1 at variant 0.627:")
for s1, m, rev, p1, p2 in rows[:8]:
    print("  %-26s S1 %.4f  rev %.4f  pass %s  v2 %s" % (m, s1, rev, p1, p2))
print("passers in the whole population:", [m for _, m, _, p1, _ in rows if p1])
