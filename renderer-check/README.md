# Does a CPU renderer reproduce VC3D? An independent check on two scan types

AndreasHad04 wrote a CPU-only Python renderer that reproduces the PHerc 343 First Letters render
without VC3D or an NVIDIA GPU (https://github.com/AndreasHad04/villa-apple-silicon). That matters
because the VC3D build that produced the winning image is no longer downloadable
(https://github.com/ScrollPrize/villa/issues/2049).

This is an independent check of that renderer against VC3D on two of my own surfaces, one per
eligible scan type, neither of them PHerc 343.

## Result

It reproduces VC3D on both, once two convention differences are matched.

| surface | scan | single layer | paired layers | wrong pair (control) | unflipped (control) |
|---|---|---|---|---|---|
| PHerc0800 z7472_w060 | 8.64 um | r 0.9753, 5.02 | **r 0.99863, 1.23** | r 0.9139, 9.29 | r 0.1792, 28.64 |
| PHerc0813 z4704_w080 | 9.362 um | r 0.9670, 6.68 | **r 0.99806, 1.66** | r 0.8866, 12.30 | r 0.1742, 33.16 |

Median correlation over layers, then mean absolute difference in grey levels, over valid pixels.

## The two conventions

**Normal direction.** My renders came from VC3D with `--flip-normals`; the CPU renderer uses VC's
default. Mapped the wrong way round the correlation falls to about 0.17, so this is not ambiguous.

**A half-voxel depth offset.** The CPU renderer writes 66 layers centred at 32.5, so every layer
sits at a half-integer depth. A 31-layer render centred at 15 sits on integers. The two sampling
grids interleave and never coincide, so no single layer of one lands on a layer of the other.
Averaging the two adjacent layers in the right direction takes the mean difference from 5 to 7 grey
levels down to 1.2 to 1.7. Averaging the other adjacent pair is clearly worse, which pins the
direction rather than leaving it as a fitted choice.

Compared single-layer the agreement looks mediocre and you could reasonably conclude the renderer
disagrees with VC3D. It does not.

## What is not explained

The residual after pairing is 1.2 to 1.7 grey levels rather than zero. Nearest-vertex normal against
VC3D's, or the interpolation, is where I would look next. Not chased here.

## Cost

Streaming anonymously from the open-data bucket on a laptop, no GPU: 974 chunks / 2.04 GB / 331 s
fetch / 40 s compute for the 8.64 um surface; 1320 chunks / 2.77 GB / 22 s compute for the 9.362 um
one. The resumable chunk cache earned its keep - the second run hit a full disk six chunks from the
end and resumed without refetching.

## Running it

    python compare_renderers.py <dir containing the VC3D surface-volumes zarr> <the CPU render zarr>

Reports both mappings and both controls.
