"""rank.py: run the four pre-registered screens on every inferred mesh, join the gate table, write ranked.csv + summary.json.
usage: rank.py --renders /workspace/atlas/renders --gates data/gates.csv --control-s1 <S1 of the w043 control> --out atlas/
Ranking statistic R = S1(mesh)/S1(control), forward direction, ties by the mean over the three files (PREREG "Ranking").
Meshes that pass all four screens are listed with scores only; their images are not placed in the public atlas."""
import argparse, csv, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screens import screens

ap = argparse.ArgumentParser(); ap.add_argument("--renders", required=True); ap.add_argument("--gates", required=True)
ap.add_argument("--control-s1", type=float, required=True); ap.add_argument("--out", required=True); ap.add_argument("--force", action="store_true")
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
gates = {r["mesh"]: r for r in csv.DictReader(open(a.gates))}
rows = []
for side in sorted(glob.glob(os.path.join(a.renders, "*", "*", "ink-detection", "infer.json"))):
    d = os.path.dirname(side); mesh = os.path.basename(os.path.dirname(d)); scroll = os.path.basename(os.path.dirname(os.path.dirname(d)))
    key = f"{scroll}_{mesh}"; g = gates.get(key, {}); um = 8.64 if scroll in ("PHerc0800", "PHerc0268") else 9.362
    sj = os.path.join(d, os.environ.get("SCREENS_JSON", "screens.json"))
    if os.path.exists(sj) and not a.force: r = json.load(open(sj))
    else:
        try: r = screens(d, um, a.control_s1, os.path.join(d, "valid_mask.tif"))
        except Exception as e: print("SKIP", key, e, file=sys.stderr); continue
        json.dump(r, open(sj, "w"), indent=1)
    rows.append({"scroll": scroll, "mesh": mesh, "area_cm2": g.get("area_cm2", ""), "verdict": g.get("verdict", ""),
                 "aligned_lt30": g.get("aligned_lt30", ""), "reprova": g.get("reprova", ""), "median_angle_deg": g.get("median_angle_deg", ""),
                 "valid_px": r["valid_px"], "S1": r["S1"], "S1_mean3": r["S1_mean_over_files"], "S1_reverse": r.get("S1_reverse", ""),
                 "S2_ratio": r.get("S2_ratio", ""), "S3_period_mm": r["S3"]["period_mm"], "S3_prominence": r["S3"]["prominence"],
                 "S4_mass_in_band": r["S4"]["mass_in_band"], "S4_components": r["S4"]["components"],
                 "S4_v2_min_mass_in_band": min(x["mass_in_band"] for x in r.get("S4_per_file", [r["S4"]])), "pass": r["pass"], "pass_v2": r.get("pass_v2", ""), "R": r.get("R", "")})
    print(key, f"S1={r['S1']:.5f} rev={r.get('S1_reverse', 0):.5f} R={r.get('R', 0):.3f} pass={r['pass']}", flush=True)
rows.sort(key=lambda x: (-(x["R"] or 0), -(x["S1_mean3"] or 0)))
with open(os.path.join(a.out, "ranked.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
prim = [x for x in rows if x["aligned_lt30"] == "True" and x["reprova"] != "True"]; sec = [x for x in rows if x["aligned_lt30"] == "True"]
summ = {"scored": len(rows), "control_s1": a.control_s1,
        "primary_denominator_scored": len(prim), "primary_pass": sum(x["pass"] for x in prim),
        "secondary_denominator_scored": len(sec), "secondary_pass": sum(x["pass"] for x in sec), "all_pass": sum(x["pass"] for x in rows),
        "primary_pass_v2": sum(1 for x in prim if x["pass_v2"] is True), "secondary_pass_v2": sum(1 for x in sec if x["pass_v2"] is True), "all_pass_v2": sum(1 for x in rows if x["pass_v2"] is True),
        "reverse_gt_forward": sum(1 for x in rows if x["S1_reverse"] != "" and x["S1_reverse"] > x["S1"]),
        "passing_meshes": [f"{x['scroll']}/{x['mesh']}" for x in rows if x["pass"]], "passing_meshes_v2": [f"{x['scroll']}/{x['mesh']}" for x in rows if x["pass_v2"] is True],
        "top10_by_R": [(f"{x['scroll']}/{x['mesh']}", x["R"]) for x in rows[:10]]}
json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"), indent=1); print(json.dumps(summ, indent=1))
