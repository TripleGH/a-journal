#!/usr/bin/env python3
"""
Make the Come to the Fire slides. New look, November 17, 2026.

    python3 tools/make_slides.py slides.json out_dir [--no-record]

slides.json:   {"seed": 20261118, "slides": ["text one", "text two", ...]}
  seed    the post date as a number (YYYYMMDD). It decides which pictures get painted.
  slides  the words. A line break inside a slide splits off a verse reference,
          which is set smaller and in italics (for example "Romans 1:16").
  looks   optional. [{"family": "sea", "mood": "rose_dawn"}, null, ...] picks a picture by hand.

What this tool guarantees. It stops with an error instead of making a bad slide.
  1. Every slide gets its own picture, painted by code (tools/scenes.py). No people, ever.
  2. No picture type is used twice in one set. No set repeats an earlier set (looks.json).
     The first slide never repeats the picture type of the last five first slides.
  3. The words are the SAME SIZE on every slide of the set, as big as the longest slide allows.
  4. The words stay inside a safe box, with room on every side and the most room at the bottom.
  5. Strong contrast behind every word, measured on the finished picture.

It writes:
  out_dir/feed/slide-01.jpg ...    1080 x 1350, Instagram's 4:5 portrait size
  out_dir/story/story-single.jpg   1080 x 1920, slide 1 with the words inside the story safe zone
  out_dir/sheet.jpg                every slide side by side, for a quick look
  out_dir/report.txt               the checks and their numbers
"""
import html
import io
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
import scenes  # noqa: E402

F = np.float32
TOOLS = Path(__file__).parent
REPO = TOOLS.parent
FONT_DIR = TOOLS / "fonts"
LOOKS_FILE = REPO / "looks.json"

# The safe boxes. Words never leave them.
#   Feed: Instagram's profile grid crops a 4:5 post to its middle 3:4, and older views crop to a
#         square. This box sits inside both crops.
#   Story: Instagram covers the top (name bar) and the bottom (reply bar) of a story.
FEED = dict(name="feed", W=1080, H=1350, left=100, right=100, top=150, bottom=190)
STORY = dict(name="story", W=1080, H=1920, left=100, right=100, top=270, bottom=400)

FONT_MAX, FONT_MIN = 104, 72          # px on a 1080 px wide slide
FONT_WEIGHT = 700                     # bold: holds up best on a phone and for older eyes
LINE_H = 1.16
SLACK = 14                            # px kept free inside the box for ink that overhangs (quote marks, italics)
REF_SIZE, REF_GAP = 0.60, 0.50        # verse reference: size and gap, as parts of the main size
TEXT_RGB = (251, 247, 238)            # warm white
MAX_CHARS = 170
VERSIONS = 4                          # pictures painted per slide; the calmest behind the words is kept
MIN_TYPICAL, MIN_WORST = 6.0, 4.0     # contrast floors (the web standard for big type is 3.0)

WEAK_END = {"a", "an", "the", "of", "to", "in", "on", "at", "and", "or", "but", "for", "with", "my", "our",
            "your", "his", "her", "its", "their", "be", "is", "are", "was", "were", "that", "this", "we", "i",
            "he", "she", "it", "as", "by", "from", "so", "if", "not", "no"}

