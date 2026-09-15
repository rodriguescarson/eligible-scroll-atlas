"""make_atlas.py: static atlas page from ranked.csv and the ds8 previews.
usage: make_atlas.py --renders /workspace/atlas/renders --ranked atlas/ranked.csv --out atlas/ [--copy]
Rows sorted by R under the heading "closest to the control". Meshes that pass all four screens get scores only, no images."""
import argparse, csv, glob, html, os, shutil
ap = argparse.ArgumentParser(); ap.add_argument("--renders", required=True); ap.add_argument("--ranked", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--copy", action="store_true")
a = ap.parse_args(); os.makedirs(os.path.join(a.out, "ds8"), exist_ok=True)
rows = list(csv.DictReader(open(a.ranked)))
def f(x, n=4):
    try: return f"{float(x):.{n}f}"
    except: return ""
cards = []
for r in rows:
    d = os.path.join(a.renders, r["scroll"], r["mesh"], "ink-detection"); imgs = ""
    if r["pass"] != "True" and r.get("pass_v2") != "True":
        for p in sorted(glob.glob(os.path.join(d, "*-ds8.jpg"))):
            name = f"{r['scroll']}_{r['mesh']}_{os.path.basename(p)}"; dst = os.path.join(a.out, "ds8", name)
            if a.copy and not os.path.exists(dst): shutil.copy(p, dst)
            tag = os.path.basename(p).split("ink9um-")[-1][:-8]
            imgs += f'<figure><img loading="lazy" src="ds8/{name}" alt="{html.escape(tag)}"><figcaption>{html.escape(tag)}</figcaption></figure>'
    else: imgs = '<p class="held">passes all four screens: images held for the Scroll Prize team (pre-registration, "Outcomes")</p>'
    cards.append(f'''<section id="{r['scroll']}_{r['mesh']}"><h2>{r['scroll']} / {r['mesh']} <small>R {f(r['R'],3)}</small></h2>
<table><tr><th>area cm²</th><td>{r['area_cm2']}</td><th>verdict</th><td>{r['verdict'] or 'not inspected'}</td><th>aligned&lt;30°</th><td>{r['aligned_lt30']}</td><th>reprova</th><td>{r['reprova']}</td></tr>
<tr><th>S1 fwd</th><td>{f(r['S1'])}</td><th>S1 rev</th><td>{f(r['S1_reverse'])}</td><th>S2 ratio</th><td>{f(r['S2_ratio'],3)}</td><th>pass v1 / v2</th><td>{r['pass']} / {r.get('pass_v2','')}</td></tr>
<tr><th>S3 period mm</th><td>{f(r['S3_period_mm'],2)}</td><th>S3 prominence</th><td>{f(r['S3_prominence'],2)}</td><th>S4 mass in band</th><td>{f(r['S4_mass_in_band'],3)}</td><th>valid px</th><td>{r['valid_px']}</td></tr></table>
<div class="figs">{imgs}</div></section>''')
n_pass = sum(1 for r in rows if r["pass"] == "True")
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eligible scroll atlas</title><style>
body{{font:14px/1.45 system-ui,sans-serif;margin:0;padding:24px 16px;background:#faf9f6;color:#1c1b19;max-width:1400px;margin:auto}}
h1{{font-size:22px}} h2{{font-size:16px;margin:28px 0 6px;border-top:1px solid #d9d5cc;padding-top:14px}} small{{color:#6b665c;font-weight:normal}}
table{{border-collapse:collapse;font-size:13px}} th{{text-align:left;color:#6b665c;font-weight:500;padding:2px 10px 2px 0}} td{{padding:2px 18px 2px 0;font-variant-numeric:tabular-nums}}
.figs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}} figure{{margin:0;max-width:100%}} img{{max-width:100%;height:auto;max-height:260px;background:#000}}
figcaption{{font-size:12px;color:#6b665c}} .held{{color:#8a2f2f}} p.lead{{max-width:70ch}}
</style></head><body><h1>Eligible scroll atlas: {len(rows)} meshes, closest to the control first</h1>
<p class="lead">Raw ink_9um output on every published mesh of the eight prize-eligible 9 µm scrolls, screened under the pre-registered rule
(<a href="https://github.com/rodriguescarson/eligible-scroll-atlas/blob/main/prereg/PREREG.md">PREREG.md</a>). R = S1(mesh)/S1(w043 control).
A high R moves a mesh up the queue for a human look; it is not a detection. Meshes passing all four screens: {n_pass}.
Previews are 8× block means of the raw maps, displayed as (p − 0.25)/0.5.</p>
{''.join(cards)}</body></html>'''
open(os.path.join(a.out, "index.html"), "w").write(page); print("wrote", os.path.join(a.out, "index.html"), len(rows), "rows,", n_pass, "passing")
