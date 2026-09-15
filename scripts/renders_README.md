---
license: cc-by-nc-4.0
pretty_name: Eligible scroll atlas renders
---

# Eligible scroll atlas: surface-volume renders and raw ink_9um maps for the 340 published meshes of the eight prize-eligible 9 µm scrolls

Renders of every mesh in [pscamillo/vesuvius-eligible-meshes](https://github.com/pscamillo/vesuvius-eligible-meshes)
(commit `0c966f8f`) into the Scroll Prize team's segment layout, plus the raw output of three public `ink_9um` checkpoint files
in both layer directions. Pre-registered recipe, screens and outcomes:
[rodriguescarson/eligible-scroll-atlas](https://github.com/rodriguescarson/eligible-scroll-atlas) (`prereg/PREREG.md`, tag `prereg-v1`;
`prereg/AMENDMENT-1.md`, tag `prereg-v2`).

Layout, one folder per scroll and mesh (the zarr is shipped as one tar per mesh because the raw layout is 580k chunk files, past the Hub's per-repo limit):

```
<scroll>/<mesh>/surface-volumes.tar     untar inside <scroll>/<mesh>/ to get:
    surface-volumes/<um>um-1.2m-<keV>keV-volume-<volid>.zarr   31 layers, uint8, chunks 31x128x128, zstd, 6-level pyramid
    render.json                                                 command, AppImage sha256, villa and mesh commits, wall time
<scroll>/<mesh>/ink-detection/<scroll>-<mesh>-<volid>-ink9um-<tag>.tif      raw uint8 probability map, forward layer order
<scroll>/<mesh>/ink-detection/...-<tag>_reverse.tif                          same, reversed layer order
<scroll>/<mesh>/ink-detection/*-ds8.jpg                                      8x block mean, displayed as (p-0.25)/0.5
<scroll>/<mesh>/ink-detection/valid_mask.tif                                 nonzero at level 0, eroded 64 px
<scroll>/<mesh>/ink-detection/infer.json                                     recipe, checkpoint tags, villa commit
```

Render: `vc_render_tifxyz` from `VC3D-4b3c728-2026-09-15-linux-x86_64.AppImage`, `--scale 1 --group-idx 0 --num-slices 31
--slice-step 1 --flip-normals`, voxel size 9.362 µm (8.64 for PHerc0800 and PHerc0268), each scroll's published masked
volume by URL. `--flip-normals` is the setting that reproduces the team's own PHerc0800 surface volume (Pearson r 1.0000,
`repro/` in the code repo). Inference: `vesuvius.ink_detection.inference.infer` at villa `4b3c728`, `--overlap 0.5
--blend-mode hann --direction both`, checkpoints `hybrid_3d2d-seed43/step-060000` (`s43_060k`), `hybrid_3d2d-seed42/step-020000`
(`s42_020k`) and a uniform weight average of seed42 steps 10000/20000/30000 (`soup42_early3`, recipe in `scripts/soup42.py`).

These are raw model outputs, not detections. Nothing here has been claimed as text.

Licence: the renders and maps are derived from Vesuvius Challenge open data, which is released under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/); these files carry the same terms. The code in the GitHub
repository is MIT.

Maps are published scroll by scroll after the pre-registered screens have run on them; a mesh that passes the screens
is listed with its scores only and its images go to the Scroll Prize team first (PREREG, "Outcomes").

The known-ink control (PHerc0139 w043) and the two planted-window controls are under `controls/`.
