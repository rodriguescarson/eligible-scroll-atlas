# Amendment 1 to PREREG.md: the positive control fails S4 under the v1 wording

Filed 2026-09-15 14:10 UTC, after the three-file inference on the positive control (PHerc0139 w043) and
before any eligible mesh was scored. At filing time `infer_all.sh` had started writing maps for eligible
meshes (first mesh 14:05 UTC); `rank.py`/`screens.py` had not been run on any of them. The original
`PREREG.md` (sha256 `1efef1423caffa73d682a85e3ed083762b3bc9dd8babe33b76cb2792760fc20d`, tag `prereg-v1`)
is unchanged and remains the primary analysis.

## Control result under the v1 wording

Three forward maps (seed43/060000, seed42/020000, soup42 of steps 10k/20k/30k) and three reverse maps,
`--overlap 0.5 --blend-mode hann --batch-size 16 --no-compile`, valid = nonzero at level 0 eroded 64 px
(41,578,614 px, 83.7 % of the canvas), voxel 9.362 µm. `control/screens.json` on the pod; numbers:

| screen | value | v1 rule | result |
|---|---|---|---|
| S1 coverage, p_min ≥ 0.75 | **0.01200** (per file 0.0277 / 0.0331 / 0.0346) | reported | |
| S1 reverse | 0.00024 (forward − reverse = +0.01176, 49×) | forward > reverse | pass |
| S2 ratio | 1 by definition | within 5× | pass |
| S3 row periodicity | 4.79 mm, prominence **10.6×** | 4–5 mm, > 1.2× | pass |
| S4 stroke scale | mass in 0.3–2 mm² components = **0.491** (8-conn; 0.480 with 4-conn); 0.509 in components < 0.3 mm²; 0.000 above 2 mm² | majority of S1 mass | **fail** |

Per-file S4 on each map's own ≥ 0.75 mask: 0.599 / 0.588 / 0.679 (all pass). Pearson r between the
seed43 and seed42 forward maps over valid pixels: 0.636.

Verdict under v1: the instrument fails one of the four screens on the known-ink control, by 0.9
percentage points. Per PREREG "Outcomes": renders and maps are published, **no ranking is published
under v1**, and this is the reason.

## Why it fails

The unanimous minimum over three files from two seeds (r = 0.64 between seeds) keeps only the pixels all
three agree on, which cuts letter strokes into fragments: half of the surviving mass sits in specks
smaller than 0.3 mm² (median component 8.8e-5 mm²). Each single map keeps whole strokes (per-file mass
in band 0.59–0.68). TAUIL's control value (0.03694, unanimous over 4+ checkpoints along one training
trajectory) is consistent with this: checkpoints along one run are far more correlated than two seeds,
so their minimum fragments less. The failure is a property of the intersection, not evidence that the
model misses the ink on w043.

## v2 (secondary analysis), fixed before scoring

Everything in PREREG.md stands except S4, which is evaluated per file: each of the three forward maps'
own ≥ 0.75 mask must have the majority of its mass in connected components of 0.3–2 mm². S1, S2, S3, the
reverse asymmetry and the ranking statistic R keep the unanimous minimum. The control passes v2.

Both flags are reported for every mesh (`pass` = v1, `pass_v2` = v2, `ranked.csv`). The v1 outcome ("no
ranking") is the primary result; any list ordered by R is labelled a v2 secondary result. A mesh that
passes v2 is treated exactly as the PREREG "Outcomes" section treats a v1 pass (scores only in public,
images to the team).

## Implementation details that v1 left unspecified, fixed here

* connectivity: 8 (3×3 structuring element); areas in mm² at the scroll's voxel pitch;
* valid mask: `max over layers > 0`, `scipy.ndimage.binary_erosion` 64 iterations, 3×3, border 0;
* S3 profile: per image row, hit pixels / valid pixels, rows with no valid pixels dropped, detrended by a
  10 mm running mean, Welch PSD (`nperseg` ≤ 4096); background = median PSD over 2–10 mm excluding
  ±10 % around the peak; prominence = peak / background;
* S2 window: 0.2 ≤ S1(mesh)/S1(control) ≤ 5 ("within 5×");
* code: `scripts/screens.py` at the commit that carries this file.

## Planted control (control 2)

Running at filing time: a 4 cm² window of the w043 render, chosen as the h×w box with the most p_min ≥
0.75 mass, spliced into `PHerc0813/z6496_w040` (a median-S1 mesh in pscamillo's maps, 2020×6060 px)
at layers 1–29 of 31; inferred with the identical recipe. "Flagged" = the window holds more than half
of the spliced volume's p_min ≥ 0.75 mass and its S1 is more than 5× the S1 outside it
(`scripts/plant_eval.py`). Result to be appended to `control/` unchanged whichever way it goes.
