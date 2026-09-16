# sweep.py: measure peak GPU memory of the UNMODIFIED hecate.py across batch size, canvas size and precision.
# This is the falsifier: if peak is flat in canvas and linear in batch, canvas tiling cannot help and batch size is the knob.
import json, os, runpy, subprocess, sys, time
W = "/workspace/sweep"
CAN = [("2p5", f"{W}/canvas_2p5.zarr"), ("11p5", f"{W}/canvas_11p5.zarr"), ("29p8", f"{W}/canvas_29p8.zarr")]
RUNNER = f"{W}/one_run.py"
open(RUNNER, "w").write('''import json, runpy, sys, time, torch
inp, out, batch, prec = sys.argv[1:5]
sys.argv = ["hecate.py", "--checkpoint", "/workspace/sweep/hecate/hecate_9.6um.pth", "--input", inp,
            "--spacing-um", "9.6", "--output", out, "--device", "cuda", "--precision", prec, "--batch-size", batch]
torch.cuda.init(); torch.zeros(1, device="cuda")  # CUDA must be initialised before peak stats can be reset\ntorch.cuda.reset_peak_memory_stats(); t0 = time.time()
try:
    runpy.run_path("/workspace/sweep/hecate/hecate.py", run_name="__main__"); err = None
except SystemExit as e:
    err = None if not e.code else f"exit {e.code}"
except Exception as e:
    err = type(e).__name__ + ": " + str(e)[:200]
print(json.dumps(dict(peak_alloc_gib=torch.cuda.max_memory_allocated() / 2**30,
                      peak_reserved_gib=torch.cuda.max_memory_reserved() / 2**30,
                      total_gib=torch.cuda.get_device_properties(0).total_memory / 2**30,
                      wall_s=round(time.time() - t0, 1), error=err)), flush=True)
''')
rows = []
for prec in ("fp32", "bf16"):
    for name, path in CAN:
        for batch in (64, 32, 16, 8):
            out = f"{W}/out_{name}_{batch}_{prec}.png"
            t0 = time.time()
            r = subprocess.run([sys.executable, RUNNER, path, out, str(batch), prec], capture_output=True, text=True, timeout=5400)
            line = [l for l in r.stdout.splitlines() if l.startswith("{")]
            d = json.loads(line[-1]) if line else dict(error=(r.stderr or "no output")[-200:])
            d.update(canvas=name, batch=batch, precision=prec, total_wall_s=round(time.time() - t0, 1))
            rows.append(d); print(json.dumps(d), flush=True)
            json.dump(rows, open(f"{W}/memsweep.json", "w"), indent=1)
            if os.path.exists(out): os.remove(out)
print("SWEEP DONE")
