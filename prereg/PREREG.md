# Pre-registration: rendering and ink-screening every published mesh on the eight prize-eligible 9 um scrolls

Committed and tagged before any surface is rendered for the survey and before
any GPU hour is spent. Later revisions are new commits; this file's SHA-256 at
tag `prereg-v1` is recorded in the README.

## What is being built

A public, reproducible dataset: all 340 tifxyz meshes published by pscamillo in
`vesuvius-eligible-meshes` (1 Sep 2026; PHerc 0125, 0211, 0257, 0268, 0358,
0800, 0813, 0826; 1,935 cm2) rendered into the Vesuvius team's own
surface-volume layout with the team's own tool (`vc_render_tifxyz` from the
villa `latest` release), verified against a team-published surface volume,
then screened with the team's public 9 um ink checkpoints in both surface
directions, with every render, ink map, ds8 preview and per-mesh receipt
released.

## Population (fixed)

All 340 meshes are rendered and inferred. Nothing is dropped from the release.
Two denominators are reported and were computed before rendering, from
pscamillo's `data/index.csv` joined to TAUIL-Abd-Elilah's
`eligible-mesh-alignment/data/mesh_alignment.json` (`data/gates.csv` in this
repo, 15 Sep 2026):

* Primary: 297 meshes with a measured median sheet-alignment angle below 30
  degrees and no `reprova` verdict.
* Secondary: 327 meshes below 30 degrees regardless of verdict; 31 `reprova`
  meshes are flagged, not excluded; 2 meshes with no alignment measurement
  are listed as such.

PHerc0800 and PHerc0268 are 8.64 um scans; the other six are 9.362 um. Their
statistics are reported separately and never on one axis.

## Rendering recipe (fixed)

`vc_render_tifxyz` from the villa release asset
`VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage`, `--scale 1 --group-idx 0
--num-slices 31 --slice-step 1 --cache-gb 8 --voxel-unit micrometer` with
`--voxel-size` 9.362 (8.64 for PHerc0800 and PHerc0268), each scroll's
published masked volume by `--remote-url`, output as zarr in the team's
`surface-volumes/<um>um-1.2m-<keV>-volume-<volid>.zarr` naming.

The normals flag is not chosen by hand. The team has published surface
volumes for PHerc0800 segments; one of them is rendered from its published
mesh twice, with and without `--flip-normals`, and compared to the published
array at level 0. Whichever variant matches (`numpy.array_equal`, or Pearson r
>= 0.99 if the tool's rounding differs) sets the flag for all 340, and the
choice plus the comparison numbers go into every mesh's sidecar. If neither
matches, the survey stops until the discrepancy is understood.

## Inference recipe (fixed)

`vesuvius.ink_detection.inference.infer` from the villa repository at the
commit recorded in each receipt, three checkpoint files from the public
`scrollprize/ink_9um` release: a uniform weight average of
`hybrid_3d2d-seed42` steps 10000, 20000 and 30000; `hybrid_3d2d-seed43`
step 060000; and `hybrid_3d2d-seed42` step 020000. `--overlap 0.5` (an
on-grid stride; tarikcankorkmaz00 measured off-grid strides at 0.005 to
0.032 AUC worse), `--blend-mode hann`, both directions (forward and the
reverse-layer-order flag; the team says layer order is the setting that
matters), each render zero-padded to a multiple of 64 on Y and X before
inference so the boundary block sits on the stride grid, inference restricted
to the valid mask (nonzero at level 0, eroded 64 px).

## Controls (fixed, run before any eligible mesh is scored)

1. Positive: the team's published native surface volume for PHerc0139 w043,
   inferred by URL with the identical recipe. It must pass every screen below.
2. Planted: a 4 cm2 window of that w043 render spliced into one eligible
   render at the same pitch and inferred as if it were part of it. The
   screens must flag that window.
3. Negative: one `reprova` mesh, and the reverse direction of every mesh.

If the positive control fails a screen or the planted window is not flagged,
the instrument is not measuring ink on this data: the renders and maps are
still published, no ranking is published, and the reason is stated.

## Screens (fixed; thresholds are TAUIL's published rule, adopted unchanged)

Per mesh, over valid pixels, with p_min = the pixelwise minimum over the
three checkpoint files:

* S1 coverage: fraction of valid pixels with p_min >= 0.75.
* S2 ratio: S1 divided by S1 on the positive control; must be within 5x.
* S3 row periodicity: a dominant spatial period between 4 and 5 mm along the
  writing axis with peak prominence above 1.2x the background.
* S4 stroke scale: connected components of the p_min >= 0.75 mask with area
  between 0.3 and 2 mm2 carry the majority of S1 mass.

A mesh "passes" only if all four hold in the forward direction and the
forward-minus-reverse S1 difference is positive.

## Ranking statistic (fixed)

`R = S1(mesh) / S1(positive control)`, computed on the forward direction,
ties broken by the mean over the three files. Meshes are listed by R in
descending order under the heading "closest to the control", never
"detections". A high R moves a mesh up the queue for a human look at 3 cm or
larger; it does not clear it.

## Outcomes, written before the run

* Reproduction: pass if one normals variant matches the team's PHerc0800
  volume as defined above; otherwise the survey stops.
* Instrument: pass if control 1 passes all four screens and the planted
  window in control 2 is flagged; otherwise no ranking is published.
* Primary outcome: the number of meshes in the primary denominator passing
  all four screens. The expected value, from three prior partial surveys of
  the same meshes that each found none (TAUIL 0 of 56, gmDevi 0 of 1,880
  renders of his own fits, flummoxjr 0 of 71 rows), is zero; that is reported
  as the result if it is the result.
* Any mesh that passes all four screens is not shown in the public atlas
  beyond its screen scores; its images go to the Scroll Prize team privately,
  per the First Letters rules.

## What this cannot show

The public ink_9um checkpoints have not resolved letters even on training
scrolls at this resolution. A clean negative here says the published
checkpoints find nothing on these surfaces under this recipe; it does not
say the surfaces carry no ink.
