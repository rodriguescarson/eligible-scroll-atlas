# Pre-registration: does Hecate 9.6 um's 3D output put known ink on the target sheet?

Written 2026-09-19, before any 3D inference was run on any of the inputs below. The commit that adds this file
and the tag `prereg-hecate3d-v1` are the timestamp.

## Question

Hecate's README says its 3D output is "intended to localize ink on the middle sheet", that this is "an intended
behaviour rather than a guarantee", and that it "can miss faint ink, respond to fibres, or include neighbouring
sheets". Nobody has published a measurement of it. We measure one thing: on surfaces that carry known Greek text,
does the 3D ink probability sit in a thin layer at the rendered surface, or spread through depth, or sit on a
neighbouring wrap?

## Inputs

Known-text controls, the only two with archived 9.6 um renders: PHerc0139 w042 and w043. Each is a 31-plane
surface-conditioned render at 9.6 um, `--flip-normals`, surface at plane 15. Forward is the ink direction on both
(Hecate 2D forward fraction >= 0.5: w043 0.105 against 0.020 reverse; w042 0.069 against 0.033).

Caveats stated in advance: w043 is inside `ink_9um`'s training labels and w042 sits between training windings;
Hecate's training scroll list is not published, so either may be easier for it than unseen text. A pass is
therefore an upper bound on how well the 3D head localizes ink, not an estimate for new scrolls.

## Method

1. `hecate.py --checkpoint hecate_9.6um.pth --spacing-um 9.6 --output-3d ink3d.zarr --output ink2d.png`, forward,
   released code and weights (hecate.py sha256 prefix c232c18a1a86cfb9).
2. Ink pixels: 2D forward probability >= 0.5, inside the valid mask (render nonzero at plane 15, eroded 64 px).
3. Depth profile P(z): the sum of 3D probability over ink pixels for each evaluated plane (the 16 planes in the
   Zarr's `evaluated_z_interval`), normalised to fractions.
4. Metrics: `argmax_offset` = argmax plane minus plane 15; `layer_concentration` (LC) = fraction of the profile
   within +/-2 planes of its own argmax. A flat profile gives LC = 5/16 = 0.3125.

## Pass and fail, fixed now

PASS if **both** controls have |argmax_offset| <= 3 planes **and** LC >= 0.50.

Rationale: consecutive windings sit about 7 planes apart at this spacing, so a peak within 3 planes is on the
rendered sheet and not the next wrap; LC >= 0.50 is 1.6 times the flat value.

FAIL otherwise. On FAIL the 3D output is not used for any screening, no population pass is run, and the result is
published as a negative in this repository.

## Reported whichever way it comes out, not part of pass/fail

- The same profile for 2D non-ink pixels (probability < 0.1) on both controls.
- Exploratory, n = 1 each, no claim: the same profile on TAUIL's documented false positive PHerc0813 z12496_w060,
  re-rendered at 9.6 um with the September recipe. If the 3D head were a false-positive screen, its profile would
  differ from the controls'. One mesh cannot establish that and this document does not claim it can.

## Separate, deterministic check for ScrollPrize/villa#1830

A short PHerc0826 fit (tracks and normals only) on the PR branch with `"num_windings": 90` in
`spiral-scroll.json` and no winding override, and the same fit on unpatched main. Expected: the branch resolves
`shell_outer_winding_idx = 90` and exports no winding at or above 90; main resolves 130. This is a check of the
config plumbing, not a hypothesis test.
