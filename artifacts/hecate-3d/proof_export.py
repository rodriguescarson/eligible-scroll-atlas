#!/usr/bin/env python3
"""villa#1830 proof: report the fitted checkpoint's winding settings and run the exporter's reconstruction stage.

Run from a villa spiral-fitting checkout (that checkout's modules are imported).
usage: proof_export.py <checkpoint_fitted.ckpt> <umbilicus.json> <destination_dir>
"""
import os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
import torch
from checkpoint_io import load_checkpoint_cpu
import flatten_spiral_checkpoint as flatten

ckpt, umbilicus, dest = sys.argv[1:4]
checkpoint = load_checkpoint_cpu(ckpt)
config = flatten._checkpoint_config(checkpoint)
print(f"PROOF checkout={os.getcwd()}", flush=True)
print(f"PROOF checkpoint shell_outer_winding_idx={config.get('shell_outer_winding_idx')} "
      f"model_gap_expander_num_windings={config.get('model_gap_expander_num_windings')} "
      f"model_gap_expander_capacity_windings={config.get('model_gap_expander_capacity_windings')}", flush=True)
surface = flatten._export_source_surface(
    checkpoint, config, Path(umbilicus), Path(dest),
    device=torch.device("cuda"), voxel_size_um=9.362, chunk_size=65536)
print(f"PROOF exported {surface}", flush=True)
