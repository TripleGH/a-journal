#!/usr/bin/env python3
"""
Render Come to the Fire word-carousel slides. BIG TYPE version (Nov 16, 2026).

Usage:
  python3 render_slides.py slides.json out_dir

slides.json:
  {"seed": 20261116, "slides": ["text one", "text two", ...]}

A newline inside a slide splits it: the part after the last newline is set
smaller, as a verse reference (for example "Romans 1:16").

Keep each slide SHORT: about 90 characters or fewer. Never more than 160.

Outputs:
  out_dir/feed/slide-01.jpg ... (1080x1080)
  out_dir/story/story-01.jpg ... (1080x1920)
"""
import json, sys, os, random, html
from pathlib import Path
from playwright.sync_api import sync_playwright

FONT_DIR = Path(__file__).parent / "fonts"  # the three Cormorant Garamond files sit next to this script

# Palette variants: (sky_top, sky_mid, horizon_warm, glow_rgba, ground)
PALETTES = [
    ("#0b0f1c", "#232638", "#b8743f", "255,168,92", "#090705"),   # amber dusk
    ("#0e0b14", "#2a1f2e", "#b3655a", "255,140,120", "#0a0607"),  # rose dusk
    ("#070b16", "#17233a", "#7a6a6c", "220,190,170", "#05070a"),  # blue hour
    ("#0a0e12", "#1c2a30", "#8a7550", "235,200,150", "#06080a"),  # teal-gray dawn
    ("#100c0a", "#2e2018", "#c47a3a", "255,175,95", "#0a0705"),   # ember
    ("#0c0d16", "#262a3d", "#9a7a72", "240,200,180", "#08080c"),  # violet haze
]

def silhouette_path(rng, kind, w, h, base):
    """Return an SVG path for a ground silhouette starting at y=base (0..1 of height)."""
    pts = []
    n = 14
    for i in range(n + 1):
        x = w * i / n
        if kind == "hills":
            y = h * (base + rng.uniform(-0.035, 0.035))
        else:  # treeline: jagged
            y = h * (base + rng.uniform(-0.02, 0.05))
        pts.append((x, y))
    d = f"M0,{h} L0,{pts[0][1]:.1f} "
    if kind == "hills":
        # smooth with quadratic curves
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            cx = (x0 + x1) / 2
            d += f"Q{x0:.1f},{y0:.1f} {cx:.1f},{(y0 + y1) / 2:.1f} "
        d += f"L{w},{pts[-1][1]:.1f} "
    else:
        for x, y in pts:
            d += f"L{x:.1f},{y:.1f} "
    d += f"L{w},{h} Z"
    return d, pts

def hill_y(pts, x):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0) if x1 != x0 else 0
            return y0 + (y1 - y0) * t
    return pts[-1][1]

def trees(rng, w, h, pts, count, ceiling=None):
    """Simple conifer silhouettes standing on the hill line (drawn under the hills).

    ceiling: a y value in px. No tree tip may rise above it, so a tree can never
    poke into the words. A tree that would end up too short is left out.
    """
    out = []
    for _ in range(count):
        x = rng.uniform(40, w - 40)
        th = rng.uniform(0.05, 0.13) * h
        ratio = rng.uniform(0.35, 0.5)
        y0 = hill_y(pts, x) + 8
        if ceiling is not None:
            th = min(th, (y0 - ceiling) / 0.93)  # the tip sits at y0 - 0.93 * th
            if th < 0.035 * h:
                continue
        tw = th * ratio
        # Plant the tree: its lowest branch line sits on the ground, so it never floats.
        yb = y0 + th * 0.19
        # conifer: three stacked triangles
        poly = []
        for k in range(3):
            yy = yb - th * (1 - k * 0.28)
            ww = tw * (0.45 + k * 0.3)
            poly.append(f"{x:.1f},{yy - th*0.12:.1f} {x - ww/2:.1f},{yy + th*0.25:.1f} {x + ww/2:.1f},{yy + th*0.25:.1f}")
        for p in poly:
            out.append(f'<polygon points="{p}" fill="#050403" opacity="0.98"/>')
    return "\n".join(out)

