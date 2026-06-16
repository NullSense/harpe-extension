#!/usr/bin/env python3
"""Generate Harpe store assets: procedural SVG art tiles + HTML templates that
reuse the real popup.css, ready to be screenshotted at store dimensions.

Run:  python3 store/build_assets.py
Then render the HTML in store/templates/ with a headless browser (see store/README).
"""
import os
import random
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "store")
ASSETS = os.path.join(STORE, "assets")
TPL = os.path.join(STORE, "templates")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(TPL, exist_ok=True)

rng = random.Random(7)


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'preserveAspectRatio="xMidYMid slice">{body}</svg>')


def lin(id_, stops, angle=90):
    import math
    a = math.radians(angle)
    x2, y2 = round(50 + 50 * math.cos(a), 2), round(50 + 50 * math.sin(a), 2)
    x1, y1 = round(50 - 50 * math.cos(a), 2), round(50 - 50 * math.sin(a), 2)
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return (f'<linearGradient id="{id_}" x1="{x1}%" y1="{y1}%" x2="{x2}%" y2="{y2}%">{s}</linearGradient>')


def grain(w, h, op=0.06):
    return (f'<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" '
            f'numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/>'
            f'</filter><rect width="{w}" height="{h}" filter="url(#n)" opacity="{op}"/>')


# Each tile is an evocative procedural scene — varied subjects so the grid reads
# like a real, diverse gallery of "found" media.
def t_sunset_mountains():
    d = lin("g", [("0", "#1a1330"), ("0.45", "#7d3b5c"), ("0.7", "#d6743f"), ("1", "#f3b25a")])
    sun = '<circle cx="270" cy="150" r="46" fill="#ffd98a" opacity="0.95"/>'
    m1 = '<polygon points="0,400 0,250 110,170 220,260 330,180 400,250 400,400" fill="#2a1c35" opacity="0.92"/>'
    m2 = '<polygon points="0,400 0,300 130,230 260,310 400,240 400,400" fill="#160f24"/>'
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#g)"/>{sun}{m1}{m2}{grain(400,400)}')


def t_ocean():
    d = lin("g", [("0", "#06303a"), ("0.5", "#0e6e7e"), ("1", "#5fd0c4")], 100)
    waves = "".join(
        f'<path d="M0 {y} Q100 {y-18} 200 {y} T400 {y} V400 H0 Z" fill="#03242b" opacity="{0.15+i*0.12}"/>'
        for i, y in enumerate(range(150, 360, 45)))
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#g)"/>{waves}{grain(400,400)}')


def t_forest():
    d = lin("g", [("0", "#0a2a1a"), ("0.6", "#1f5d33"), ("1", "#88c06a")], 80)
    hills = "".join(
        f'<ellipse cx="{cx}" cy="{cy}" rx="180" ry="120" fill="#0e3a22" opacity="{op}"/>'
        for cx, cy, op in [(60, 420, 0.9), (220, 460, 0.8), (360, 430, 0.7)])
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#g)"/>{hills}{grain(400,400)}')


def t_nebula():
    d = (f'<radialGradient id="r" cx="40%" cy="35%" r="80%">'
         f'<stop offset="0" stop-color="#c98a3c"/><stop offset="0.4" stop-color="#5b2b6b"/>'
         f'<stop offset="1" stop-color="#0a0816"/></radialGradient>')
    stars = "".join(f'<circle cx="{rng.randint(0,400)}" cy="{rng.randint(0,400)}" r="{rng.choice([1,1,2])}" fill="#fff" opacity="{rng.uniform(0.4,1):.2f}"/>' for _ in range(60))
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#r)"/>{stars}{grain(400,400,0.04)}')


def t_dunes():
    d = lin("g", [("0", "#3a1f12"), ("0.5", "#b5713a"), ("1", "#f0c98a")], 95)
    curves = "".join(
        f'<path d="M0 {y} Q200 {y-50} 400 {y} V400 H0 Z" fill="#5a3318" opacity="{0.2+i*0.18}"/>'
        for i, y in enumerate(range(180, 360, 55)))
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#g)"/>{curves}{grain(400,400)}')


