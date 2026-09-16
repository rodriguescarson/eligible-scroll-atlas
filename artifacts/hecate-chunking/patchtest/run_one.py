import json, runpy, sys, time, torch
src, inp, out, batch, prec = sys.argv[1:6]
sys.argv = ["hecate.py", "--checkpoint", "/workspace/sweep/hecate/hecate_9.6um.pth", "--input", inp,
            "--spacing-um", "9.6", "--output", out, "--device", "cuda", "--precision", prec, "--batch-size", batch]
torch.cuda.init(); torch.zeros(1, device="cuda"); torch.cuda.reset_peak_memory_stats()
t0 = time.time(); err = None
try:
    runpy.run_path(src, run_name="__main__")
except SystemExit as e:
    err = None if not e.code else f"exit {e.code}"
except Exception as e:
    err = type(e).__name__ + ": " + str(e)[:200]
print(json.dumps(dict(peak_alloc_gib=torch.cuda.max_memory_allocated() / 2**30,
                      peak_reserved_gib=torch.cuda.max_memory_reserved() / 2**30,
                      wall_s=round(time.time() - t0, 1), error=err)), flush=True)
