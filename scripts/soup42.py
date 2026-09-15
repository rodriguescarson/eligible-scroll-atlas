"""Uniform parameter average of hybrid_3d2d-seed42 steps 10000/20000/30000 (inkbench soup.py, soup_s42_early3).
Writes checkpoints/soup42_early3.pth with the same top-level structure as the inputs, optimizer state dropped."""
import hashlib, json, os, torch

ROOT = "/workspace/atlas/checkpoints"
SRC = [f"{ROOT}/ink_9um/hybrid_3d2d-seed42/step-0{s}.pth" for s in ("10000", "20000", "30000")]
OUT = f"{ROOT}/soup42_early3.pth"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def state_key(ck):
    for k in ("model", "model_state_dict", "state_dict", "network_weights"):
        if k in ck and isinstance(ck[k], dict): return k
    raise KeyError(list(ck.keys()))

if not os.path.exists(OUT):
    base = torch.load(SRC[0], map_location="cpu", weights_only=False)
    key = state_key(base)
    acc = {k: v.clone().double() if torch.is_tensor(v) and v.is_floating_point() else v for k, v in base[key].items()}
    for p in SRC[1:]:
        sd = torch.load(p, map_location="cpu", weights_only=False)[key]
        assert sd.keys() == acc.keys(), p
        for k, v in sd.items():
            if torch.is_tensor(v) and v.is_floating_point(): acc[k] += v.double()
    base[key] = {k: (v / len(SRC)).to(base[key][k].dtype) if torch.is_tensor(v) and v.is_floating_point() else v for k, v in acc.items()}
    for k in ("optimizer", "optimizer_state_dict", "scheduler", "ema"): base.pop(k, None)
    torch.save(base, OUT)
    print("soup written", OUT, "state key", key, "tensors", sum(1 for v in acc.values() if torch.is_tensor(v)))
meta = {"output": OUT, "output_sha256": sha(OUT), "inputs": {p: sha(p) for p in SRC}, "recipe": "uniform mean of floating-point tensors; non-float entries copied from step-010000"}
json.dump(meta, open(f"{ROOT}/soup42_early3.json", "w"), indent=1)
print(json.dumps(meta, indent=1))
