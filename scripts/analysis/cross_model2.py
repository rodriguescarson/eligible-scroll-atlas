# cross_model2.py: for the Hecate top 10, the pre-registered ink_9um screen result per threshold variant, read by exact keys.
import json
from huggingface_hub import hf_hub_download
R = "rodriguescarson/eligible-scroll-atlas-held"
TOK = open("/workspace/atlas/.hf_token").read().strip()
TOP = ["PHerc0813/z13088_w040", "PHerc0813/z12496_w060", "PHerc0211/z11520_w020", "PHerc0211/z7920_w020",
       "PHerc0800/z9872_w020", "PHerc0211/z9120_w020", "PHerc0813/z11904_w060", "PHerc0211/z9712_w080",
       "PHerc0813/z13696_w040", "PHerc0813/z5888_w020"]
shown = False
print("%-26s %-6s %8s %8s %6s %6s %7s %6s %7s" % ("mesh", "thr", "S1", "S1_rev", "S2", "S3", "S3_prom", "S4", "pass/v2"))
for m in TOP:
    try:
        p = hf_hub_download(R, f"screens_all/{m}/ink-detection/screens_all.json", repo_type="dataset", token=TOK, local_dir="/tmp/screens")
        d = json.load(open(p))
    except Exception as e:
        print("%-26s unavailable %s" % (m, str(e)[:50])); continue
    for thr, v in sorted(d.get("variants", {}).items()):
        if not shown:
            print("KEYS:", sorted(v.keys())); shown = True
        s3 = v.get("S3") if isinstance(v.get("S3"), dict) else {}
        s4 = v.get("S4") if isinstance(v.get("S4"), dict) else {}
        print("%-26s %-6s %8.4f %8.4f %6s %6s %7s %6s %7s" % (
            m, thr, v.get("S1", float("nan")), v.get("S1_reverse", float("nan")),
            v.get("S2_pass"), s3.get("pass", v.get("S3_pass")), round(s3.get("prominence", 0), 2),
            s4.get("pass", v.get("S4_pass")), f"{v.get('pass')}/{v.get('pass_v2')}"))