# Words in a slide that nudge the choice of picture. A nudge, never a rule.
HINTS = [
    (r"\b(morning|dawn|sunrise|awake|awakens|daybreak|first thought)\b",
     ["sea", "ridges", "cloudsea", "meadow", "lake", "field"], ["rose_dawn", "gold_sunrise", "teal_dawn", "mint_morning"]),
    (r"\b(evening|night|sleep|rest|dark|darkness|midnight)\b",
     ["stars", "lake", "dunes", "tree", "aurora"], ["violet_dusk", "blue_hour", "moonlit", "deep_night"]),
    (r"\b(praise|glory|worship|hallelujah|thank|thanks|rejoice|joy|light|shine)\b",
     ["rays", "cloudsea", "sea", "aurora"], ["gold_sunrise", "storm_light", "amber_haze", "fire_sunset"]),
    (r"\b(heaven|heavens|star|stars|sky|creation|created|eternal|eternity)\b",
     ["stars", "aurora", "cloudsea"], ["deep_night", "moonlit"]),
    (r"\b(water|waters|river|sea|thirst|well|peace|still|calm|quiet)\b",
     ["lake", "sea"], ["blue_hour", "teal_dawn", "rose_dawn"]),
    (r"\b(mountain|mountains|rock|refuge|fortress|strength|strong|high)\b", ["ridges", "pines", "lake"], []),
    (r"\b(desert|wilderness|wait|waiting|dry|valley)\b", ["dunes", "ridges"], ["amber_haze", "autumn_ember"]),
    (r"\b(seed|harvest|grow|growth|fruit|field|sow|plant|root|roots|tree|branch|vine|garden)\b",
     ["field", "tree", "meadow", "pines"], []),
    (r"\b(fire|flame|burn|revival|candle|lamp)\b", ["bokeh", "tree", "dunes"], ["candle_gold", "fire_sunset", "autumn_ember"]),
    (r"\b(storm|trouble|fear|afraid|trial|suffer|pain|sorrow|grief)\b", ["rays", "pines", "ridges"], ["storm_light", "blue_hour"]),
    (r"\b(love|heart|grace|mercy|tender)\b", ["sea", "lake", "bokeh", "field"], ["rose_dawn", "rose_lights", "magenta_twilight"]),
    (r"\b(pray|prayer|presence|holy|spirit)\b", ["bokeh", "pines", "stars", "cloudsea"], ["candle_gold", "teal_dawn"]),
]


def stop(msg):
    print("STOPPED: " + msg)
    sys.exit(1)


# --------------------------------------------------------------------------- choosing the pictures

def hints_for(text):
    fams, moods = set(), set()
    low = text.lower()
    for pat, fs, ms in HINTS:
        if re.search(pat, low):
            fams.update(fs)
            moods.update(ms)
    return fams, moods


def choose_looks(texts, seed, history, forced):
    """One picture type and one light for each slide. Different within the set, and different
    from the sets before it."""
    fams = list(scenes.FAMILIES)
    recent_first = [h[0]["family"] for h in history[-5:] if h]
    recent_pairs = {(l["family"], l["mood"]) for h in history[-2:] for l in h}
    yesterday = {l["family"] for l in history[-1]} if history else set()
    old = {tuple((l["family"], l["mood"]) for l in h) for h in history}
    for attempt in range(40):
        rng = np.random.default_rng([int(seed), 77, attempt])
        used_f, used_m, out = set(), set(), []
        for i, text in enumerate(texts):
            if forced and i < len(forced) and forced[i]:
                f, mo = forced[i]["family"], forced[i]["mood"]
            else:
                hf, hm = hints_for(text)
                best = None
                for f in fams:
                    if f in used_f and len(used_f) < len(fams):
                        continue
                    if i == 0 and f in recent_first and len(set(recent_first)) < len(fams):
                        continue
                    s = rng.random() + (0.9 if f in hf else 0.0) - (0.6 if f in yesterday else 0.0)
                    if best is None or s > best[0]:
                        best = (s, f)
                f = best[1]
                bm = None
                for mo in scenes.FAMILIES[f][1]:
                    s = rng.random() + (0.7 if mo in hm else 0.0) - (0.8 if mo in used_m else 0.0) \
                        - (0.6 if (f, mo) in recent_pairs else 0.0)
                    if bm is None or s > bm[0]:
                        bm = (s, mo)
                mo = bm[1]
            used_f.add(f)
            used_m.add(mo)
            out.append({"family": f, "mood": mo})
        if tuple((l["family"], l["mood"]) for l in out) not in old:
            return out
    stop("could not find a set of pictures that differs from every earlier set.")


# --------------------------------------------------------------------------- setting the words

BASE_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'CTF Serif'; font-weight:{w}; font-style:normal; src:url('{fonts}/{main}') format('woff2'); }}
@font-face {{ font-family:'CTF Serif'; font-weight:600; font-style:italic; src:url('{fonts}/{ital}') format('woff2'); }}
html,body {{ margin:0; padding:0; background:transparent; }}
#c {{ position:relative; overflow:hidden; }}
#b {{ position:absolute; text-align:center; color:rgb({r},{g},{b}); font-family:'CTF Serif',Georgia,serif;
     font-weight:{w}; line-height:{lh}; font-kerning:normal; font-variant-numeric:lining-nums;
     text-shadow:0 2px 4px rgba(0,0,0,.60), 0 0 16px rgba(0,0,0,.50), 0 0 40px rgba(0,0,0,.40); }}