def font_size(text, story):
    """Big type. Legibility comes first (Gregg, Nov 16, 2026: about double the old size)."""
    n = len(text)
    if story:
        if n <= 36: return 124
        if n <= 60: return 110
        if n <= 90: return 96
        if n <= 120: return 84
        if n <= 160: return 72
        return 60
    if n <= 36: return 108
    if n <= 60: return 96
    if n <= 90: return 84
    if n <= 120: return 74
    if n <= 160: return 64
    return 54

def build_html(text, idx, total, story, seed, ceiling=None, pager=True):
    rng = random.Random(seed)
    w, h = (1080, 1920) if story else (1080, 1080)
    sky_top, sky_mid, horizon, glow, ground = PALETTES[(idx - 1) % len(PALETTES)]
    base = 0.82 if story else 0.82
    kind = rng.choice(["hills", "hills", "treeline"])
    path, pts = silhouette_path(rng, kind, w, h, base)
    tree_svg = trees(rng, w, h, pts, rng.randint(3, 6), ceiling) if kind == "treeline" else trees(rng, w, h, pts, rng.randint(0, 2), ceiling)
    # A newline splits off a verse reference, set smaller under the main words.
    parts = text.split("\n")
    main, ref = ("\n".join(parts[:-1]), parts[-1]) if len(parts) > 1 else (text, "")
    fs = font_size(main, story)
    safe = html.escape(main).replace("\n", "<br>")
    ref_html = f'<span class="ref">{html.escape(ref)}</span>' if ref else ""
    ornament = "✦"
    fonts = FONT_DIR.as_uri()
    text_top = "44%" if story else "42%"
    pager_html = f'<div class="pager">{idx}/{total}</div>' if pager else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
@font-face {{ font-family: 'Cormorant Garamond'; font-weight: 500; font-style: normal;
  src: url('{fonts}/cormorant-garamond-latin-500-normal.woff2') format('woff2'); }}
@font-face {{ font-family: 'Cormorant Garamond'; font-weight: 500; font-style: italic;
  src: url('{fonts}/cormorant-garamond-latin-500-italic.woff2') format('woff2'); }}
@font-face {{ font-family: 'Cormorant Garamond'; font-weight: 600; font-style: normal;
  src: url('{fonts}/cormorant-garamond-latin-600-normal.woff2') format('woff2'); }}
html,body {{ margin:0; padding:0; }}
.slide {{ position:relative; width:{w}px; height:{h}px; overflow:hidden;
  background: linear-gradient(180deg, {sky_top} 0%, {sky_mid} 46%, {horizon} 74%, {ground} 84%, #050403 100%); }}
.glow {{ position:absolute; inset:0;
  background: radial-gradient(ellipse 70% 20% at 50% {int(base*100)-5}%, rgba({glow},0.58) 0%, rgba({glow},0.20) 45%, rgba(0,0,0,0) 72%); }}
.clouds {{ position:absolute; inset:0; opacity:0.45; mix-blend-mode: screen;
  -webkit-mask-image: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.75) 45%, rgba(0,0,0,0.35) 70%, rgba(0,0,0,0) 82%);
  mask-image: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.75) 45%, rgba(0,0,0,0.35) 70%, rgba(0,0,0,0) 82%); }}
.ground {{ position:absolute; inset:0; }}
.vignette {{ position:absolute; inset:0;
  background: radial-gradient(ellipse 78% 70% at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55) 78%, rgba(0,0,0,0.85) 100%); }}
/* A soft dark pool behind the words so big white type always reads cleanly. */
.scrim {{ position:absolute; inset:0;
  background: radial-gradient(ellipse 62% 40% at 50% {text_top}, rgba(4,6,12,0.50) 0%, rgba(4,6,12,0.30) 55%, rgba(4,6,12,0) 100%); }}
.grain {{ position:absolute; inset:0; opacity:0.10; mix-blend-mode: overlay; }}
.text {{ position:absolute; left:50%; top:{text_top}; transform:translate(-50%,-50%);
  width:900px; text-align:center; text-wrap:balance; color:#fbf7ee;
  font-family:'Cormorant Garamond', Georgia, serif; font-weight:600; font-size:{fs}px; line-height:1.17;
  text-shadow: 0 3px 10px rgba(0,0,0,0.80), 0 0 34px rgba(0,0,0,0.60); letter-spacing:0; font-variant-numeric: lining-nums; }}
