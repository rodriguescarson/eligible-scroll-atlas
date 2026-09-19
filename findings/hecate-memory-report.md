# Hecate 9.6 um: peak memory, bf16, and one change that does not help

Measured while running the released 9.6 um model over the 340 published meshes of the eight prize-eligible scrolls,
September 2026. Raw data and harness in `artifacts/hecate-chunking/`.

Three findings: one operational, one about precision, and one null. None of them asks you to change the code. The second
may be worth a line in the README, and the third is reported because we pre-registered it and it came out negative.

## 1. Live memory is flat in canvas size and linear in batch; reserved memory is not flat on a large real canvas

**Correction, 19 September 2026.** The first version of this section said peak GPU memory is flat in canvas size, and
explained our 23 out-of-memory failures with the fp32 figure for two jobs at batch 64 (41.3 GiB). Both were wrong. Our
population ran bf16, and the flat result only covers the synthetic canvases we measured, up to 29.8 megapixels. On a real
47.3 megapixel render at bf16 batch 64, peak **allocated** memory was 12.00 GiB, the same as on the small canvases, but peak
**reserved** memory was 28.79 GiB against 14.63. That reserve growth is what made two jobs collide. The run and its script
are in `artifacts/hecate-3d/` (`peakmem_w043_bf16_b64.log`).

24 runs of the released `hecate.py` on one A40 (44.43 GiB), torch 2.8.0+cu128, three synthetic canvases of 2.5, 11.5 and 29.8
megapixels at 31 planes. Real surfaces run larger: PHerc0139 w043 is 47.3 megapixels.

| Precision | batch 64 | batch 32 | batch 16 | batch 8 |
|---|---|---|---|---|
| fp32 | 20.63 | 10.62 | 5.60 | 3.10 |
| bf16 | 14.63 | 7.62 | 4.10 | 2.35 |

Peak reserved GiB on the synthetic canvases. Every figure is identical at all three sizes and only wall time scales with
area (53, 240 and 623 seconds at batch 64, fp32). Live tensors stay flat beyond that range too, which matches the code: the
output accumulator, the Hann weight map and the result are disk-backed memmaps. What does not stay flat is how much the caching
allocator holds on to: 28.79 GiB reserved on the 47.3 megapixel real render, with 12.00 GiB allocated. We have not separated
whether that growth comes from canvas size or from real data rather than synthetic.

**Why it mattered to us.** We ran two processes per card at `--precision bf16 --batch-size 64`. On a small canvas one run
reserves 14.63 GiB, so two fit on a 44.43 GiB card with room to spare. On a large real canvas one run reserves about 29 GiB, and
two do not. 23 of 340 meshes died with out-of-memory, the neighbouring process holding 34.21 GiB each time, and every one
succeeded when rerun alone. Each mesh ran in its own process, so this is not memory building up across meshes.

The practical advice is to size a card from peak **reserved** memory on your largest canvas, not from peak allocated or a small
test render. Whether `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, or tiling the canvas, would cap the reserve is untested.

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
