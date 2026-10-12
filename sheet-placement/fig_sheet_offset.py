"""Figure: is the rendered surface sitting on a papyrus sheet?

Left: where the sheet sits relative to the rendered surface, patch by patch, for a surface known
to carry readable ink against ours. Right: every screened surface against the control band.
"""
import csv, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ctrl = json.load(open("phase2/control_w043.json"))
co = np.load("phase2/control_w043_offsets.npy")
rows = [r for r in csv.DictReader(open("phase2/sheet_offsets.csv")) if r["iqr"]]
iqr = np.array([float(r["iqr"]) for r in rows])
w2 = np.array([100 * float(r["within2"]) for r in rows])
con = np.array([float(r["contrast"]) for r in rows])
ex = np.load("phase2/example_offsets.npy")

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2),
                              gridspec_kw=dict(width_ratios=[1, 1.15]))

# left: the two distributions, same axes
b = np.linspace(-8, 8, 33)
ax.hist(co, bins=b, weights=np.full(len(co), 100 / len(co)), color="#2e7d32", alpha=.85,
        label=f"curated surface, readable ink  (n={len(co)})")
ax.hist(ex, bins=b, weights=np.full(len(ex), 100 / len(ex)), histtype="step", lw=2.2,
        color="#b23b3b", label=f"our best surface  (n={len(ex)})")
ax.axvline(0, color="#222", lw=1.2)
ax.set_xlim(-8, 8)
ax.set_xlabel("where the sheet sits, relative to the rendered surface (voxels)")
ax.set_ylabel("% of patches")
ax.set_title("A surface on a sheet keeps the sheet at zero", loc="left",
             fontsize=12.5, fontweight="bold")
ax.legend(frameon=False, fontsize=9.5, loc="upper left")
for s_ in ("top", "right"): ax.spines[s_].set_visible(False)

# right: every surface, spread vs contrast
ax2.axhspan(min(s["iqr"] for s in ctrl["slabs"]), max(s["iqr"] for s in ctrl["slabs"]),
            color="#2e7d32", alpha=.18, zorder=0)
ax2.axvspan(min(s["contrast"] for s in ctrl["slabs"]), max(s["contrast"] for s in ctrl["slabs"]),
            color="#2e7d32", alpha=.10, zorder=0)
ax2.scatter(con, iqr, s=22, color="#b23b3b", alpha=.6, edgecolors="none", zorder=3)
ax2.scatter([ctrl["contrast"]], [ctrl["iqr"]], s=160, marker="*", color="#2e7d32",
            edgecolors="white", linewidth=.8, zorder=5, label="curated control")
ax2.set_xlabel("how clearly the sheets show up (grey levels)")
ax2.set_ylabel("spread of the sheet position (voxels)")
ax2.set_ylim(0, max(iqr.max() * 1.08, 8))
ax2.set_title(f"None of our {len(rows)} surfaces land where the control is", loc="left",
              fontsize=12.5, fontweight="bold")
ax2.legend(loc="upper right", frameon=False, fontsize=10)
ax2.text(ctrl["contrast"], ctrl["iqr"] + 1.2, "control", color="#2e7d32",
         ha="center", fontsize=10, fontweight="bold")
for s in ("top", "right"): ax2.spines[s].set_visible(False)

fig.text(.5, .018, "Each render samples the scan at many depths around the surface. Inside a small "
         "patch it is brightest where the papyrus is.\nOn the curated surface that depth is the surface "
         "itself. On ours it is anywhere within half a sheet.",
         ha="center", fontsize=9.5, color="#333")
fig.tight_layout(rect=[0, .055, 1, 1])
fig.savefig("phase2/fig_sheet_offset.png", dpi=170)
print(f"wrote phase2/fig_sheet_offset.png  (n={len(rows)} surfaces, control IQR {ctrl['iqr']:.2f})")