def t_city_night():
    d = lin("g", [("0", "#0b1026"), ("0.7", "#23284e"), ("1", "#c98a3c")], 90)
    blds, x = [], 10
    while x < 400:
        bw = rng.randint(28, 52); bh = rng.randint(120, 300)
        blds.append(f'<rect x="{x}" y="{400-bh}" width="{bw}" height="{bh}" fill="#070a18"/>')
        for wy in range(400 - bh + 12, 392, 22):
            for wx in range(x + 6, x + bw - 6, 14):
                if rng.random() > 0.45:
                    blds.append(f'<rect x="{wx}" y="{wy}" width="5" height="7" fill="#ffd98a" opacity="0.85"/>')
        x += bw + rng.randint(6, 14)
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#g)"/>{"".join(blds)}{grain(400,400,0.04)}')


def t_bloom():
    d = (f'<radialGradient id="r" cx="50%" cy="50%" r="70%"><stop offset="0" stop-color="#2a0d1f"/>'
         f'<stop offset="1" stop-color="#0d0610"/></radialGradient>')
    petals = "".join(
        f'<ellipse cx="200" cy="200" rx="22" ry="100" fill="{c}" opacity="0.7" transform="rotate({a} 200 200)"/>'
        for a, c in [(0, "#d6743f"), (45, "#c93f6a"), (90, "#e8b066"), (135, "#a23b7c"),
                     (180, "#d6743f"), (225, "#c93f6a"), (270, "#e8b066"), (315, "#a23b7c")])
    core = '<circle cx="200" cy="200" r="34" fill="#ffd98a"/>'
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#r)"/>{petals}{core}{grain(400,400,0.05)}')


def t_bauhaus():
    bg = '<rect width="400" height="400" fill="#efe4d2"/>'
    shapes = ('<circle cx="120" cy="130" r="80" fill="#c4452f"/>'
              '<rect x="200" y="60" width="150" height="150" fill="#1f3b6e"/>'
              '<polygon points="60,400 200,240 340,400" fill="#e0a92e"/>'
              '<circle cx="300" cy="320" r="46" fill="#16110c"/>')
    return svg(400, 400, f'{bg}{shapes}{grain(400,400,0.05)}')


def t_aurora():
    d = lin("g", [("0", "#04101a"), ("1", "#0a2438")], 90)
    bands = "".join(
        f'<path d="M0 {y} Q130 {y-70} 260 {y-10} T400 {y-30} V400 H0 Z" fill="{c}" opacity="0.45"/>'
        for y, c in [(170, "#3fd6a0"), (210, "#5fb0e0"), (250, "#9a6fd0")])
    stars = "".join(f'<circle cx="{rng.randint(0,400)}" cy="{rng.randint(0,140)}" r="1" fill="#fff" opacity="{rng.uniform(0.3,0.9):.2f}"/>' for _ in range(40))
    return svg(400, 400, f'<defs>{d}</defs><rect width="400" height="400" fill="url(#g)"/>{stars}{bands}{grain(400,400,0.04)}')


TILES = [t_sunset_mountains, t_ocean, t_forest, t_nebula, t_dunes,
         t_city_night, t_bloom, t_bauhaus, t_aurora]

# Realistic-looking dimensions/areas to label the cards with.
DIMS = [(3840, 2160), (4096, 2731), (2400, 3000), (5472, 3648), (3000, 2000),
        (2560, 1440), (1920, 2400), (3508, 2480), (4480, 6720)]


def mp(w, h):
    a = w * h
    return f"{a/1_000_000:.1f} MP" if a >= 1_000_000 else f"{a/1000:.0f} kpx"


def write_tiles():
    for i, fn in enumerate(TILES, 1):
        with open(os.path.join(ASSETS, f"thumb-{i}.svg"), "w") as f:
            f.write(fn())
    # A wide poster for the video card.
    poster = svg(640, 360,
                 f'<defs>{lin("g",[("0","#1a1330"),("0.5","#7d3b5c"),("1","#f3b25a")],100)}</defs>'
                 f'<rect width="640" height="360" fill="url(#g)"/>'
                 f'<polygon points="0,360 0,210 180,150 360,240 520,160 640,220 640,360" fill="#221634" opacity="0.9"/>'
                 f'<circle cx="470" cy="120" r="40" fill="#ffd98a" opacity="0.9"/>{grain(640,360,0.05)}')
    with open(os.path.join(ASSETS, "poster.svg"), "w") as f:
        f.write(poster)
    # Big page images for the faux gallery behind the panel.
    for i, fn in enumerate([t_sunset_mountains, t_ocean, t_city_night, t_bloom, t_forest, t_aurora], 1):
        with open(os.path.join(ASSETS, f"page-{i}.svg"), "w") as f:
            f.write(fn())
    # Brand mark copy for promos.
    src_icon = os.path.join(ROOT, "extension", "icons", "icon128.png")
    if os.path.exists(src_icon):
        shutil.copy(src_icon, os.path.join(ASSETS, "icon128.png"))


