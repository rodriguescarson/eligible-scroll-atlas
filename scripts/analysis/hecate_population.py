# hecate_population.py <stats.jsonl>... : population summary of the Hecate 9.6 um pass over the eligible meshes.
# Merges per-mesh stats from every pod, reports the distribution of forward and reverse bright fractions and the
# forward/reverse ratio, and places the two held candidates in that distribution.
import json, sys
CAND = {  # measured separately in h96/cand, not part of the population files
    "PHerc0813/z13088_w040": None,  # filled from the dossier at run time if passed as name=fwd05,fwd075,rev05,rev075
    "PHerc0358/z11280_w020": (0.0877, 0.0495, 0.0439, 0.0090),
}
rows, files = {}, []
for a in sys.argv[1:]:
    if "=" in a:
        n, v = a.split("=", 1); CAND[n] = tuple(float(x) for x in v.split(",")); continue
    files.append(a)
    for line in open(a):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        f, v = r.get("fwd"), r.get("rev")
        if isinstance(f, dict) and isinstance(v, dict) and "ge_0.5" in f and "ge_0.5" in v:
            rows[r["mesh"]] = (f["ge_0.5"], f["ge_0.75"], v["ge_0.5"], v["ge_0.75"], r.get("valid_px", 0), bool(r.get("retry")))
print("files", len(files), "| meshes with both maps", len(rows), "| retried", sum(1 for x in rows.values() if x[5]))
def q(vals, p):
    s = sorted(vals); i = min(len(s) - 1, int(p * len(s)))
    return s[i]
def line(name, vals):
    print("  %-14s median %.4f  p90 %.4f  p99 %.4f  max %.4f" % (name, q(vals, .5), q(vals, .9), q(vals, .99), max(vals)))
if rows:
    f05 = [x[0] for x in rows.values()]; f075 = [x[1] for x in rows.values()]
    r05 = [x[2] for x in rows.values()]; r075 = [x[3] for x in rows.values()]
    ratio = [(x[1] + 1e-4) / (x[3] + 1e-4) for x in rows.values()]
    print("population:")
    for n, v in (("fwd >=0.5", f05), ("fwd >=0.75", f075), ("rev >=0.5", r05), ("rev >=0.75", r075), ("fwd/rev @0.75", ratio)): line(n, v)
    print("  meshes with fwd >= rev at 0.75: %d of %d" % (sum(1 for x in rows.values() if x[1] >= x[3]), len(rows)))
    top = sorted(rows.items(), key=lambda kv: -kv[1][1])[:10]
    print("top 10 by fwd >=0.75:")
    for k, v in top: print("   %-28s fwd %.4f  rev %.4f  ratio %.1f" % (k, v[1], v[3], (v[1] + 1e-4) / (v[3] + 1e-4)))
    for name, c in CAND.items():
        if not c: continue
        pct = lambda val, vals: 100.0 * sum(1 for x in vals if x <= val) / len(vals)
        print("candidate %-28s fwd>=0.75 %.4f (%.1f pct of population), ratio %.1f (%.1f pct), above population max: %s"
              % (name, c[1], pct(c[1], f075), (c[1] + 1e-4) / (c[3] + 1e-4), pct((c[1] + 1e-4) / (c[3] + 1e-4), ratio), c[1] > max(f075)))
