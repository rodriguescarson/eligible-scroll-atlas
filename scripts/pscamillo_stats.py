"""Per-mesh stats of pscamillo maps (seed43/060000, layers 7-24): S1-like frac>=0.75 forward and reverse, over pixels where the map is nonzero."""
import glob, os, csv, numpy as np, tifffile
rows=[]
for f in sorted(glob.glob("pscamillo_maps/PHerc*/*.tif")):
    if f.endswith("_reverse.tif"): continue
    r=f[:-4]+"_reverse.tif"
    m=tifffile.imread(f).astype(np.float32)/255.0; v=m>0
    row={"scroll":f.split("/")[1],"mesh":os.path.basename(f)[:-4],"shape":f"{m.shape[0]}x{m.shape[1]}","nonzero_frac":float(v.mean()),
         "S1_fwd":float((m[v]>=0.75).mean()) if v.any() else 0.0,"mean_fwd":float(m[v].mean()) if v.any() else 0.0}
    if os.path.exists(r):
        mr=tifffile.imread(r).astype(np.float32)/255.0; vr=mr>0
        row["S1_rev"]=float((mr[vr]>=0.75).mean()) if vr.any() else 0.0
    rows.append(row)
with open("pscamillo_stats.csv","w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=["scroll","mesh","shape","nonzero_frac","S1_fwd","mean_fwd","S1_rev"]); w.writeheader(); w.writerows(rows)
s=np.array([r["S1_fwd"] for r in rows]); print("n",len(rows),"S1_fwd median %.5f p90 %.5f max %.5f" % (np.median(s),np.percentile(s,90),s.max()))
top=sorted(rows,key=lambda r:-r["S1_fwd"])[:8]
for r in top: print(r["scroll"],r["mesh"],r["shape"],"S1 %.4f rev %.4f mean %.3f" % (r["S1_fwd"],r.get("S1_rev",0),r["mean_fwd"]))