# ── card / panel fragments ───────────────────────────────────────────────────

def card(i, selected=False, saved=False):
    w, h = DIMS[i - 1]
    cls = "card" + (" selected" if selected else "")
    extra = ('<div class="result-badge ok">✓</div>' if saved else
             ('<div class="checkmark">✓</div>' if selected else ""))
    return (f'<div class="{cls}">'
            f'<img class="thumb" src="../assets/thumb-{i}.svg" alt="">'
            f'<div class="info"><span class="dims">{w} × {h}</span><span class="area">{mp(w,h)}</span></div>'
            f'{extra}</div>')


def video_card(saved=False):
    extra = '<div class="result-badge ok">✓</div>' if saved else '<div class="checkmark">✓</div>'
    return ('<div class="card is-video selected">'
            '<img class="thumb" src="../assets/poster.svg" alt="">'
            '<div class="play-badge">▶ video</div>'
            '<div class="info"><span class="dims">1920 × 1080</span><span class="area">2.1 MP</span></div>'
            f'{extra}</div>')


GEAR = ('<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.2"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 '
        '1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 '
        '0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 '
        '0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 '
        '1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 '
        '2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>')


def panel(inner_settings="", status="", saved_bar="", grid_cards="", count="20 found"):
    return f'''
  <aside class="harpe">
    <header>
      <div class="header-left"><img src="../assets/icon128.png" class="logo" alt=""><span class="app-name">Harpe</span></div>
      <div class="header-right">
        <button class="btn-icon" aria-expanded="{'true' if inner_settings else 'false'}">{GEAR}</button>
        <button class="btn-secondary">Rescan</button>
      </div>
    </header>
    {inner_settings}
    <div class="page-title-bar"><span class="page-title">Nasjonalmuseet — Collection highlights</span><span class="count">{count}</span></div>
    <div class="status {status[0] if status else ''}">{status[1] if status else ''}</div>
    {saved_bar}
    <main class="grid">{grid_cards}</main>
  </aside>'''


def settings_drawer():
    rows = []
    for lbl, ph in [("Images", "~/Pictures/harpe"), ("Videos", "~/Videos/harpe"), ("Audio", "~/Music/harpe")]:
        rows.append(f'<div class="dest-row"><label class="settings-label">{lbl}</label>'
                    f'<input class="settings-input" placeholder="{ph}"></div>')
    return f'''
    <section class="settings">
      <p class="mode-line ok">✓ Harpe engine connected — full power</p>
      <div class="dest-grid">{''.join(rows)}</div>
      <div class="settings-row"><button class="btn-primary">Save</button></div>
      <p class="settings-help">One folder per type — <code>~</code> and <code>$VARS</code> allowed, files grouped by site inside. Blank = the default shown.</p>
    </section>'''


def saved_bar(path="~/Videos/harpe/nasjonalmuseet.no"):
    return (f'<div class="saved-bar"><span class="saved-text">Saved to {path}</span>'
            '<button class="btn-secondary">Open folder</button></div>')


# ── page (faux browser) ──────────────────────────────────────────────────────

def browser_page(panel_html, url, page_grid):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="popup.css"><link rel="stylesheet" href="shared.css"></head>
<body class="shot"><div class="window">
  <div class="chrome"><div class="lights"><i class="r"></i><i class="y"></i><i class="g"></i></div>
    <div class="omni">🔒 {url}</div><div class="ext-pin"><img src="../assets/icon128.png" alt=""></div></div>
  <div class="viewport">
    <div class="webpage">
      <div class="wp-head"><h1>Collection highlights</h1><p>A few thousand works, free to explore.</p></div>
      <div class="wp-grid">{page_grid}</div>
    </div>
    {panel_html}
  </div>
