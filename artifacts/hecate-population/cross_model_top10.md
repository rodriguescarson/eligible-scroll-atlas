# Hecate top 10 against the pre-registered ink_9um screens (16 Sep 2026, population 256 of 340 meshes)

Accounting: 267 meshes were submitted to Hecate scoring and 256 returned usable maps. The 11 that did not are all PHerc0800
(z7472_w040/w060, z8672_w020/w040/w060/w080/w100, z11072_w080/w100, z12272_w020/w040), recorded as error rows in
`all.jsonl`; they were rerun successfully on the pod afterwards. The remaining meshes were still being scored when these
figures were computed. The joined per-mesh table behind every figure here is `cross_model_join.json`.

Hecate rank is by masked forward >= 0.75. Ink columns are the pre-registered variant at the TAUIL scale (raw threshold 0.627,
uint8 >= 160). "pass" is the v1 rule (S4 unanimous across the three ink files); "v2" is the per-file variant.

| Hecate rank | mesh | Hecate fwd / rev | ink S1 fwd / rev | S2 | S3 (prom) | S4 | ink pass / v2 |
|---|---|---|---|---|---|---|---|
| 1 | PHerc0813 z13088_w040 | 0.0774 / 0.0066 | 0.0344 / 0.0031 | yes | yes (2.26) | yes | **pass** / no |
| 2 | PHerc0813 z12496_w060 | 0.0674 / 0.0126 | 0.0405 / 0.0035 | yes | yes (2.57) | yes | **pass** / no | 
| 3 | PHerc0211 z11520_w020 | 0.0423 / 0.0558 | 0.0042 / 0.0051 | no | yes (1.49) | yes | no / no |
| 4 | PHerc0211 z7920_w020 | 0.0402 / 0.0850 | 0.0034 / 0.0135 | no | no | no | no / no |
| 5 | PHerc0800 z9872_w020 | 0.0257 / 0.0010 | 0.0174 / 0.0000 | yes | no | yes | no / no |
| 6 | PHerc0211 z9120_w020 | 0.0253 / 0.0552 | 0.0023 / 0.0097 | no | yes (1.83) | no | no / no |
| 7 | PHerc0813 z11904_w060 | 0.0231 / 0.0264 | 0.0110 / 0.0032 | yes | no (0.84) | yes | no / no |
| 8 | PHerc0211 z9712_w080 | 0.0223 / 0.0150 | 0.0047 / 0.0023 | no | no | no | no / no |
| 9 | PHerc0813 z13696_w040 | 0.0219 / 0.0061 | 0.0030 / 0.0003 | no | yes (7.20) | yes | no / no |
| 10 | PHerc0813 z5888_w020 | 0.0216 / 0.0138 | 0.0268 / 0.0223 | yes | yes (2.47) | yes | **pass** / no |

**The agreement is one-directional.** Every ink-screen passer that Hecate has scored is in its top 10 (ranks 1, 2 and 10 of 256;
about 4e-05 if ranks were unrelated). The converse fails: seven of Hecate's ten strongest forward responses are rejected by the
pre-registered ink rule, two of them (ranks 4 and 6) with reverse stronger than forward in both models.

**And rank 2 is TAUIL's known false positive**, which passes every ink screen at this threshold. So a mesh can top both models and
still not be writing. What survives from this table: the two models respond to an overlapping small set of surfaces, and that set
is not defined by ink.

Rank 10 (z5888_w020) is a weak pass: its ink forward 0.0268 is barely above its reverse 0.0223.

## Population view, not just the top 10 (16 Sep 03:35 UTC, 256 meshes joined to their screens)

Rank correlations between the two models across all 256 scored meshes (Spearman):

| Pair | rho |
|---|---|
| Hecate forward >=0.75 against ink S1 | 0.185 |
| Hecate forward >=0.75 against ink S1 forward minus reverse | 0.069 |
| Hecate log forward/reverse against ink S1 forward minus reverse | 0.442 |

Shared membership of the strongest sets:

| Set | Shared | Expected by chance | Probability of that many or more |
|---|---|---|---|
| Top 10 | 5 of 10 | 0.4 | 6.6e-06 |
| Top 20 | 8 of 20 | 1.6 | 2.3e-05 |
| Top 50 | 17 of 50 | 9.8 | 5.1e-03 |

**Read it as tail agreement, not general agreement.** The models pick overlapping extremes and agree moderately on which
direction is stronger (rho 0.44), but they barely agree on the ordering of surfaces overall (rho 0.19), and the overlap
attenuates sharply with depth: 5 of 10 at P = 6.6e-06, 8 of 20 at P = 2.3e-05, 17 of 50 at P = 5.1e-03 against 9.8 expected.
The top-50 overlap is still above chance, not at it. Mean Hecate forward >=0.75 is 0.0555 for the three ink-rule passers against 0.0065 for the other 253,
but n is 3, and one of the three is the known false positive.

## Known ink placed in the same distribution (16 Sep 03:50 UTC)

Computed with the identical statistic, masked fraction over the render's valid area eroded by 64 px, from the archived 9.6 um
renders of the two PHerc0139 controls. The far-winding controls (w051, w058, PHerc0172 w081) have no archived render in the
dataset, so they cannot be made comparable; future control runs should archive the render alongside the maps.

