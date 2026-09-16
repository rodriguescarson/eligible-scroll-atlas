# Out-of-memory evidence from the September Hecate pass (16 Sep 2026)

Mined from the per-mesh inference logs on the three pods that ran the 9.6 micron pass, before the last pod removed itself.
Raw data: `mem_evidence.json` (305 log entries over 153 meshes), `stats_pod6_snapshot.jsonl`.

## What happened

23 meshes failed with `torch.OutOfMemoryError` across three A40 pods (44.43 GiB each) running two `hecate.py` processes at
`--batch-size 64`. All 23 were rerun alone afterwards and every one succeeded, so nothing was lost; the cost was operator
attention and about 40 minutes of pod time.

## What the logs show

- In all 10 log entries carrying the message, the failure is the same shape: the *other* process on the card held **34.21 GiB**,
  and the failing process died asking for 0.9 to 2.9 GiB more than remained, at
  `x = torch.cat([x, feats[0]], dim=1)` in `forward_features`.
- The failing process itself was small at that moment: 5.09 to 5.56 GiB allocated by PyTorch, plus 2.78 to 3.48 GiB reserved but
  unallocated.
- The meshes that failed were **not** the large ones: their canvases were 4.5, 9.5, 15.6, 20.0 and 21.5 megapixels, while the
  largest canvas in the whole pass, 29.8 megapixels, completed normally.
- Canvas sizes across the pass: minimum 2.5, median 11.5, maximum 29.8 megapixels; patch counts up to 28,762 per run.

## What this does and does not establish

It establishes that a single Hecate run can reach 34.21 GiB on an A40, and that two such runs do not fit on one card, so
concurrency is what produced every failure here.

It does **not** establish that peak memory scales with canvas area, because the tool logs memory only when it fails: there is no
per-run peak for the successful runs, including the 29.8 megapixel one. Any claim about the scaling has to be measured
deliberately, by instrumenting `torch.cuda.max_memory_allocated` across a range of canvas sizes, before it is stated.

## Why this is worth fixing rather than working around

The workaround used here was to rerun failures one at a time, which works but halves throughput on a card that can otherwise hold
two jobs. A bounded-memory path would let one A40 run two jobs reliably, and would let the model run at all on the 24 GiB cards
most people have. Whether that is achievable, and at what cost in runtime or output fidelity, is being measured rather than
assumed; the acceptance test is that a tiled map reproduces the whole-canvas map within a stated tolerance.
