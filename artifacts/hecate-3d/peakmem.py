# peakmem.py: run hecate.py unchanged and report PyTorch's peak reserved and allocated GPU memory at exit.
# usage: python peakmem.py hecate.py --checkpoint hecate_9.6um.pth --input render.zarr --spacing-um 9.6 --output out.png \
#        --device cuda --precision bf16 --batch-size 64
import atexit, runpy, sys, torch
def report():
    if torch.cuda.is_available():
        print(f"PEAKMEM reserved_gib={torch.cuda.max_memory_reserved()/2**30:.3f} "
              f"allocated_gib={torch.cuda.max_memory_allocated()/2**30:.3f}", flush=True)
atexit.register(report)
script = sys.argv[1]; sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
