# export_join.py: save the per-mesh ink + Hecate join that the cross-model figures rest on, plus the mesh accounting.
import glob, json
hec, err = {}, []
for line in open("/tmp/hecate_all.jsonl"):
    line = line.strip()
    if not line: continue
    try: r = json.loads(line)
    except Exception: continue
    f, v = r.get("fwd"), r.get("rev")
    if isinstance(f, dict) and isinstance(v, dict) and "ge_0.75" in f:
        hec[r["mesh"]] = dict(h_fwd05=f["ge_0.5"], h_fwd075=f["ge_0.75"], h_rev05=v["ge_0.5"], h_rev075=v["ge_0.75"],
                              valid_px=r.get("valid_px"), retry=bool(r.get("retry")))
    else:
        err.append((r.get("mesh"), str(f)[:60] if not isinstance(f, dict) else str(v)[:60]))
ink = {}
for p in glob.glob("/workspace/screens_all/screens_all/*/*/ink-detection/screens_all.json"):
    try: j = json.load(open(p))
    except Exception: continue
    v = j.get("variants", {}).get("0.627")
    if v: ink[f"{j['scroll']}/{j['mesh']}"] = dict(ink_S1=v.get("S1"), ink_S1_rev=v.get("S1_reverse"), ink_pass=bool(v.get("pass")), ink_pass_v2=bool(v.get("pass_v2")))
rows = [dict(mesh=m, **hec[m], **ink.get(m, {})) for m in sorted(hec)]
json.dump(dict(submitted=len(hec) + len(err), usable=len(hec), error_rows=len(err),
               errors=[e[0] for e in err], ink_meshes=len(ink), joined=sum(1 for r in rows if "ink_S1" in r), rows=rows),
          open("/tmp/cross_model_join.json", "w"), indent=1)
print("submitted", len(hec) + len(err), "| usable", len(hec), "| error rows", len(err))
print("errors:", [e[0] for e in err][:12])
print("joined with ink:", sum(1 for r in rows if "ink_S1" in r))
