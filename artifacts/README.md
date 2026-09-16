# Artifacts behind the September figures

JSON only. Every figure in the September writeup is computed from a file here by a script in `scripts/analysis/`.

- `survey/population_summary.json` — the pre-registered ink survey over all 340 eligible meshes, four variant pass counts and
  their denominators.
- `hecate-population/` — the Hecate 9.6 um pass joined to those screens: per-mesh statistics (`all.jsonl`, the per-pod files),
  the joined table (`cross_model_join.json`) and the cross-model writeup.
- `hecate-chunking/patchtest/` — the pre-registered dead-tensor-release test: the change as a diff, the harness, and
  `equivalence.out`, one row per baseline/patched pair. Twelve pairs, every output sha256-identical, peak reserved memory
  unchanged to the byte in all twelve while peak allocated fell up to 33 percent. The patch is dropped; the null is the result.
- `fit-0826/`, `fit-0191/` — spiral-fit outputs: per-winding areas, the comparison against pscamillo's published meshes, the
  overlapping-window consistency test, winding spacing profiles, the radial sheet-spacing checks and the winding-count A/B.

Held back deliberately: imagery of any mesh that passed the pre-registered screens, and the candidate dossiers. Under the
First Letters rules those go to the Scroll Prize team privately before anything is said in public. Everything needed to rerun the
measurements is here; only the pictures of candidates are not.
