# equivalence.py: does releasing dead tensors change the output, and does it move peak memory?
# Runs the baseline and the patched file over the same canvas at the same batch and precision, in separate processes so peak
# stats are clean, then compares the PNGs byte for byte. Bit-identical is the bar: this edit changes no arithmetic.
import hashlib, json, subprocess, sys, time
W = "/workspace/patch"
RUNNER = f"{W}/run_one.py"
open(RUNNER, "w").write('''import json, runpy, sys, time, torch
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
''')
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
rows = []
for canvas in ("2p5", "11p5", "29p8"):
    for batch in (64, 16):
        for prec in ("fp32", "bf16"):
            res = {}
            for arm, src in (("baseline", f"{W}/hecate_baseline.py"), ("patched", f"{W}/hecate_patched.py")):
                out = f"{W}/out_{arm}_{canvas}_{batch}_{prec}.png"
                r = subprocess.run([sys.executable, RUNNER, src, f"/workspace/sweep/canvas_{canvas}.zarr", out, str(batch), prec],
                                   capture_output=True, text=True, timeout=5400)
                line = [l for l in r.stdout.splitlines() if l.startswith("{")]
                d = json.loads(line[-1]) if line else dict(error=(r.stderr or "no output")[-200:])
                d["sha256"] = sha(out) if not d.get("error") else None
                res[arm] = d
            row = dict(canvas=canvas, batch=batch, precision=prec,
                       identical=(res["baseline"].get("sha256") == res["patched"].get("sha256") and res["baseline"].get("sha256") is not None),
                       base_reserved=res["baseline"].get("peak_reserved_gib"), patched_reserved=res["patched"].get("peak_reserved_gib"),
                       base_alloc=res["baseline"].get("peak_alloc_gib"), patched_alloc=res["patched"].get("peak_alloc_gib"),
                       base_wall=res["baseline"].get("wall_s"), patched_wall=res["patched"].get("wall_s"),
                       errors=[a for a in ("baseline", "patched") if res[a].get("error")])
            rows.append(row); print(json.dumps(row), flush=True)
            json.dump(rows, open(f"{W}/equivalence.json", "w"), indent=1)
open(f"{W}/TEST_DONE", "w").write("done")
print("EQUIVALENCE DONE")
