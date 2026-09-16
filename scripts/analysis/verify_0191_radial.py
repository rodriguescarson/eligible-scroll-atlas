# verify_0191_radial.py: re-run the PHerc0191 density check with the volume named explicitly and recorded in the output.
# The original run's JSON did not record which volume it sampled, and PHerc0191's geometry is in-bounds for PHerc0826, so a
# wrong-scroll read would not have errored. Arm A's windings come back from the private dataset (both fit pods are gone).
import glob, json, os, subprocess
from huggingface_hub import snapshot_download
RUN = "spiralfit/PHerc0191/2026-09-15_PHerc0191_slice-11600-12400_0-patch_w90"
d = snapshot_download("rodriguescarson/eligible-scroll-atlas-held", repo_type="dataset",
                      token=open("/workspace/atlas/.hf_token").read().strip(),
                      local_dir="/workspace/verify0191", allow_patterns=[RUN + "/meshes/all/*"])
run = f"/workspace/verify0191/{RUN}/"
print("windings:", len(glob.glob(run + "meshes/all/w*/")))
umb = "/workspace/verify0191/umbilicus.json"
if not os.path.exists(umb):
    subprocess.run(["curl", "-sfL", "-o", umb, "https://raw.githubusercontent.com/AlexeyDrobkovStrikesBack/herculaneum-umbilici/main/PHerc0191_umbilicus.json"], check=True)
VOL = "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0191/volumes/20250821151635-9.362um-1.2m-113keV-masked.zarr/0"
subprocess.run(["/workspace/atlas/villa/vesuvius/.venv/bin/python", "/tmp/radial_pitch_vol.py", run, umb, "/nonexistent",
                "/workspace/verify0191/out", "12000", VOL], check=False)
r = json.load(open("/workspace/verify0191/out/radial_pitch.json"))
print("volume recorded:", r.get("volume"), "| shape", r.get("volume_shape"))
s = r["summary"]
for w in ("w027", "w051", "w073"):
    if w in s: print(w, s[w])
print("per-ray ours vs strict peaks:", [(x["ray"], x["ours"], x["peaks_k3"]) for x in s["per_ray_ours_vs_scan"]])
