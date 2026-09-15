# eligible-scroll-atlas

Every published surface mesh on the eight prize-eligible 9 um scrolls of the
Vesuvius Challenge, rendered into the team's own surface-volume layout with the
team's own tool, verified against a team-published volume, and screened with
the team's public 9 um ink checkpoints under a pre-registered recipe. Renders,
ink maps, previews and per-mesh receipts are released so nobody has to render
these scrolls again.

* `prereg/PREREG.md`: the recipe, controls, screens and outcomes, committed
  before the first render. SHA-256 at tag `prereg-v1`: `1efef1423caffa73d682a85e3ed083762b3bc9dd8babe33b76cb2792760fc20d`.
* `data/gates.csv`: the 340 meshes with area, pscamillo's eye verdict, and
  TAUIL's sheet-alignment angle (`scripts/gates.py` builds it).
* Renders and maps: Hugging Face dataset, linked here when uploaded.

Inputs: meshes from [pscamillo/vesuvius-eligible-meshes](https://github.com/pscamillo/vesuvius-eligible-meshes),
alignment from [TAUIL-Abd-Elilah/eligible-mesh-alignment](https://github.com/TAUIL-Abd-Elilah/eligible-mesh-alignment),
checkpoints from [scrollprize/ink_9um](https://huggingface.co/scrollprize/ink_9um),
tools from [ScrollPrize/villa](https://github.com/ScrollPrize/villa).

Code is MIT. Renders and maps derive from the Vesuvius Challenge CT data and
carry its CC BY-NC 4.0 terms.

## Status

| date | step |
|---|---|
| 15 Sep 2026 | gate table built (340 meshes; 327 aligned under 30 degrees; 297 of those not `reprova`); pre-registration written |
| 15 Sep 2026 | reproduction of a team-published PHerc0800 surface volume from its mesh: `--flip-normals` matches at r = 1.0000, mean abs diff 0.003 (`repro/PHerc0800_reproduction.md`) |

**Amendment 1** (15 Sep, filed before any eligible mesh was scored): the positive control fails S4 under the v1 wording by 0.9 points; v1 stands as primary (no ranking), v2 evaluates S4 per file. `prereg/AMENDMENT-1.md` sha256 `eef19198383bbee3cfa60418b2f175c281ea31759d5b067cd2926498e1b86d2a`.
**Amendment 2** (15 Sep, filed before the remaining 245 meshes were scored and before the PHerc0800 rescore was read): the screens used raw probabilities instead of TAUIL's rescaled ones; on the pre-registered scale the control passes all four screens; Amendment 1's mechanism is withdrawn; w043 is training data. `prereg/AMENDMENT-2.md` sha256 `c0d8056c8d042019bfa49caf868463c4eb962a07b260803b83055ebf944ca798`.

## Status (15 Sep 2026)

* Renders: all 340 meshes rendered into the team's segment layout (69 GB zstd, 0 failures), **all 340 uploaded** (one `surface-volumes.tar` per mesh) to
  [rodriguescarson/eligible-scroll-atlas-renders](https://huggingface.co/datasets/rodriguescarson/eligible-scroll-atlas-renders)
  together with the raw ink_9um maps as they are produced (three checkpoint files, both layer directions).
* Controls: see `control/RESULT.md`. **Correction (Amendment 2, tag `prereg-v3`):** our screens first ran on raw
  probabilities instead of TAUIL's rescaled scale. On the pre-registered scale the known-ink control passes all four
  screens, and Amendment 1's explanation for its S4 failure is withdrawn. The control segment (w043) is ink_9um training
  data, so an out-of-training control (w042) is being added. The planted 4 cm2 window was flagged at 54x and 997x on the
  old scale and is being re-evaluated.
* Inference over the 340 meshes is running (`scripts/infer_v2.sh`); per-mesh screen scores, the pscamillo
  comparison (`scripts/compare_pscamillo.py`) and the v2 list follow when it finishes.