</div></body></html>'''


def page_grid(n=6):
    return "".join(f'<div class="wp-tile"><img src="../assets/page-{i}.svg" alt=""></div>' for i in range(1, n + 1))


def write_shared_css():
    css = '''/* faux-browser + promo chrome for store shots (not shipped) */
:root{ --shot-w:1280px; --shot-h:800px; }
html,body{height:100%;}
body.shot{margin:0;background:#05040a;display:flex;align-items:center;justify-content:center;}
.window{width:var(--shot-w);height:var(--shot-h);background:var(--bg);overflow:hidden;display:flex;flex-direction:column;}
.chrome{height:46px;flex:none;display:flex;align-items:center;gap:14px;padding:0 16px;background:#100b08;border-bottom:1px solid var(--border);}
.lights{display:flex;gap:7px;}
.lights i{width:12px;height:12px;border-radius:50%;display:block;}
.lights .r{background:#ff5f57;} .lights .y{background:#febc2e;} .lights .g{background:#28c840;}
.omni{flex:1;height:28px;border-radius:8px;background:#1b130d;border:1px solid var(--border);display:flex;align-items:center;padding:0 12px;font-family:var(--mono);font-size:12px;color:var(--text-muted);}
.ext-pin{width:28px;height:28px;border-radius:7px;background:rgba(201,138,60,0.14);border:1px solid var(--border-strong);display:flex;align-items:center;justify-content:center;}
.ext-pin img{width:18px;height:18px;}
.viewport{flex:1;display:flex;min-height:0;}
.webpage{flex:1;min-width:0;overflow:hidden;background:radial-gradient(120% 90% at 20% -10%,rgba(201,138,60,0.07),transparent 55%),#0c0907;padding:34px 36px;}
.wp-head h1{font-family:var(--serif);font-size:34px;letter-spacing:.04em;color:var(--text);margin:0 0 6px;}
.wp-head p{font-family:var(--mono);font-size:13px;color:var(--text-muted);margin:0 0 22px;}
.wp-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
.wp-tile{aspect-ratio:4/3;border-radius:12px;overflow:hidden;border:1px solid var(--border);box-shadow:0 18px 40px -24px rgba(0,0,0,.7);}
.wp-tile img{width:100%;height:100%;object-fit:cover;display:block;}
/* the docked panel */
.harpe{width:392px;flex:none;height:100%;overflow:hidden;display:flex;flex-direction:column;background:var(--bg);border-left:1px solid var(--border);box-shadow:-24px 0 60px -30px rgba(0,0,0,.8);}
.harpe .grid{overflow:hidden;}
.harpe .status{}
/* promos */
body.promo{margin:0;}
.promo-stage{width:var(--shot-w);height:var(--shot-h);position:relative;overflow:hidden;background:
  radial-gradient(90% 120% at 80% -10%,rgba(201,138,60,0.18),transparent 55%),
  radial-gradient(80% 90% at 0% 110%,rgba(91,43,107,0.22),transparent 60%),var(--bg);
  display:flex;align-items:center;}
.promo-pad{padding:0 9%;max-width:62%;}
.promo-stage .logo-row{display:flex;align-items:center;gap:18px;margin-bottom:26px;}
.promo-stage .logo-row img{width:74px;height:74px;filter:drop-shadow(0 8px 26px rgba(216,153,33,.4));}
.promo-stage .wordmark{font-family:var(--serif);font-size:64px;letter-spacing:.12em;color:var(--bronze-bright);}
.promo-stage h2{font-family:var(--serif);font-weight:600;font-size:46px;line-height:1.15;letter-spacing:.02em;color:var(--text);margin:0 0 18px;}
.promo-stage h2 .hl{color:var(--bronze-bright);}
.promo-stage p{font-family:var(--mono);font-size:18px;line-height:1.6;color:var(--text-muted);margin:0;max-width:30ch;}
.promo-chips{display:flex;gap:10px;margin-top:28px;flex-wrap:wrap;}
.promo-chips span{font-family:var(--mono);font-size:13px;color:var(--bronze-bright);border:1px solid var(--border-strong);background:rgba(201,138,60,.1);border-radius:999px;padding:6px 13px;}
.promo-float{position:absolute;right:-40px;top:50%;transform:translateY(-50%) rotate(-4deg);width:360px;height:560px;background:var(--bg2);border:1px solid var(--border-strong);border-radius:18px;overflow:hidden;box-shadow:0 50px 120px -40px rgba(0,0,0,.9),0 0 0 1px rgba(201,138,60,.08);display:flex;flex-direction:column;}
.promo-float.small{width:300px;height:340px;right:-30px;}
/* small tile layout */
.promo-stage.tile .promo-pad{max-width:100%;padding:0 30px;}
.promo-stage.tile .wordmark{font-size:42px;}
.promo-stage.tile h2{font-size:24px;}
.promo-stage.tile p{font-size:13px;}
'''
    with open(os.path.join(TPL, "shared.css"), "w") as f:
        f.write(css)


def write_templates():
    shutil.copy(os.path.join(ROOT, "extension", "css", "popup.css"), os.path.join(TPL, "popup.css"))
    write_shared_css()

    # 1) Scan result
    grid1 = (card(1, selected=True) + card(2, selected=True) + video_card() +
             card(3) + card(4) + card(5, selected=True) + card(6) + card(7) + card(8))
    p1 = panel(status=("ok", "Click images to select, then Grab."),
               grid_cards=grid1, count="21 found")
    with open(os.path.join(TPL, "screenshot-scan.html"), "w") as f:
        f.write(browser_page(p1, "nasjonalmuseet.no/collection", page_grid(6)))

    # 2) Settings — per-type folders
    grid2 = card(4) + card(2) + card(7) + card(1) + card(9) + card(3)
    p2 = panel(inner_settings=settings_drawer(),
               status=("scanning", "Scanning page…"), grid_cards=grid2, count="21 found")
    with open(os.path.join(TPL, "screenshot-settings.html"), "w") as f:
        f.write(browser_page(p2, "nasjonalmuseet.no/collection", page_grid(6)))

    # 3) Saved + open folder (video grabbed)
    grid3 = video_card(saved=True) + card(1, saved=True) + card(2, saved=True) + card(5) + card(8) + card(6)
    p3 = panel(status=("ok", "Downloaded 1 file."), saved_bar=saved_bar(),
               grid_cards=grid3, count="grab complete")
    with open(os.path.join(TPL, "screenshot-saved.html"), "w") as f:
        f.write(browser_page(p3, "nasjonalmuseet.no/collection", page_grid(6)))

    # 4) Marquee promo (1400×560)
    marquee = f'''<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="popup.css"><link rel="stylesheet" href="shared.css">
<style>:root{{--shot-w:1400px;--shot-h:560px;}}</style></head>
<body class="promo"><div class="promo-stage">
  <div class="promo-pad">
    <div class="logo-row"><img src="../assets/icon128.png" alt=""><span class="wordmark">Harpe</span></div>
    <h2>Grab any <span class="hl">image or video</span><br>from any page.</h2>
    <p>Scan the live page, pick what you want, download it. Works in your browser — no setup.</p>
    <div class="promo-chips"><span>Images</span><span>X / Twitter video</span><span>Gigapixel art</span><span>Private — nothing leaves your machine</span></div>
  </div>
  <div class="promo-float">{panel(status=("ok","Click images to select, then Grab."), grid_cards=card(1,selected=True)+card(2,selected=True)+video_card()+card(4)+card(7)+card(3), count="21 found")}</div>
</div></body></html>'''
    with open(os.path.join(TPL, "promo-marquee.html"), "w") as f:
        f.write(marquee)

    # 5) Small promo tile (440×280)
    small = f'''<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="popup.css"><link rel="stylesheet" href="shared.css">
<style>:root{{--shot-w:440px;--shot-h:280px;}}</style></head>
<body class="promo"><div class="promo-stage tile">
  <div class="promo-pad">
    <div class="logo-row"><img src="../assets/icon128.png" alt="" style="width:48px;height:48px"><span class="wordmark">Harpe</span></div>
    <h2>Grab any image<br>or <span class="hl">video</span>.</h2>
    <p>From any page. No setup.</p>
  </div>
</div></body></html>'''
    with open(os.path.join(TPL, "promo-small.html"), "w") as f:
        f.write(small)


if __name__ == "__main__":
    write_tiles()
    write_templates()
    print("assets →", ASSETS)
    print("templates →", TPL)
    print("render these at the sizes noted in each file's :root --shot-w/h")