.ln {{ white-space:nowrap; }}
.ref {{ font-weight:600; font-style:italic; line-height:1.2; white-space:nowrap; }}
</style></head><body></body></html>"""

MEASURE_JS = """async ([words, refs, w]) => {
  await document.fonts.load(w + " 100px 'CTF Serif'");
  await document.fonts.load("italic 600 100px 'CTF Serif'");
  await document.fonts.ready;
  const c = document.createElement('canvas').getContext('2d');
  c.font = w + " 100px 'CTF Serif'";
  const out = {words: words.map(x => c.measureText(x).width), space: c.measureText(' ').width};
  c.font = "italic 600 100px 'CTF Serif'";
  out.refs = refs.map(x => c.measureText(x).width);
  return out;
}"""


def split_slide(text):
    parts = text.strip().split("\n")
    if len(parts) > 1:
        return " ".join(" ".join(parts[:-1]).split()), parts[-1].strip()
    return " ".join(text.split()), ""


def break_lines(words, widths, space, maxw):
    """Fewest lines that fit, then the most even split. Prefers to turn after punctuation and
    never leaves a small word like 'the' or 'of' hanging at the end of a line."""
    n = len(words)
    if any(w > maxw for w in widths):
        return None
    pre = [0.0]
    for w in widths:
        pre.append(pre[-1] + w)

    def lw(i, j):
        return pre[j] - pre[i] + space * (j - i - 1)

    L, cur = 1, 0.0
    for w in widths:
        if cur == 0:
            cur = w
        elif cur + space + w <= maxw:
            cur += space + w
        else:
            L, cur = L + 1, w
    target = lw(0, n) / L
    INF = float("inf")
    best = [[INF] * (L + 1) for _ in range(n + 1)]
    back = [[-1] * (L + 1) for _ in range(n + 1)]
    best[0][0] = 0.0
    for j in range(1, n + 1):
        for l in range(1, min(L, j) + 1):
            for i in range(l - 1, j):
                if best[i][l - 1] == INF:
                    continue
                w = lw(i, j)
                if w > maxw:
                    continue
                c = best[i][l - 1] + ((w - target) / maxw) ** 2
                if j < n:
                    last = words[j - 1]
                    if last.lower().strip("“”\"'‘’.,;:!?()") in WEAK_END:
                        c += 0.02
                    if last[-1:] in ",;:":
                        c -= 0.012
                    if last.rstrip("”’\"'")[-1:] in ".!?":
                        c -= 0.04          # a sentence ends here: the best place to turn
                    elif j - 2 >= i and words[j - 2].rstrip("”’\"'")[-1:] in ".!?":
                        c += 0.06          # never leave the first word of a new sentence hanging
                elif j - i == 1 and L > 1:
                    c += 0.03
                if c < best[j][l]:
                    best[j][l], back[j][l] = c, i
    if best[n][L] == INF:
        return None
    out, j, l = [], n, L
    while l > 0:
        i = back[j][l]
        out.append(" ".join(words[i:j]))
        j, l = i, l - 1
    return out[::-1]


def layout(slide, size, maxw):
    k = size / 100.0
    lines = break_lines(slide["words"], [w * k for w in slide["widths"]], slide["space"] * k, maxw)
    if lines is None or slide["refw"] * k * REF_SIZE > maxw:
        return None, 0.0
    h = len(lines) * size * LINE_H + ((REF_GAP + REF_SIZE * 1.2) * size if slide["ref"] else 0.0)
    return lines, h


def layer_html(spec, lines, ref, size, top):
    inner = "".join(f'<div class="ln">{html.escape(l)}</div>' for l in lines)
    if ref:
        inner += (f'<div class="ref" style="font-size:{size * REF_SIZE:.2f}px;margin-top:{size * REF_GAP:.2f}px">'
                  f'{html.escape(ref)}</div>')
    return (f'<div id="c" style="width:{spec["W"]}px;height:{spec["H"]}px"><div id="b" style="left:{spec["left"]}px;'
            f'width:{spec["W"] - spec["left"] - spec["right"]}px;top:{top:.2f}px;font-size:{size}px">{inner}</div></div>')


def shoot_layer(page, spec, lines, ref, size, top):
    page.set_viewport_size({"width": spec["W"], "height": spec["H"]})
    page.evaluate("h => { document.body.innerHTML = h; }", layer_html(spec, lines, ref, size, top))
    page.evaluate("document.fonts.ready")
    png = page.screenshot(type="png", omit_background=True, clip={"x": 0, "y": 0, "width": spec["W"], "height": spec["H"]})
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGBA")).astype(F) / 255.0


# --------------------------------------------------------------------------- light, contrast, compositing

def to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def lum(lin):
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


TEXT_LUM = float(lum(to_lin(np.array(TEXT_RGB, np.float64) / 255.0)))


def glyphs_of(layer):
    """Where the letters themselves are (not their shadow)."""
    l = lum(to_lin(layer[..., :3]))
    return ((layer[..., 3] > 0.5) & (l > 0.4)).astype(np.uint8)


def words_mask(glyph):
    """A soft shape around the words: 1 where the letters are, fading to 0 a little way out."""
    m = cv2.GaussianBlur(glyph.astype(F), (0, 0), 30)
    return cv2.GaussianBlur(np.clip(m / 0.08, 0, 1), (0, 0), 26).astype(np.float64)


def brightness_behind(bg, m):
    """How bright the picture is where the words will sit (0 dark .. 1 white)."""
    L = lum(to_lin(bg.astype(np.float64)))
    return float((L * m).sum() / max(m.sum(), 1.0))


def expose_for_words(bg, m, glyph, cap):
    """Tone the picture for reading, without turning it muddy.
    1. A very bright picture is brought down a little, all over.
    2. The rows that sit behind the words are dimmed evenly from edge to edge, with soft top and
       bottom edges. A whole row gets one factor, so the picture keeps its own shapes and light
       (a sun stays a sun) and no dark patch appears behind the words.
    3. Whatever is darkened gets its colour deepened, so a pale sky turns rich, not grey."""
    lin = to_lin(bg.astype(np.float64))
    L = lum(lin)
    mean_l = float((L * m).sum() / max(m.sum(), 1.0))
    gain = float(np.clip((0.24 / max(mean_l, 1e-6)) ** 0.7, 0.55, 1.0))
    rows = m.max(axis=1)
    rows = np.maximum(rows, gaussian_filter1d(rows, 60, mode="nearest"))     # long soft tails above and below
    xs = np.nonzero(glyph.any(axis=0))[0]
    x0, x1 = max(int(xs.min()) - 40, 0), min(int(xs.max()) + 40, L.shape[1])
    lb = cv2.GaussianBlur((L * gain).astype(F), (0, 0), 10)
    p90 = np.percentile(lb[:, x0:x1], 90, axis=1)
    f = gaussian_filter1d(np.clip((cap / np.maximum(p90, 1e-6)) ** 0.85, 0.12, 1.0), 28, mode="nearest")
    total = (gain * (1 - rows * (1 - f)))[:, None, None]
    lin = lin * total
    ln = lum(lin)[..., None]
    lin = np.clip(ln + (lin - ln) * (1 + 0.45 * (1 - total)), 0, None)
    out = to_srgb(lin).astype(F)
    soft = cv2.GaussianBlur(out, (0, 0), 3.5)                      # quiet the fine detail under the letters
    k = (0.75 * np.clip(m, 0, 1))[..., None].astype(F)
    return out * (1 - k) + soft * k, gain


def contrast_of(final, glyph):
    """Contrast between the letters and the picture right around them."""
    ring = cv2.dilate(glyph, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))) \
        & (1 - cv2.dilate(glyph, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))))
    L = cv2.GaussianBlur(lum(to_lin(final.astype(np.float64))).astype(F), (0, 0), 1.5)
    p50, p95 = np.percentile(L[ring > 0], [50, 95])
    return (TEXT_LUM + 0.05) / (p50 + 0.05), (TEXT_LUM + 0.05) / (p95 + 0.05)


def make_one(page, spec, slide, size, look, seed, variant=None):
    """Paint one picture, set the words on it, check it. Returns (image 0..255 uint8, facts)."""
    W, H = spec["W"], spec["H"]
    box_w, box_h = W - spec["left"] - spec["right"], H - spec["top"] - spec["bottom"]
    lines, h = layout(slide, size, box_w - SLACK)
    if lines is None or h > box_h + 0.5:
        stop(f"the words do not fit the {spec['name']} box at size {size}. This should not happen; tell Gregg.")
    layer = shoot_layer(page, spec, lines, slide["ref"], size, spec["top"] + (box_h - h) / 2)
    glyph = glyphs_of(layer)
    ys, xs = np.nonzero(glyph)
    if len(ys) == 0:
        stop("no letters were drawn. Is the font file missing from tools/fonts?")
    # centre the ink itself in the safe box (line boxes carry uneven air around the letters)
    dy = int(round(spec["top"] + box_h / 2 - (ys.min() + ys.max() + 1) / 2))
    dx = int(round(spec["left"] + box_w / 2 - (xs.min() + xs.max() + 1) / 2))
    if dy or dx:
        layer = np.roll(layer, (dy, dx), axis=(0, 1))
        if dy > 0:
            layer[:dy] = 0
        elif dy < 0:
            layer[dy:] = 0
        if dx > 0:
            layer[:, :dx] = 0
        elif dx < 0:
            layer[:, dx:] = 0
        glyph = glyphs_of(layer)
        ys, xs = np.nonzero(glyph)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    margins = dict(left=x0, right=W - x1, top=y0, bottom=H - y1)
    for side in ("left", "right", "top", "bottom"):
        if margins[side] < spec[side] - 3:
            stop(f"words reach {margins[side]} px from the {side} edge on the {spec['name']} picture; "
                 f"the rule is {spec[side]} px. Shorten that slide.")
    m = words_mask(glyph)
    if variant is None:        # paint a few versions; keep the one that is calmest behind the words
        tries = [(brightness_behind(b, m), j, b) for j, b in
                 ((j, scenes.paint(look["family"], look["mood"], seed + 1000 * j, W, H)) for j in range(VERSIONS))]
        _, variant, bg = min(tries, key=lambda t: t[0])
    else:
        bg = scenes.paint(look["family"], look["mood"], seed + 1000 * variant, W, H)
    a = layer[..., 3:4]
    cap, final, typ, worst, gain = 0.24, None, 0.0, 0.0, 1.0
    for _ in range(10):
        toned, gain = expose_for_words(bg, m, glyph, cap)
        final = toned * (1 - a) + layer[..., :3] * a
        typ, worst = contrast_of(final, glyph)
        if typ >= MIN_TYPICAL and worst >= MIN_WORST:
            break
        cap *= 0.8
    else:
        stop(f"could not reach the contrast floor on a {look['family']} picture (typical {typ:.1f}, worst {worst:.1f}).")
    img = (np.clip(final, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img, dict(lines=len(lines), margins=margins, typical=typ, worst=worst, gain=gain, variant=variant)


# --------------------------------------------------------------------------- main

def load_history():
    if LOOKS_FILE.exists():
        return json.loads(LOOKS_FILE.read_text())
    return {"sets": []}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        stop("usage: python3 tools/make_slides.py slides.json out_dir [--no-record]")
    record = "--no-record" not in argv
    spec_in = json.loads(Path(args[0]).read_text())
    out = Path(args[1]).resolve()
    seed = int(spec_in.get("seed", 0))
    texts = [t for t in spec_in["slides"] if t.strip()]
    if not seed:
        stop('slides.json needs "seed": the post date as a number, like 20261118.')
    if not 3 <= len(texts) <= 10:
        stop(f"{len(texts)} slides. Use 5 to 7 (never fewer than 3 or more than 10).")
    slides = []
    for i, t in enumerate(texts, 1):
        main_text, ref = split_slide(t)
        if len(main_text) > MAX_CHARS:
            stop(f"slide {i} has {len(main_text)} characters. The limit is {MAX_CHARS}. Shorten it.")
        slides.append(dict(text=main_text, ref=ref, words=main_text.split()))

    hist = load_history()
    earlier = [s["looks"] for s in hist["sets"] if int(s["seed"]) != seed]
    looks = choose_looks(texts, seed, earlier, spec_in.get("looks"))

    for d in ("feed", "story", "work"):
        (out / d).mkdir(parents=True, exist_ok=True)
    base = out / "work" / "base.html"
    base.write_text(BASE_HTML.format(fonts=FONT_DIR.as_uri(), w=FONT_WEIGHT, lh=LINE_H,
                                     main=f"cormorant-garamond-latin-{FONT_WEIGHT}-normal.woff2",
                                     ital="cormorant-garamond-latin-600-italic.woff2",
                                     r=TEXT_RGB[0], g=TEXT_RGB[1], b=TEXT_RGB[2]))
    report = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto(base.as_uri())
        flat = [w for s in slides for w in s["words"]]
        m = page.evaluate(MEASURE_JS, [flat, [s["ref"] for s in slides], str(FONT_WEIGHT)])
        k = 0
        for s, rw in zip(slides, m["refs"]):
            s["widths"], s["space"], s["refw"] = m["words"][k:k + len(s["words"])], m["space"], rw
            k += len(s["words"])

        # one size for the whole set: the biggest at which the longest slide still fits its box
        box_w = FEED["W"] - FEED["left"] - FEED["right"]
        box_h = FEED["H"] - FEED["top"] - FEED["bottom"]
        size = None
        for cand in range(FONT_MAX, FONT_MIN - 1, -1):
            if all((lambda r: r[0] is not None and r[1] <= box_h)(layout(s, cand, box_w - SLACK)) for s in slides):
                size = cand
                break
        if size is None:
            worst_i = max(range(len(slides)), key=lambda i: len(slides[i]["text"]))
            stop(f"slide {worst_i + 1} is too long to fit at the smallest text size ({FONT_MIN}). Shorten it.")

        feed = []
        for i, (s, look) in enumerate(zip(slides, looks), 1):
            img, facts = make_one(page, FEED, s, size, look, seed * 100 + i)
            if i == 1:
                first_variant = facts["variant"]
            Image.fromarray(img).save(out / "feed" / f"slide-{i:02d}.jpg", quality=92, subsampling=0, optimize=True)
            feed.append(img)
            mg = facts["margins"]
            report.append(f"slide {i}: {look['family']:9s} {look['mood']:17s} {len(s['text']):3d} chars, {facts['lines']} lines, "
                          f"margins L{mg['left']} R{mg['right']} T{mg['top']} B{mg['bottom']}, "
                          f"contrast typical {facts['typical']:.1f} worst {facts['worst']:.1f}")
        story, facts = make_one(page, STORY, slides[0], size, looks[0], seed * 100 + 1, variant=first_variant)
        Image.fromarray(story).save(out / "story" / "story-single.jpg", quality=92, subsampling=0, optimize=True)
        mg = facts["margins"]
        report.append(f"story  : {looks[0]['family']:9s} {looks[0]['mood']:17s} margins L{mg['left']} R{mg['right']} "
                      f"T{mg['top']} B{mg['bottom']}, contrast typical {facts['typical']:.1f} worst {facts['worst']:.1f}")
        browser.close()

    # contact sheet
    th, gap = 540, 12
    tw, sw = int(th * 1080 / 1350), int(th * 1080 / 1920)
    cols = min(len(feed) + 1, 4)
    rows = (len(feed) + 1 + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (24, 24, 24))
    for i, img in enumerate(feed):
        sheet.paste(Image.fromarray(img).resize((tw, th), Image.LANCZOS),
                    (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    i = len(feed)
    sheet.paste(Image.fromarray(story).resize((sw, th), Image.LANCZOS),
                (gap + (i % cols) * (tw + gap) + (tw - sw) // 2, gap + (i // cols) * (th + gap)))
    sheet.save(out / "sheet.jpg", quality=90)

    fams = [l["family"] for l in looks]
    head = [f"text size on every slide: {size} px (limits {FONT_MIN} to {FONT_MAX})",
            f"picture types: {', '.join(fams)}",
            f"no picture type repeated: {'yes' if len(set(fams)) == len(fams) else 'NO'}",
            f"contrast floors: typical {MIN_TYPICAL}, worst {MIN_WORST} (web standard for big type: 3.0)"]
    text = "\n".join(head + report) + "\n"
    (out / "report.txt").write_text(text)
    (out / "looks.json").write_text(json.dumps(looks, indent=1) + "\n")
    print(text, end="")
    if record:
        hist["sets"] = [s for s in hist["sets"] if int(s["seed"]) != seed] + [{"seed": seed, "looks": looks}]
        LOOKS_FILE.write_text(json.dumps(hist, indent=1) + "\n")
        print(f"recorded this set in {LOOKS_FILE.name} (commit it with the pictures)")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
