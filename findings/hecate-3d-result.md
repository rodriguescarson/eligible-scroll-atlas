# Hecate 9.6 um 3D output on known ink: result

Pre-registered in `prereg/HECATE-3D.md` (tag `prereg-hecate3d-v1`, sha256 `105b47ea...6620`, pushed 2026-09-19 08:01 UTC),
with one amendment before any run (tag `prereg-hecate3d-v2`, 08:03 UTC). Runs started 08:12 UTC on one RTX 6000 Ada,
released `hecate.py` (sha256 prefix `c232c18a1a86cfb9`) and `hecate_9.6um.pth`, bf16, batch 32. Everything below comes from
`artifacts/hecate-3d/`, produced by `hecate_profile.py` in the same folder.

## Pre-registered criterion: PASS

Both known-text controls put their 3D ink mass in a thin layer on the rendered surface.

| control | ink pixels | peak offset (planes) | layer concentration | criterion met |
|---|---|---|---|---|
| PHerc0139 w042 | 2,491,180 | 0 | 0.663 | yes |
| PHerc0139 w043 | 3,958,700 | 0 | 0.754 | yes |

Pass needed |peak offset| <= 3 and layer concentration >= 0.50 (a flat profile gives 0.3125) on both. Profile of the 3D
ink mass by plane, offset from the surface plane, in percent:

| offset | -4 | -3 | -2 | -1 | 0 | +1 | +2 | +3 | +4 | +5 | +6 | +7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| w042 ink | 2.4 | 5.2 | 10.1 | 13.2 | **15.7** | 14.6 | 12.8 | 10.1 | 7.4 | 4.4 | 2.2 | 1.0 |
| w043 ink | 1.3 | 3.9 | 9.7 | 15.2 | **19.6** | 17.4 | 13.4 | 8.7 | 5.3 | 2.9 | 1.4 | 0.7 |

Both controls are inside the training data of the models that taught Hecate's 3D head (w043 is an `ink_9um` training
winding, w042 sits between training windings), so this is an upper bound on localization, not an estimate for new scrolls.

## What the pass does not mean

The same measure on pixels with no 2D ink (probability < 0.1), which the pre-registration required us to report:

| | peak offset | layer concentration | mass within +/-2 of the surface |
|---|---|---|---|
| w042 non-ink | +1 | 0.624 | 0.563 |
| w043 non-ink | +1 | 0.667 | 0.615 |

Non-ink pixels are nearly as concentrated as ink, one plane deeper, with a small rise at +7, where the next wrap sits.
So Hecate's 3D output sits on the rendered sheet as its authors intend, but it does so everywhere, ink or not. **Depth
concentration is not evidence of ink.** That is the 3D version of what our 2D calibration already showed: response
strength did not separate TAUIL's known false positive from real text either.

## Exploratory, one mesh, no claim

TAUIL's documented false positive, PHerc0813 z12496_w060, re-rendered at 9.6 um with the September recipe:

| | peak offset | layer concentration | mass within +/-2 of the surface |
|---|---|---|---|
| false positive, "ink" pixels | +1 | 0.649 | 0.581 |
| false positive, non-ink | +7 | 0.295 | 0.386 |

It would pass the control criterion too. Its "ink" profile peaks one plane deeper and is broader than the real text's
(0.58 of its mass within two planes of the surface, against 0.66 and 0.75), which is closer in shape to the controls'
non-ink pixels than to their ink, and its non-ink mass peaks on the neighbouring wrap. That is a lead worth pre-registering
on more meshes, not a result: one mesh cannot separate a property of this false positive from noise.

## villa#1830 check

Deterministic, as amended before the run: a 300-step PHerc0826 fit (z 6528 to 7328, tracks and normals only) on the PR
branch (`de41bfb`) and on its base (`b1ef996e`), with the same config overrides and no winding override.

| | spiral-scroll.json | checkpoint `shell_outer_winding_idx` | exporter | windings in the written mesh |
|---|---|---|---|---|
| PR branch | `"num_windings": 90` | 90 | `reconstructing windings 10..90` | 81 |
| base | no count | 130 | `reconstructing windings 10..130` | 121 |

The first export attempt exited 1 on both arms because our harness created the destination folder and villa's writer
refuses to overwrite one. The reconstruction had completed (81/81 and 121/121 windings) before that write. Rerun into
fresh folders, both exit 0 and the counts above come from the written meshes' own metadata.

## Side measurement, not pre-registered: why the September out-of-memory failures happened

The controls are larger than any canvas in the September memory sweep, so we measured the 2D pass of the released
`hecate.py` on w043 (47.3 megapixels, real) at the population's setting, bf16 batch 64, wrapped in `peakmem.py`:

| | peak allocated | peak reserved |
|---|---|---|
| synthetic canvases, 2.5 to 29.8 Mpx (`artifacts/hecate-chunking/`) | 12.00 GiB | 14.63 GiB |
| w043, 47.3 Mpx real render (`peakmem_w043_bf16_b64.log`) | 12.00 GiB | 28.79 GiB |

Live memory is flat in canvas size; the caching allocator's reserve nearly doubles, so two such jobs cannot share a 44.43 GiB
card. That, not the fp32 batch arithmetic we first published, explains the 23 failures. This commit corrects
`findings/hecate-memory-report.md` and `artifacts/hecate-chunking/oom_evidence.md` accordingly. Canvas size and real versus
synthetic data are not separated by one run.

## Cost

One RTX 6000 Ada at $0.84/h in US-WA-1, 08:09 to 09:01 UTC: about $0.72. The pod removed itself after the outputs were
copied off, confirmed gone by the RunPod API.
