# The Hecate out-of-memory failures were our own misconfiguration (16 Sep 2026)

Supersedes the earlier version of this file, which framed these failures as a missing capability and proposed bounded-memory
tiling. A line-by-line memory model of `hecate.py` says that framing was wrong.

## What actually happened

23 meshes failed with `torch.OutOfMemoryError` across three A40 pods running **two** inference processes each at
`--batch-size 64`. The tool's own default is `--batch-size 1` (line 411). All 23 recovered when rerun alone. Every failure was a
co-tenancy collision produced by our launch settings, not by any mesh being too large.

## Why tiling the canvas would have saved nothing

Every GPU allocation in this tool scales with **batch**, not with canvas size:

| Term | Scales with | Cost |
|---|---|---|
| The failing `torch.cat` at line 179 | batch | exactly 48.0 MiB per patch, fp32 |
| Decoder block 2 working set, the global peak | batch | 112 MiB per patch |
| Encoder pyramid, pinned but dead after line 165 | batch | 85 MiB per patch |
| Model parameters and buffers | nothing | 498.1 MiB, constant |
| Output accumulator, weight map, PNG and Zarr | canvas | disk-backed memmaps, zero GPU bytes |

The logged 2.30 GiB request divided by 48.0 MiB gives an effective batch of 49, which is the arithmetic confirming batch as the
driver. At 2380 x 12240 the canvas-sized arrays are 116.5 MiB each on disk, not on the card.

The measured receptive field is 405 pixels in Y and X, so canvas tiles would need a 405 pixel halo to stay equivalent. Tiling
would add overlap work and seam risk to buy memory that was never allocated on the GPU in the first place.

## What the tool already does well, and is worth saying out loud

Inference runs under `inference_mode` with gradients disabled; patches are XY-tiled with Hann blending; only the central planes
are read in Z; the accumulators are float32 memmaps in a temp directory; normalization runs in 128 x 256 blocks; results leave
the GPU every batch; the PNG is streamed and the Zarr written in chunks. Output is never held whole in memory. The design is
already bounded. We opted out of its default and paid for it.

## Measured, on an unmodified hecate.py (16 Sep 2026)

Peak GPU memory of the released tool on one A40, torch 2.8.0+cu128, three synthetic canvases spanning the range seen in the
September pass, float32. Raw data in `memsweep.json`, harness in `held-scripts` as the sweep runner.

| Canvas | batch 64 | batch 32 | batch 16 | batch 8 |
|---|---|---|---|---|
| 2.5 Mpx | 20.63 | 10.62 | 5.60 | 3.10 |
| 11.5 Mpx | 20.63 | 10.62 | 5.60 | 3.10 |
| 29.8 Mpx | 20.63 | 10.62 | 5.60 | 3.10 |

Peak reserved GiB; peak allocated tracks it at 15.15, 7.82, 4.16 and 2.32. Wall time is the only thing that scales with canvas:
53 s, 240 s and 623 s at batch 64.

The same grid in bf16, also identical at every canvas size:

| Precision | batch 64 | batch 32 | batch 16 | batch 8 |
|---|---|---|---|---|
| fp32 | 20.63 | 10.62 | 5.60 | 3.10 |
| bf16 | 14.63 | 7.62 | 4.10 | 2.35 |

bf16 takes 29 percent off peak reserved memory, not the half a full-precision switch would give, which matches the model's
finding that the two largest decoder operations, the trilinear upsample and the group norm, stay in float32 under autocast. It is
also 40 percent faster on the largest canvas: 377 s against 623 s at batch 64.

**Peak memory is identical across a twelvefold change in canvas area and halves exactly with batch size.** That is the
prediction from the line-by-line model, confirmed: nothing on the GPU scales with the canvas, so tiling it cannot save a byte.

**What would have prevented all 23 failures.** Two concurrent jobs need twice the reserved figure plus context. At batch 64 that
is 41.3 GiB against 44.43 GiB of card, with no headroom for the second process's fragmentation, which is exactly the collision we
hit. At batch 32 it is 21.2 GiB, at batch 16 it is 11.2 GiB. Any of those would have run two jobs comfortably, at a cost of 1 to
7 percent in wall time: on the largest canvas, 623 s at batch 64 against 641 s at 32 and 649 s at 16.

## The dead-tensor release: pre-registered, tested, dropped

Three tensors stay alive long after their last use: the conv1 output, the `feats` list, and above all the encoder pyramid bound
as `feat_maps`, which is 85 MiB per patch and about 39 percent of peak. Releasing them is arithmetic-free. Before touching the
code we fixed the bar: byte-identical output PNGs as the acceptance test, and peak **reserved** memory as the metric, because
peak live memory falling does not guarantee reserved memory follows. Written down in advance: if reserved does not move, the
patch is dropped and the null is what gets reported.

Reserved did not move. Not by a byte, in any configuration.

| precision / batch | allocated, base → patched | reserved, base → patched |
|---|---|---|
| fp32, 64 | 15.15 → 13.53 | 20.63 → 20.63 |
| bf16, 64 | 12.00 → 8.01 | 14.70 → 14.70 |
| fp32, 16 | 4.16 → 3.75 | 5.60 → 5.60 |
| bf16, 16 | 3.37 → 2.37 | 4.12 → 4.12 |

GiB, one A40, torch 2.8.0+cu128, twelve baseline/patched pairs: the four configurations above crossed with the same three
canvases. Every pair produced a sha256-identical image, every pair reproduced the row exactly regardless of canvas, and wall
time moved by at most 1.5 s on runs of 32 to 650 seconds.

Releasing the tensors cuts live allocation by up to 33 percent and buys a neighbouring process exactly nothing, because the
caching allocator keeps the freed blocks in its own pool instead of returning them to the driver. **The patch is dropped.** The
trap it illustrates is worth more than the patch would have been: profile Hecate with `max_memory_allocated`, the number most
people quote, and this change looks like a third of the card; measure `max_memory_reserved`, the number that decides whether two
jobs fit, and it is identically zero.

Separately, `--precision bf16` does not halve the decoder, because the trilinear upsample and group norm carry fp32 autocast
policies, so the largest tensors stay fp32 in both precision modes. That one is a real finding and goes to the team.

So both questions this file was opened to settle came back against the interesting answer. Canvas tiling saves nothing because
nothing on the GPU scales with the canvas, and the dead-tensor release saves nothing a co-tenant can use. The only lever that
moved peak reserved memory is the batch size, and it was ours to set all along.
