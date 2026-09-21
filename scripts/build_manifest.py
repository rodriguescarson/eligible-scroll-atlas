#!/usr/bin/env python3
"""Build data/manifest.csv: one row per published mesh, joining the gate table to the model scores.

No network. Reads data/gates.csv and artifacts/hecate-population/cross_model_join_final.json.
"""
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASET = "https://huggingface.co/datasets/rodriguescarson/eligible-scroll-atlas-renders/resolve/main"

gates = list(csv.DictReader((ROOT / "data/gates.csv").open()))
summary = json.loads((ROOT / "artifacts/survey/population_summary.json").read_text())
held = {key for key, _ in summary["held"]}   # screen passers: imagery withheld under the pre-registration
joined = json.loads((ROOT / "artifacts/hecate-population/cross_model_join_final.json").read_text())
scores = {r["mesh"]: r for r in joined["rows"]}

ranked = sorted((r for r in scores.values() if r.get("h_fwd05") is not None),
                key=lambda r: -r["h_fwd05"])
rank = {r["mesh"]: i + 1 for i, r in enumerate(ranked)}

FIELDS = ["scroll", "mesh", "area_cm2", "eye_verdict", "alignment_deg", "aligned_lt30", "reprova",
          "valid_px", "ink_S1", "ink_S1_reverse", "ink_pass_v1", "ink_pass_v2",
          "hecate_fwd_ge05", "hecate_rev_ge05", "hecate_rank", "maps_held", "surface_volumes_tar", "ink_detection_dir"]

rows = []
for g in gates:
    key = f"{g['scroll']}/{g['mesh'].split('_', 1)[1]}"
    s = scores.get(key, {})
    rows.append({
        "scroll": g["scroll"], "mesh": g["mesh"].split("_", 1)[1],
        "area_cm2": g["area_cm2"], "eye_verdict": g["verdict"],
        "alignment_deg": g["median_angle_deg"], "aligned_lt30": g["aligned_lt30"], "reprova": g["reprova"],
        "valid_px": s.get("valid_px", ""), "ink_S1": s.get("ink_S1", ""),
        "ink_S1_reverse": s.get("ink_S1_rev", ""), "ink_pass_v1": s.get("ink_pass", ""),
        "ink_pass_v2": s.get("ink_pass_v2", ""), "hecate_fwd_ge05": s.get("h_fwd05", ""),
        "hecate_rev_ge05": s.get("h_rev05", ""), "hecate_rank": rank.get(key, ""), "maps_held": key in held,
        "surface_volumes_tar": f"{DATASET}/{g['scroll']}/{g['mesh'].split('_', 1)[1]}/surface-volumes.tar",
        "ink_detection_dir": f"{DATASET}/{g['scroll']}/{g['mesh'].split('_', 1)[1]}/ink-detection",
    })

out = ROOT / "data/manifest.csv"
with out.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
missing = [r["mesh"] for r in rows if r["hecate_rank"] == ""]
print(f"wrote {out} with {len(rows)} rows; without a Hecate score: {len(missing)}")
