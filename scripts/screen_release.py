"""screen_release.py: score every finished mesh under the four reported variants (AMENDMENT-2) and mark it for release.
Variants: hit threshold uint8>=160 (TAUIL scale, primary) and uint8>=192 (v1 as implemented) x S4 on the unanimous minimum
(PREREG) and S4 per file (AMENDMENT-1). Controls' S1 for S2/R: 0.0549 (TAUIL scale), 0.0120 (raw 0.75).
Writes ink-detection/screens_all.json (never uploaded) and a marker: .cleared if no variant passes, .held otherwise.
Loops until inference has written ALL DONE and every receipt carries a marker."""
import glob, json, os, sys, time
sys.path.insert(0, "/workspace/atlas")
import screens as S
W = "/workspace/atlas"; R = f"{W}/renders"; LOG = f"{W}/log/screen_release.log"
CONTROL_S1 = {0.627: 0.0549, 0.75: 0.0120}
def log(m): open(LOG, "a").write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {m}\n")
log("START")
while True:
    todo = [j for j in sorted(glob.glob(f"{R}/*/*/ink-detection/infer.json"))
            if not (os.path.exists(os.path.join(os.path.dirname(j), ".cleared")) or os.path.exists(os.path.join(os.path.dirname(j), ".held")))]
    for j in todo:
        d = os.path.dirname(j); mesh = os.path.basename(os.path.dirname(d)); scroll = os.path.basename(os.path.dirname(os.path.dirname(d)))
        um = 8.64 if scroll in ("PHerc0800", "PHerc0268") else 9.362
        out = {"scroll": scroll, "mesh": mesh, "variants": {}}
        try:
            for thr in (0.627, 0.75):
                S.THR = thr
                r = S.screens(d, um, CONTROL_S1[thr], os.path.join(d, "valid_mask.tif"))
                out["variants"][str(thr)] = r
        except Exception as e:
            log(f"ERROR {scroll}/{mesh}: {str(e)[:200]}"); continue
        flags = {f"thr{t}_{k}": bool(v[k]) for t, v in out["variants"].items() for k in ("pass", "pass_v2")}
        out["flags"] = flags; out["any_pass"] = any(flags.values())
        json.dump(out, open(os.path.join(d, "screens_all.json"), "w"), indent=1)
        open(os.path.join(d, ".held" if out["any_pass"] else ".cleared"), "w").write(json.dumps(flags))
        v = out["variants"]["0.627"]
        log(f"{'HELD' if out['any_pass'] else 'cleared'} {scroll}/{mesh} S1@160={v['S1']:.5f} R={v.get('R', 0):.3f} S3={v['S3']['pass']} S4={v['S4']['mass_in_band']:.3f} flags={flags}")
    done = os.path.exists(f"{W}/infer/progress.log") and "ALL DONE" in open(f"{W}/infer/progress.log").read()
    if done and not todo:
        log("ALL DONE"); break
    time.sleep(120)