| Surface | fwd >=0.5 | fwd >=0.75 | rev >=0.75 | ratio | percentile of 256 |
|---|---|---|---|---|---|
| Candidate PHerc0813 z13088_w040 | 0.1180* | 0.0774 | 0.0066 | 11.5 | highest |
| Known false positive z12496_w060 | 0.0674** | 0.0674 | 0.0126 | 5.3 | 99.6 |
| **Known ink w043** (in Hecate's training labels) | 0.1045 | 0.0547 | 0.0072 | 7.5 | 99.2 |
| **Known ink w042** (not in its labels) | 0.0688 | 0.0333 | 0.0149 | 2.2 | 98.4 |

\* population file value; \*\* forward >=0.75 repeated, the >=0.5 figure is in the population file.

**What this calibrates.** Real Greek text does land in the top 1-2% of the eligible-mesh population, so the measure behaves as
intended. But the candidate scores above both known-ink controls on level and ratio, and the known false positive also scores
above w042 and close to w043. So "stronger than known ink" is not an argument for text, and this scale is not a measure of how
much ink is present. The calibration bounds the claim rather than supporting it.

## The same calibration on the ink model (16 Sep 03:55 UTC)

Reference-detector positives scored by the pre-registered screens (no ink ground truth exists off the training set: w043 is inside ink_9um's training labels and w042 sits between training windings w041 and w043, so neither is held out; the PHerc0139 far windings and the PHerc0172 windings are the closest to unseen), placed in the 340-mesh ink S1 distribution at the same variant
(population median 0.0015, p90 0.0060, p99 0.0266, max 0.0405):

| Control | ink S1 fwd / rev | pre-registered rule | percentile of 340 |
|---|---|---|---|
| PHerc0139 w059 | 0.0274 / 0.0035 | pass, both variants | 99.4 |
| PHerc0139 w058 | 0.0271 / 0.0048 | pass, both variants | 99.4 |
| PHerc0139 w055 | 0.0149 / 0.0069 | pass, both variants | 97.6 |
| PHerc0139 w051 | 0.0134 / 0.0022 | pass, both variants | 97.1 |
| PHerc0172 w081 | 0.0074 / 0.0014 | v2 only | 92.4 |
| PHerc0172 w087 | 0.0053 / 0.0008 | fails both | 86.8 |

**Two things follow.**

1. **A detection limit.** Real text on far windings of a good scan lands at the 97th to 99.4th percentile and passes the rule.
   On PHerc0172 real text lands at the 87th to 92nd and does not pass v1 at all. So a PHerc0172-like surface carrying writing
   would be missed by the pre-registered screen, and any negative result has to be stated with that bound.
2. **The candidate and the known false positive both outscore real text, in both models.** In ink, the known false positive
   z12496_w060 is the population maximum at 0.0405 and the candidate z13088_w040 is second at 0.0344, with every
   PHerc0139 control (0.0134 to 0.0274) below both. In Hecate, the candidate is the maximum and the false positive second, again above the controls.
   Whatever these two surfaces are, they produce a stronger response than genuine Greek text does, which is an argument against
   reading the strength as ink.

## Verified ink ranking over all 340 meshes (16 Sep 04:00 UTC)

Read directly from every mesh's `screens_all.json` at the pre-registered variant, rather than inferred from the table above.

| Rank | mesh | ink S1 fwd / rev | v1 | v2 |
|---|---|---|---|---|
| 1 | PHerc0813 z12496_w060 | 0.0405 / 0.0035 | pass | no |
| 2 | PHerc0813 z13088_w040 | 0.0344 / 0.0031 | pass | no |
| 3 | PHerc0813 z5888_w020 | 0.0268 / 0.0223 | pass | no |
| 4 | PHerc0211 z6720_w100 | 0.0267 / 0.0316 | no | no |
| 5 | PHerc0358 z11280_w020 | 0.0264 / 0.0043 | pass | pass |
| 6 | PHerc0813 z7696_w020 | 0.0202 / 0.0080 | pass | pass |
| 7 | PHerc0800 z9872_w020 | 0.0174 / 0.0000 | no | no |
| 8 | PHerc0813 z9504_w020 | 0.0162 / 0.0146 | no | no |

The five meshes passing the v1 rule across the whole population are ranks 1, 2, 3, 5 and 6. Rank 1 is the known false positive.
Rank 4 fails because its reverse exceeds its forward, which is the screen doing its job.

## Rejected: scoring the remaining controls from a mask taken off the map (16 Sep 04:10 UTC)

The three far-winding controls have Hecate maps but no archived render, so the population statistic cannot be computed for them.
I tested whether a mask derived from the map itself (pixels above zero, eroded 64 px) reproduces the real one, on the two controls
where the render is archived:

| Control | true fwd >=0.75 | map-derived | error | mask pixels, true vs derived |
|---|---|---|---|---|
| PHerc0139 w042 | 0.0333 | 0.0538 | +62% | 37.3M vs 20.2M |
| PHerc0139 w043 | 0.0547 | 0.0757 | +38% | 39.5M vs 25.9M |

**The proxy is rejected.** A Hecate map has large zero regions inside the valid area, so eroding from non-zero pixels removes
genuine low-probability interior and inflates the bright fraction by a third to two thirds. For the record, the numbers it
produced for the unarchived controls were w058 0.0484, w051 0.0168 and PHerc0172 w081 0.2588; they are artefacts of that bias
and are not used anywhere. The w081 figure alone, at the top of the entire population, shows how wrong the method is.

The gap stays open: only w042 and w043 can be placed in the Hecate distribution. Control runs must archive the render alongside
the maps, which costs about a gigabyte per control and is the cheapest fix available.
