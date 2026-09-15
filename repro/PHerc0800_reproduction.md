# Reproduction: the team's PHerc0800 surface volume from its published mesh

Done before any eligible mesh was rendered, as the pre-registration requires.

**Mesh:** `PHerc0800/segments/20251028213516-auto_grown_20251028213516907/mesh/20251028213516-on-20250521135224-8.64um.tifxyz`
(team-published; `scale [0.05, 0.05]`, the same grid step as pscamillo's 340).
**Reference:** the team's published `surface-volumes/8.64um-1.2m-116keV-volume-20250521135224.zarr`, level 0, shape `[31, 2160, 2240]`, chunks `[31, 128, 128]`, uint8, no compressor, 174 of 306 chunk keys present.
**Tool:** `vc_render_tifxyz` from `VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage`, `--scale 1 --group-idx 0 --num-slices 31 --slice-step 1 --cache-gb 8 --voxel-size 8.64 --voxel-unit micrometer --zarr-compressor none`, the volume streamed by `--remote-url` from the open-data bucket. Command in `render_repro.sh`; console output in `render_*.out`.

| variant | chunks compared | identical | missing / extra | Pearson r | mean abs diff (grey levels) |
|---|---|---|---|---|---|
| plain | 174 | 0 | 0 / 0 | 0.7294 | 23.885 |
| `--flip-normals` | 174 | 0 | 0 / 0 | **1.0** | **0.003** |

The flipped render reproduces the published volume to within rounding (r = 1.0, 0.003 grey levels mean absolute difference, identical chunk footprint); the plain render is the same data with the layer order reversed (`flip_is_layer_reversed_plain = True`), r = 0.7294.

**Decision, per the pre-registration:** `--flip-normals` is the convention for all 340 renders. Whether pscamillo's fitter writes normals with the same sign as the team's tracer is not established by this test; that is why every mesh is inferred in both layer orders, and why each sidecar records `normals_flipped: true`.

Timing on an 8 vCPU pod in EU-RO-1 streaming from us-east-1: 3 min 11 s for the first render (cold cache, 1.8 GB of chunks), 15 s for the second (warm cache).