.text .orn {{ display:block; font-size:{max(24, int(fs*0.30))}px; opacity:0.85; margin-bottom:{int(fs*0.38)}px; letter-spacing:0; line-height:1; }}
.text .ref {{ display:block; margin-top:{int(fs*0.45)}px; font-size:{max(40, int(fs*0.62))}px; font-weight:500; font-style:italic; opacity:0.95; }}
.pager {{ position:absolute; left:0; right:0; bottom:{'88px' if story else '40px'}; text-align:center; color:#f5f0e6; opacity:0.85;
  font-family:'Cormorant Garamond', Georgia, serif; font-weight:600; font-size:{'34px' if story else '30px'}; letter-spacing:0.08em; font-variant-numeric: lining-nums; }}
</style></head>
<body>
<div class="slide">
  <div class="glow"></div>
  <svg class="clouds" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
    <filter id="cl" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.0022 0.0048" numOctaves="5" seed="{seed % 1000}" stitchTiles="stitch"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.95  0 0 0 0 0.88  0 0 0 0 0.80  0 0 0 1.6 -0.55"/>
      <feGaussianBlur stdDeviation="1.2"/>
    </filter>
    <rect width="{w}" height="{h}" filter="url(#cl)"/>
  </svg>
  <svg class="ground" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#0b0907"/><stop offset="1" stop-color="#030202"/>
      </linearGradient>
    </defs>
    {tree_svg}
    <path d="{path}" fill="url(#g)"/>
  </svg>
  <div class="vignette"></div>
  <div class="scrim"></div>
  <svg class="grain" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
    <filter id="gr"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="{(seed*7) % 1000}"/></filter>
    <rect width="{w}" height="{h}" filter="url(#gr)"/>
  </svg>
  <div class="text"><span class="orn">{ornament}</span>{safe}{ref_html}</div>
  {pager_html}
</div>
</body></html>"""

def shoot(page, hp, target, text, i, total, story, seed, pager=True):
    # Pass 1: lay out the words and measure where they end.
    hp.write_text(build_html(text, i, total, story, seed, pager=pager))
    page.goto(hp.as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(150)
    box = page.evaluate("(() => { const r = document.querySelector('.text').getBoundingClientRect(); return [r.top, r.bottom]; })()")
    # Pass 2: same scene, but no tree tip may come within 48px of the words.
    hp.write_text(build_html(text, i, total, story, seed, ceiling=box[1] + 48, pager=pager))
    page.goto(hp.as_uri())
    page.wait_for_timeout(250)
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(target), type="jpeg", quality=92, full_page=False)
    return box

def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2]).resolve()
    slides = spec["slides"]
    seed_base = spec.get("seed", 20260914)
    total = len(slides)
    (out / "feed").mkdir(parents=True, exist_ok=True)
    (out / "story").mkdir(parents=True, exist_ok=True)
    (out / "html").mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for story in (False, True):
            w, h = (1080, 1920) if story else (1080, 1080)
            limit = h * (0.78 if story else 0.76)  # the words must end above the ground line
            page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            for i, text in enumerate(slides, start=1):
                seed = seed_base + i  # same seed for feed and story so scenes match
                kind = "story" if story else "feed"
                hp = out / "html" / f"{kind}-{i:02d}.html"
                target = out / kind / f"{'story' if story else 'slide'}-{i:02d}.jpg"
                top, bottom = shoot(page, hp, target, text, i, total, story, seed)
                flag = "" if (top >= 60 and bottom <= limit) else "  <-- WORDS DO NOT FIT, SHORTEN THIS SLIDE"
                print(f"wrote {target.name}: {len(text)} chars, words span y={top:.0f}..{bottom:.0f}{flag}")
            if story:
                # One extra story frame with no page counter, for posting a single frame.
                shoot(page, out / "html" / "story-single.html", out / "story" / "story-single.jpg", slides[0], 1, total, True, seed_base + 1, pager=False)
                print("wrote story-single.jpg (slide 1, no counter)")
            page.close()
        browser.close()

if __name__ == "__main__":
    main()
