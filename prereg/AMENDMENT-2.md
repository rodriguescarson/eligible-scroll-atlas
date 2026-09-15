# Amendment 2: the screens ran on the wrong probability scale, and Amendment 1's explanation is withdrawn

Filed 2026-09-15, about 17:35 UTC. State at filing: PHerc0800 (95 meshes) had been scored with the v1 code and its maps
were public; a rescore of PHerc0800 on the corrected scale had been started (17:18 UTC) and its output had not been opened;
the other 245 meshes had not been scored under any version. `PREREG.md` (tag `prereg-v1`) and `AMENDMENT-1.md` (tag
`prereg-v2`) are left unchanged.

## What was wrong

1. **Scale.** `PREREG.md` adopts TAUIL's thresholds "unchanged". TAUIL's code
   ([corpus-ink-survey @ 6e7c66b](https://github.com/TAUIL-Abd-Elilah/corpus-ink-survey/blob/6e7c66b/scripts/corpus_survey.py),
   lines 64-80) first rescales each uint8 map as `clip((p/255 - 0.25)/0.5, 0, 1)`, the ink_9um model card's display
   scale (the models train with BCE label smoothing, so confident no-ink sits near 0.25), then counts pixels above 0.75.
   That is uint8 >= 160. `scripts/screens.py` counted raw `p/255 >= 0.75`, uint8 >= 192, a stricter cut than the one
   pre-registered.
2. **Amendment 1's mechanism.** Amendment 1 put the control's S4 failure down to the unanimous minimum over two seeds
   fragmenting strokes. On the pre-registered scale the same three maps pass S4 at 0.691 (table below). That explanation
   is withdrawn: the failure came from the scale.
3. **TAUIL's checkpoints.** Amendment 1 described them as "4+ checkpoints along one training trajectory". His code uses
   hybrid_3d2d seed42 steps 030000 and 075000 and seed43 steps 030000 and 075000, two seeds and two steps. The code
   applies a coverage and confidence-ratio filter (`vs_control < 3.0 or conf_ratio < 3.2`); row periodicity and stroke
   scale were applied by hand to his worked false positive.
4. **The positive control is training data.** PHerc0139 w043 is in the ink_9um training labels
   (`ink_9um/labels/aligned-scrollprizeorg-21slices/pherc0139-w043`). Both controls therefore measure the models on
   papyrus they were fitted to and overstate sensitivity on unseen scrolls.

## The control on both scales (same three forward maps, same valid mask)

| | raw >= 0.75 (v1 as implemented) | rescaled > 0.75, uint8 >= 160 (as pre-registered) |
|---|---:|---:|
| S1, unanimous minimum | 0.0120 | 0.0549 |
| S1, reverse | 0.0002 | 0.0056 |
| S3 row period, prominence | 4.79 mm, 10.6x | 4.79 mm, 15.2x |
| S4 unanimous (mass in 0.3-2 mm2 components) | 0.491, fail | **0.691, pass** |
| S4 per file | 0.599 / 0.588 / 0.679 | 0.621 / 0.587 / 0.571 |
| all four screens | fail (S4) | **pass** |

Numbers: `control/threshold_scale.json`, produced by `scripts/screens.py` with `SCREEN_THR` set to 0.75 and 0.627.

## What is reported from here (fixed before any further score is read)

* **Primary:** `PREREG.md` as written, on TAUIL's scale (`SCREEN_THR=0.627`, uint8 >= 160). Control 1 passes all four
  screens. Control 2 (the planted window) is re-evaluated on this scale and reported whichever way it goes; the instrument
  condition is met only if it is flagged. R uses the control's S1 on this scale, 0.0549.
* **Also reported for every mesh:** raw >= 0.75 (v1 as implemented) and Amendment 1's per-file S4, on both scales, so
  every mesh carries four pass flags.
* **Out-of-training positive control:** PHerc0139 w042 (`20260206000000-w042_2026020613`, native 9.362 um surface volume,
  in neither ink_9um label list) is inferred with the identical recipe and scored on both scales before any sensitivity
  figure is published.
* **Publication:** maps are published scroll by scroll only after all four variants are scored; a mesh passing any
  variant is held for the Scroll Prize team (`PREREG.md`, "Outcomes").
