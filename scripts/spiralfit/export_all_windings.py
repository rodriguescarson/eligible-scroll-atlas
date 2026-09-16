# export_all_windings.py (from the feasibility runbook s4, not yet run): write every winding of a fitted spiral checkpoint as tifxyz
import argparse
from pathlib import Path
import numpy as np, torch
from checkpoint_io import load_checkpoint_cpu
from flatten_spiral_checkpoint import _build_model, _checkpoint_config
from sample_spiral import get_spiral_yxs
from tifxyz import save_tifxyz

p = argparse.ArgumentParser()
p.add_argument('checkpoint'); p.add_argument('umbilicus'); p.add_argument('out_dir')
p.add_argument('--first', type=int, default=0); p.add_argument('--last', type=int, default=None)
p.add_argument('--voxel-size-um', type=float, required=True); p.add_argument('--chunk', type=int, default=65536)
a = p.parse_args(); dev = torch.device('cuda')
ck = load_checkpoint_cpu(a.checkpoint); cfg = _checkpoint_config(ck)
model = _build_model(ck, cfg, Path(a.umbilicus), dev)
with torch.inference_mode():
    T = model.get_slice_to_spiral_transform(); dr = model.get_dr_per_winding()
    z0, z1 = int(ck['z_begin']), int(ck['z_end'])
    step = int(cfg.get('output_step_size', 20)); m = int(cfg['model_flow_bounds_z_margin'])
    outer = cfg.get('shell_outer_winding_idx') or int(cfg['model_gap_expander_num_windings'])
    last = a.last if a.last is not None else int(outer) - 1
    yxs_w = get_spiral_yxs(last + 1, dr, step, group_by_winding=True, device=str(dev))
    zs = torch.arange(z0 - m, z1 + m, step, dtype=torch.float32, device=dev)
    for w in range(a.first, last + 1):
        yxs = yxs_w[w]
        if yxs.shape[0] < 2: continue
        sp = torch.cat([zs[:, None, None].expand(-1, yxs.shape[0], 1), yxs[None].expand(zs.shape[0], -1, 2)], -1)
        fl = sp.reshape(-1, 3)
        sc = torch.cat([T.inv(fl[i:i + a.chunk]) for i in range(0, fl.shape[0], a.chunk)]).reshape_as(sp)
        sc[(sc[..., 0] < z0) | (sc[..., 0] >= z1)] = -1.0
        arr = sc.cpu().numpy().astype(np.float32)
        if not (arr[..., 0] >= 0).any(): continue
        save_tifxyz(arr, a.out_dir, f'w{w:03d}', step, a.voxel_size_um, 'export_all_windings')
        print('wrote', w, flush=True)
