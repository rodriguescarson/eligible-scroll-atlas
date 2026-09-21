# eligible-scroll-atlas

Every published surface mesh on the eight prize-eligible 9 um scrolls of the Vesuvius Challenge, rendered into the team's
own surface-volume layout with the team's own tool, verified against a team-published volume, and screened with the team's
public 9 um ink checkpoints under a pre-registration written before the first render. Renders, ink maps, previews and
per-mesh receipts are public so nobody has to render these scrolls again.

## Get one mesh in about twenty seconds

```sh
curl -sO https://raw.githubusercontent.com/rodriguescarson/eligible-scroll-atlas/main/scripts/atlas.py
python atlas.py list --ink-pass                      # the 5 meshes that pass the pre-registered screen
python atlas.py ink PHerc0125 z10544_w020 --preview  # a downsampled ink map, about 12 KB
python atlas.py get PHerc0125 z10544_w020            # the surface volume, 31 planes, plane 15 is the surface
```

```python
from atlas import meshes, fetch_surface_volume, open_surface
rows = [m for m in meshes(scroll="PHerc0813") if float(m["area_cm2"]) > 3]
volume = open_surface(fetch_surface_volume(rows[0]["scroll"], rows[0]["mesh"], "./atlas"))
volume.shape        # (31, H, W) uint8
```

Only the standard library is needed to download; `zarr` opens a surface volume as an array.

## What is public

| what | where |
|---|---|
| 340 surface volumes and 2,028 raw ink maps, 83 GB | [eligible-scroll-atlas-renders](https://huggingface.co/datasets/rodriguescarson/eligible-scroll-atlas-renders) |
| 4 spiral fits as tifxyz meshes, PHerc0191 and 3 PHerc0826 windows | [eligible-scroll-spiral-fits](https://huggingface.co/datasets/rodriguescarson/eligible-scroll-spiral-fits) |
| every mesh with its gate values and both models' scores | [`data/manifest.csv`](data/manifest.csv), 340 rows, built by `scripts/build_manifest.py` |
| the pre-registration and its amendments | [`prereg/`](prereg), tags `prereg-v1` to `prereg-v3`, each with its sha256 |
| the JSON behind every figure | [`artifacts/`](artifacts) |
| what the models did and did not show | [`findings/`](findings) |

The maps of the five meshes that passed the screens are held back: under the pre-registration their imagery goes to the
Scroll Prize team privately before any public statement. Their surface volumes and their scores are public, and
`maps_held` in the manifest marks them.

## What the survey found

All 340 meshes were screened and none dropped. Under the four pre-registered variants the pass counts are 5, 2, 0 and 1,
against denominators of 340 overall, 297 primary and 327 secondary. No mesh passes all four.

This is also the first run of the team's Hecate 9.6 um model, released 15 September, over all 340 meshes in both layer
directions, joined mesh by mesh to the ink screens. Four of the five ink passers land in Hecate's top 10 of 340
(P = 1.9e-06 if ranks were unrelated), so the two models agree in the tail. The agreement is not evidence of ink: the
highest response in the whole population and the second highest are our candidate and TAUIL's documented false positive,
and both score above known Greek text in both models.

[`findings/hecate-3d-result.md`](findings/hecate-3d-result.md) tests the same question in depth, pre-registered before the
run: Hecate's 3D output does put known ink on the rendered sheet, but it puts non-ink pixels there too, so depth
concentration is not evidence of ink either.

## What we got wrong, in public

* **Amendment 2** (`prereg-v3`): the screens first counted raw probabilities where the pre-registered rule is TAUIL's
  rescaled scale. On the pre-registered scale the known-ink control passes all four screens, and Amendment 1's
  explanation for its earlier failure is withdrawn.
* **Both original controls overstate sensitivity**: w043 is inside `ink_9um`'s training labels and w042 sits between
  training windings. Neither is held out, and the writeup no longer calls them that.
* **The out-of-memory explanation was wrong** and is corrected in [`findings/hecate-memory-report.md`](findings/hecate-memory-report.md):
  the population ran bf16, not fp32, and the measured cause is that reserved memory nearly doubles on a large real canvas
  (28.79 GiB against 14.63) while allocated memory stays at 12.00 GiB.
* **A shortcut tested and rejected**: scoring unarchived controls from a mask taken off the Hecate map inflates the bright
  fraction by 62 and 38 percent, so it is used nowhere.

## Upstream

* The layer direction was settled by measurement and the correction is merged into
  [pscamillo/vesuvius-eligible-meshes#1](https://github.com/pscamillo/vesuvius-eligible-meshes/pull/1).
* [ScrollPrize/villa#1830](https://github.com/ScrollPrize/villa/pull/1830) lets a dataset's `spiral-scroll.json` carry its
  own winding count, so a fit stops exporting windings past the papyrus.
* A memory report on the released Hecate model went to its author.

## Inputs and terms

Meshes from [pscamillo/vesuvius-eligible-meshes](https://github.com/pscamillo/vesuvius-eligible-meshes), alignment from
[TAUIL-Abd-Elilah/eligible-mesh-alignment](https://github.com/TAUIL-Abd-Elilah/eligible-mesh-alignment), checkpoints from
[scrollprize/ink_9um](https://huggingface.co/scrollprize/ink_9um) and [scrollprize/hecate](https://huggingface.co/scrollprize/hecate),
tools from [ScrollPrize/villa](https://github.com/ScrollPrize/villa).

Code is MIT. Renders, maps and meshes derive from the Vesuvius Challenge CT data and carry its CC BY-NC 4.0 terms.

## Dates

| date | step |
|---|---|
| 15 Sep 2026 | gate table built (340 meshes; 327 aligned under 30 degrees; 297 of those not `reprova`); pre-registration written; PHerc0800 reproduction, `--flip-normals` matches at r = 1.0000 ([`repro/`](repro)) |
| 16 Sep 2026 | all 340 meshes rendered and uploaded; screens complete; Hecate pass over all 340 complete |
| 19 Sep 2026 | spiral fits published; Hecate 3D localization tested against a pre-registration; memory report corrected |
