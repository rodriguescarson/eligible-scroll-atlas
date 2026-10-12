# Is the flattened surface actually on a sheet? A per-surface test, and the answer for eight eligible scrolls

## The short version

Ink not appearing on a scroll can mean the ink is not there, or it can mean the surface we rendered
is not on the papyrus. Those two look identical in the output and are usually argued about rather
than measured. There is a cheap way to tell them apart, it needs no extra data, and run across every
prize-sized surface on eight eligible scrolls it says the second thing.

## The test

A render already samples the scan at many depths around the surface. So the question does not need
the raw scan, an umbilicus, or any ray casting. Inside a small patch, the scan is brightest where the
papyrus is. A surface that follows a sheet puts that brightest depth at zero everywhere. A surface
that ignores the sheets puts it anywhere within half a sheet.

Measure it patch by patch, not over the whole surface. Over a whole surface the sheet undulates and
the signal averages away to nothing: on our best surface the whole-surface swing is under two grey
levels and looks like noise, while the same data measured in small patches swings by fourteen. That
one choice is the difference between the test working and not.

## The control

The number only means something next to a surface known to be on a sheet, so the test is calibrated
against the team's own curated PHerc0139 w043, which carries readable ink. Four separate regions of
it, two thousand patches:

- the sheets show up at 67 grey levels
- half the patches put the papyrus within 1.8 voxels of the surface
- 42 in 100 are within 2 voxels

Consistent across all four regions. That is what a surface on a sheet looks like.

## The result

228 prize-sized surfaces across PHerc 0125, 0211, 0257, 0268, 0358, 0800, 0813 and 0826. 223 could be
measured; the other five are outer wraps that render almost empty, under two in a hundred pixels
valid, and are reported rather than dropped.

| | surfaces | papyrus within 2 voxels | half the patches within | sheets show up at |
|---|---|---|---|---|
| curated control, readable ink | - | 42 in 100 | 1.8 voxels | 67 |
| PHerc0125 | 49 | 13 in 100 | 8.5 voxels | 13 |
| PHerc0211 | 58 | 12 in 100 | 8.5 voxels | 15 |
| PHerc0257 | 2 | 11 in 100 | 9.1 voxels | 12 |
| PHerc0268 | 2 | 10 in 100 | 9.9 voxels | 8 |
| PHerc0358 | 1 | 13 in 100 | 10.0 voxels | 18 |
| PHerc0800 | 57 | 13 in 100 | 8.8 voxels | 15 |
| PHerc0813 | 52 | 12 in 100 | 8.9 voxels | 17 |
| PHerc0826 | 2 | 12 in 100 | 8.2 voxels | 21 |
| **all of ours** | **223** | **12 in 100** | **8.7 voxels** | **15** |

Not one of the 223 looks like the control. One has a tight spread and no signal behind it: the sheets
show up at under two grey levels there, so the brightest depth is noise rather than papyrus, and only
3 in 100 of its patches are within 2 voxels. That is why both numbers have to be read together, and
why a tight spread on its own is not evidence of anything.

## What this changes

Two things, and the second is the one that matters.

**The ink results on these scrolls were measuring surface placement.** A reading-face against
blind-face contrast, or any ink comparison, computed on a surface that is not on the papyrus is a
statement about the surface. Published nulls on these scrolls, including ours, have to be read that
way. This is not hypothetical: a null of the same shape was published on PHerc 343 shortly before
that scroll won its prize, and the letters turned out to be one to three windings from the sheet the
search had tracked.

**It separates "no ink" from "no ink recovered yet", per surface.** That distinction has been asked
for repeatedly and the honest answer for these eight scrolls is now attributable rather than
ambiguous: the limiting factor is where the surfaces sit, not the ink models. The models were never
given papyrus to look at.

The sheets also show up four to five times more faintly in our renders than in the curated one. So
surface placement is not the only problem on this scan type; the sheet structure is weak to begin
with.

## A second finding, from trying the obvious fix

The surfaces are short, so the obvious move is to join adjacent windows into a taller one. They
overlap, and the arithmetic is good: the longest unbroken runs reach several centimetres.

It does not work, and it fails quietly. A shared wrap label is not the same sheet from one window to
the next. Across all 265 joins the two surfaces sit a median of two to three sheets apart, the offset
is across the sheet rather than along it on 237 of them, and only 20 joins land within half a sheet.
Joining at a fixed label splices text onto a different page. The drift cannot be followed either:
within a column the sign alternates, so there is no trend to track.

Reported with the check anyone can run before trusting a join:
https://github.com/pscamillo/vesuvius-eligible-meshes/issues/2

## What this does not say

It does not say there is no ink in these scrolls. It says the surfaces as rendered are not on the
papyrus often enough for an ink result computed on them to mean much, and it says so per surface
rather than per scroll, with a positive control behind the number.

It also does not rank the scrolls by promise. The contrast column hints at it, but scan quality has
been mapped by others and that work is theirs.

## Files

- `sheet_offset.py` — the test, one surface at a time. Fetches a render, measures, deletes it.
- `control_w043.py` — the calibration against the team's curated PHerc0139 w043.
- `sheet_offsets.csv` — all 228 surfaces: patches, sheet contrast, median offset, spread, hit rates.
- `control_w043.json` — the control, four regions and pooled.
- `fig_sheet_offset.py` — the figure.

## Running it

One pass over a render. No scan access, no umbilicus, no labels, no ground truth, so it runs on any
scroll including ones nobody has read. Calibrate against a surface known to carry ink before
trusting the numbers on one that does not.
