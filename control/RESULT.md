# Controls: result (15 Sep 2026)

Both controls ran before any eligible mesh was scored. Files in this directory are copied unchanged from the pod
(`/workspace/atlas/control`, `/workspace/atlas/planted`); the raw maps (uint8 TIFF, 6120×8120) are in the HF renders
repo alongside the eligible meshes.

## Control 1: PHerc0139 w043, the team's published native surface volume

Copied locally from the bucket (28 layers, 6120×8120, 1.4 GB), then the recipe fixed in `prereg/PREREG.md`:
`vesuvius.ink_detection.inference.infer` at villa `4b3c728`, `--overlap 0.5 --blend-mode hann --direction both
--batch-size 16 --no-compile`, three checkpoint files, both layer directions. Timings on one A40 while six renders
shared the CPU: 1100 s, 1077 s, 1056 s per file (both directions).

| | seed43/060000 | seed42/020000 | soup42 (10k/20k/30k) | unanimous minimum |
|---|---:|---:|---:|---:|
| S1 forward (frac ≥ 0.75 over valid) | 0.0331 | 0.0277 | 0.0346 | **0.0120** |
| S1 reverse | 0.0050 | 0.0020 | | **0.0002** |
| S4 mass in 0.3–2 mm² components | 0.588 | 0.599 | 0.679 | **0.491** |

Unanimous minimum: S3 row period 4.79 mm at 10.6× prominence (pass); S4 0.491 (**fail** under v1's "majority" rule
by 0.9 points; 8-connectivity, 0.480 with 4-connectivity; 0.509 of the mass sits in components under 0.3 mm², none
above 2 mm²). Pearson r between the seed43 and seed42 forward maps over valid pixels: 0.636. `screens.json` has the
full record. Previews (`*-ds8.jpg`) are 8× block means displayed as (p − 0.25)/0.5; the forward maps show text rows
across the sheet, the reverse maps show almost nothing.

Verdict: under `PREREG.md` (v1) the instrument fails one screen on the known-ink control, so **no ranking is
published under v1**. `prereg/AMENDMENT-1.md` (tag `prereg-v2`, filed before any eligible mesh was scored) records
this, explains it (the intersection of two seeds' maps fragments strokes below 0.3 mm²), and defines v2 (S4 per
file), under which the control passes.

## Control 2: a planted 4 cm² window of w043 inside an eligible render

`scripts/plant_control.py`: the 1764×2587 px window of the w043 render holding the most p_min ≥ 0.75 mass
(control box y=3853, x=2091) spliced into `PHerc0813/z6496_w040` (2020×6060 px, a median-S1 mesh in pscamillo's
maps) at layers 1–29 of 31, target box y=50, x=2190; then the identical recipe. `planted/plant.json`,
`planted/plant_eval.json`.

| | value |
|---|---:|
| S1 inside the window | 0.0345 |
| S1 outside the window | 0.00064 |
| ratio inside / outside | **54×** |
| share of the spliced volume's hit mass inside the window | **0.991** |
| window share of the valid area | 0.677 |
| screens on the spliced volume (unanimous minimum) | S1 0.0236, reverse 0.0004, S3 4.22 mm at 4.3×, S4 0.636; pass v1 and v2 |

Verdict: **flagged**. Caveat: the window is 68 % of that target's valid area; a second run into the largest
9.362 µm canvas (`PHerc0813/z4704_w100`, 2420×12940 px) is in progress and will be appended here whichever way it goes.

## Instrument verdict

* v1 (primary): fails, on control 1's S4 alone; renders, maps and every per-mesh screen score are published, no ranking.
* v2 (secondary): passes both controls.
