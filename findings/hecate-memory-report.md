# Hecate 9.6 um: peak memory, bf16, and one change that does not help

Measured while running the released 9.6 um model over the 340 published meshes of the eight prize-eligible scrolls,
September 2026. Raw data and harness in `artifacts/hecate-chunking/`.

about precision. Neither needs a code change to be useful, and the second may be worth a line in the README.

## 1. Peak GPU memory is flat in canvas size and linear in batch

24 runs of the released `hecate.py` on one A40 (44.43 GiB), torch 2.8.0+cu128, three canvases spanning the range we see in
practice: 2.5, 11.5 and 29.8 megapixels at 31 planes.

| Precision | batch 64 | batch 32 | batch 16 | batch 8 |
|---|---|---|---|---|
| fp32 | 20.63 | 10.62 | 5.60 | 3.10 |
| bf16 | 14.63 | 7.62 | 4.10 | 2.35 |

Peak reserved GiB. Every figure is identical at all three canvas sizes, so canvas area contributes nothing to peak memory; only
wall time scales with it (53, 240 and 623 seconds at batch 64, fp32). That matches the code: the output accumulator, the Hann
weight map and the result are disk-backed memmaps, and everything resident on the GPU scales with batch.

**Why it mattered to us.** We ran two processes per card at `--batch-size 64`, which needs 41.3 GiB of a 44.43 GiB card in fp32.
23 of 340 meshes died with out-of-memory, always with the neighbouring process holding 34.21 GiB, and every one succeeded when
rerun alone. The tool's default of 1 is not the problem; our launch settings were. Two jobs fit comfortably at batch 32 (21.2 GiB)
or 16 (11.2 GiB), and the cost is small: on the largest canvas, 623 s at batch 64 against 641 s at 32 and 649 s at 16.

A sentence in the README giving peak memory per patch, or the two-jobs-per-card arithmetic, would have saved us the failures.

## 2. `--precision bf16` takes 29 percent off peak, not half

bf16 saves 29 percent of peak reserved memory rather than the ~50 percent a full switch would give, and it is 40 percent faster
on the largest canvas (377 s against 623 s). The reason appears to be that two operations in the decoder carry fp32 autocast
policies, so the two largest tensors stay fp32 in both modes: the trilinear upsample before the final concatenation, and the
group norm inside the decoder block. The failing allocation in our logs, `torch.cat([x, feats[0]], dim=1)`, is exactly 48.0 MiB
per patch in both precision modes.

This is worth knowing for anyone sizing a card from the flag name.

## 3. The obvious patch does not help, and the measurement says why

Three tensors stay referenced after their last use: the conv1 output through the backbone, the encoder pyramid for the whole
decode, and each reduced feature until the function returns. Releasing them is arithmetic-free and should be bit-identical.

We published the pass/fail condition before running it, so this is checkable rather than asserted: commit `a8ede96` of
the repository linked below carries the acceptance bar and the metric, and the branch tip `8460ddc` still carried them
five minutes before the GPU that produced these numbers was created. Acceptance bar: byte-identical output PNGs. Metric: peak **reserved**
memory, not peak allocated, because reserved is what a co-tenant process sees. Stated in advance: if reserved does not move,
there is nothing to propose and we say so.

Reserved did not move. Not by a byte, in any configuration.

| precision / batch | allocated, base → patched | reserved, base → patched |
|---|---|---|
| fp32, 64 | 15.15 → 13.53 | 20.63 → 20.63 |
| bf16, 64 | 12.00 → 8.01 | 14.70 → 14.70 |
| fp32, 16 | 4.16 → 3.75 | 5.60 → 5.60 |
| bf16, 16 | 3.37 → 2.37 | 4.12 → 4.12 |

GiB, on one A40, torch 2.8.0+cu128. twelve baseline/patched pairs, the four configurations above crossed with the same three
canvases as section 1. Every pair produced a sha256-identical output image, and every pair reproduced the row above exactly,
which is section 1's result arriving a second way: these numbers do not depend on canvas size. Wall time is unchanged, within
1.5 s on runs of 32 to 650 seconds.

**So we are not proposing this patch, and the null result is the useful part.** Dropping a reference earlier lowers
`max_memory_allocated` by up to 33 percent (bf16 at batch 64, 12.00 → 8.01 GiB) and leaves `max_memory_reserved` untouched,
because the caching allocator keeps the freed blocks in its own pool instead of returning them to the driver. Anyone who
profiles Hecate with `max_memory_allocated` and patches against it will measure a large win and get no extra co-tenant capacity
at all. That is the trap, and it is the reason we report the two numbers separately in section 1.

The only lever that moved reserved is the one in section 1: run at a smaller batch size. On the largest canvas that costs 4
percent of wall time and halves the card footprint.
