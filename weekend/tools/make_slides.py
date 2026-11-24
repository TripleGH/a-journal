#!/usr/bin/env python3
"""
Make the Come to the Fire slides. The garden look, November 20, 2026.

    python3 tools/make_slides.py slides.json out_dir [--no-record]
    python3 tools/make_slides.py --list            (prints the picture types and the colour stories)

slides.json:   {"seed": 20261123, "slides": ["text one", "text two", ...]}
  seed    the post date as a number (YYYYMMDD). It decides which pictures get painted.
  slides  the words. A line break inside a slide splits off a verse reference,
          which is set smaller, with a small leaf ornament on each side.
  looks   optional. [{"family": "trellis", "mood": "blush"}, null, ...] picks a picture by hand
          (null lets the tool choose). Run with --list to see the names.
  style   optional. "upright" sets the words in upright letters instead of the swash italic.
  hook    optional. true makes slide 1 a headline: one short line, set bigger than the other slides
          (used for the weekend posts). The other slides still share one size. Without it, nothing changes.

What this tool guarantees. It stops with a plain message instead of making a bad slide.
  1. Every slide gets its own picture, painted by code (tools/garden.py): flowers, leaves, garlands,
     lattice, stripes, fine gold lines. No photos, no AI pictures, no people, nothing that looks like paper.
  2. No picture type and no colour story is used twice in one set. No set repeats an earlier set
     (looks.json). The first slide never repeats the picture type of the last five first slides.
  3. The words are the SAME SIZE on every slide of the set, as big as the longest slide allows.
  4. The words stay inside a safe box, with room on every side and the most room at the bottom.
  5. No flower, leaf or line ever sits behind a word. Strong contrast, measured on the finished slide.

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
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
import garden  # noqa: E402

F = np.float32
TOOLS = Path(__file__).parent
REPO = TOOLS.parent
FONT_DIR = TOOLS / "fonts"
LOOKS_FILE = REPO / "looks.json"
FONT_ITALIC, FONT_UPRIGHT = "EBGaramond-Italic-600.woff2", "EBGaramond-600.woff2"

# The safe boxes. Words never leave them.
#   Feed: Instagram's profile grid crops a 4:5 post to its middle 3:4, and older views crop to a
#         square. This box sits inside both crops.
#   Story: Instagram covers the top (name bar) and the bottom (reply bar) of a story.
FEED = dict(name="feed", W=1080, H=1350, left=100, right=100, top=150, bottom=190)
STORY = dict(name="story", W=1080, H=1920, left=100, right=100, top=270, bottom=400)

FONT_MAX, FONT_MIN = 96, 72           # px on a 1080 px wide slide
ROOM = 110                            # px of the safe box left free, top and bottom together, so the picture has room.
ROOM_MIN_FONT = 80                    # the words give up that room before they drop below this size
LINE_H = 1.18
SLACK = 34                            # px kept free inside the box for ink that overhangs (swashes, quote marks)
REF_SIZE, REF_GAP = 0.60, 0.55        # verse reference: size and gap, as parts of the main size
MAX_CHARS = 170
TRIES = 4                             # pictures tried per slide before giving up
MIN_TYPICAL, MIN_WORST = 6.0, 4.0     # contrast floors (the web standard for big type is 3.0)
PLAIN_CAPS = set("IJ")                # capitals that stay plain: their swash forms are easy to misread
HOOK_MAX, HOOK_STEP_UP = 132, 10      # headline (slide 1 of a "hook" set): its biggest size, and how much bigger than the other slides it must be
HOOK_ROOM = 300                       # px of the safe box the headline leaves free, so slide 1 has air and picture
HOOK_MAX_WORDS, HOOK_MAX_CHARS = 14, 80

WEAK_END = {"a", "an", "the", "of", "to", "in", "on", "at", "and", "or", "but", "for", "with", "my", "our",
            "your", "his", "her", "its", "their", "be", "is", "are", "was", "were", "that", "this", "we", "i",
            "he", "she", "it", "as", "by", "from", "so", "if", "not", "no"}

# Words in a slide that nudge the choice of colour story or picture. A nudge, never a rule.
MOOD_HINTS = [
    (r"\b(morning|dawn|sunrise|awake|awakens|joy|rejoice|praise|glory|light|shine|thank|thanks)\b", ["butter", "peach", "blush", "ivory"]),
    (r"\b(night|midnight|dark|darkness|sleep|star|stars)\b", ["midnight", "plum", "lilac", "porcelain"]),
    (r"\b(peace|rest|still|calm|quiet|water|waters|river)\b", ["sky", "sage", "mint", "porcelain"]),
    (r"\b(love|loved|heart|grace|mercy|tender|comfort|comforts)\b", ["blush", "rosewater", "peach"]),
    (r"\b(pray|prayer|prayed|presence|holy|spirit|worship)\b", ["lilac", "dove", "ivory", "porcelain"]),
    (r"\b(pain|suffer|suffered|suffering|sorrow|grief|hurt|trial|trouble|fear|afraid)\b", ["dove", "sage", "lilac", "sky"]),
    (r"\b(grow|growth|seed|garden|fruit|vine|harvest|plant|root|roots)\b", ["sage", "mint", "butter"]),
]
FAMILY_HINTS = [
    (r"\b(garden|grow|growth|seed|plant|harvest|sow)\b", ["border", "trellis"]),
    (r"\b(branch|branches|vine|tree|abide|root|roots)\b", ["branch", "trellis"]),
    (r"\b(crown|king|kingdom|throne|glory|holy)\b", ["frame", "arch"]),
    (r"\b(home|house|door|gate|welcome)\b", ["arch", "trellis"]),
]


def stop(msg):
    print("STOPPED: " + msg)
    sys.exit(1)


# --------------------------------------------------------------------------- setting the words

BASE_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'CTF Text'; font-weight:600; font-style:italic; src:url('{fonts}/{ital}') format('woff2'); }}
@font-face {{ font-family:'CTF Text'; font-weight:600; font-style:normal; src:url('{fonts}/{upr}') format('woff2'); }}
html,body {{ margin:0; padding:0; background:transparent; }}
#c {{ position:relative; overflow:hidden; }}
.txt {{ font-family:'CTF Text',Georgia,serif; font-weight:600; font-style:{style}; line-height:{lh}; font-kerning:normal;
       font-feature-settings:"kern","liga","lnum","calt"; }}
.sw {{ font-feature-settings:"kern","liga","lnum","calt","swsh"; }}
.dl {{ font-feature-settings:"kern","liga","lnum","calt","dlig"; }}
#b {{ position:absolute; text-align:center; }}
.ln {{ white-space:nowrap; }}
.ref {{ white-space:nowrap; line-height:1.25; }}
.orn {{ opacity:.62; font-style:normal; }}
#m {{ position:absolute; left:-20000px; top:0; white-space:nowrap; font-size:100px; }}
</style></head><body></body></html>"""

MEASURE_JS = """async ([words, refs]) => {
  await document.fonts.load("italic 600 100px 'CTF Text'");
  await document.fonts.load("600 100px 'CTF Text'");
  await document.fonts.ready;
  const host = document.createElement('div');
  host.id = 'm'; host.className = 'txt';
  document.body.appendChild(host);
  const w = h => { host.innerHTML = '<span>' + h + '</span>'; return host.firstChild.getBoundingClientRect().width; };
  const out = {words: words.map(w), refs: refs.map(w), space: w('n n') - w('nn')};
  host.remove();
  return out;
}"""


def mark_word(w):
    """One word as HTML. A word that starts with a capital gets the swash form of that capital,
    except I and J (kept plain so that "I", "Jesus" and "John" can never be misread) and words in
    all capitals such as NLT."""
    letters = [c for c in w if c.isalpha()]
    body = html.escape(w).replace("ct", '<span class="dl">ct</span>')     # the one fancy ligature that stays easy to read
    if letters and letters[0].isupper() and letters[0] not in PLAIN_CAPS \
            and not (len(letters) > 1 and all(c.isupper() for c in letters)):
        return f'<span class="sw">{body}</span>'
    return body


def mark_ref(ref):
    inner = " ".join(mark_word(w) for w in ref.split())
    return f'<span class="orn">☙</span>&nbsp;{inner}&nbsp;<span class="orn">❧</span>'


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
        out.append((i, j))
        j, l = i, l - 1
    return out[::-1]


def layout(slide, size, maxw):
    """Lines for one slide at one size: a list of (first word, last word + 1), and the height."""
    k = size / 100.0
    spans = break_lines(slide["words"], [w * k for w in slide["widths"]], slide["space"] * k, maxw)
    if spans is None or slide["refw"] * k * REF_SIZE > maxw:
        return None, 0.0
    h = len(spans) * size * LINE_H + ((REF_GAP + REF_SIZE * 1.25) * size if slide["ref"] else 0.0)
    return spans, h


def layer_html(spec, slide, spans, size, top, colour):
    inner = "".join('<div class="ln"><span class="l">' + " ".join(slide["marks"][i:j]) + "</span></div>" for i, j in spans)
    if slide["ref"]:
        inner += (f'<div class="ref" style="font-size:{size * REF_SIZE:.2f}px;margin-top:{size * REF_GAP:.2f}px">'
                  f'<span class="l">{mark_ref(slide["ref"])}</span></div>')
    return (f'<div id="c" style="width:{spec["W"]}px;height:{spec["H"]}px"><div id="b" class="txt" style="left:{spec["left"]}px;'
            f'width:{spec["W"] - spec["left"] - spec["right"]}px;top:{top:.2f}px;font-size:{size}px;color:{colour}">{inner}</div></div>')


LINES_JS = "() => [...document.querySelectorAll('.l')].map(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })"


def shoot_words(page, spec, slide, spans, size, colour):
    """Set the words, photograph them on a clear background, and centre the ink in the safe box.
    Returns the picture of the words (RGBA, 0..1), where the ink is, and a box for each line."""
    W, H = spec["W"], spec["H"]
    box_w, box_h = W - spec["left"] - spec["right"], H - spec["top"] - spec["bottom"]
    h = len(spans) * size * LINE_H + ((REF_GAP + REF_SIZE * 1.25) * size if slide["ref"] else 0.0)
    page.set_viewport_size({"width": W, "height": H})
    page.evaluate("h => { document.body.innerHTML = h; }", layer_html(spec, slide, spans, size, spec["top"] + (box_h - h) / 2, colour))
    page.evaluate("document.fonts.ready")
    lines = page.evaluate(LINES_JS)
    png = page.screenshot(type="png", omit_background=True, clip={"x": 0, "y": 0, "width": W, "height": H})
    layer = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA")).astype(F) / 255.0
    glyph = (layer[..., 3] > 0.5).astype(np.uint8)
    ys, xs = np.nonzero(glyph)
    if len(ys) == 0:
        stop("no letters were drawn. Are the font files missing from tools/fonts?")
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
        glyph = (layer[..., 3] > 0.5).astype(np.uint8)
        ys, xs = np.nonzero(glyph)
    ink = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    lines = [(a + dx, b + dy, c + dx, d + dy) for a, b, c, d in lines]
    return dict(layer=layer, glyph=glyph, ink=ink, lines=lines, n_lines=len(spans))


def ink_fits(spec, ink):
    x0, y0, x1, y1 = ink
    return (x0 >= spec["left"] - 3 and spec["W"] - x1 >= spec["right"] - 3
            and y0 >= spec["top"] - 3 and spec["H"] - y1 >= spec["bottom"] - 3)


# --------------------------------------------------------------------------- choosing the pictures

def hints_for(text):
    fams, moods = set(), set()
    low = text.lower()
    for pat, ms in MOOD_HINTS:
        if re.search(pat, low):
            moods.update(ms)
    for pat, fs in FAMILY_HINTS:
        if re.search(pat, low):
            fams.update(fs)
    return fams, moods


def choose_looks(slides, seed, history, forced, fit):
    """One picture type and one colour story for each slide. Different within the set, and
    different from the sets before it. `fit(i, family, mood)` says whether a picture suits slide i."""
    fams, moods = list(garden.FAMILIES), list(garden.MOODS)
    recent_first = [h[0].get("family") for h in history[-5:] if h]
    recent_first_mood = [h[0].get("mood") for h in history[-3:] if h]
    recent_pairs = {(l.get("family"), l.get("mood")) for h in history[-2:] for l in h}
    yesterday = {l.get("family") for l in history[-1]} if history else set()
    old = {tuple((l.get("family"), l.get("mood")) for l in h) for h in history}
    for attempt in range(60):
        rng = np.random.default_rng([int(seed), 91, attempt])
        used_f, used_m, out, dark_used, ok = set(), set(), [], False, True
        for i, s in enumerate(slides):
            if forced and i < len(forced) and forced[i]:
                f, mo = forced[i].get("family"), forced[i].get("mood")
                if f not in garden.FAMILIES or mo not in garden.MOODS:
                    stop(f'slide {i + 1}: "{f}" / "{mo}" is not a picture this tool knows. Run with --list to see the names.')
            else:
                hf, hm = hints_for(s["text"])
                best = None
                for f in fams:
                    if f in used_f and len(used_f) < len(fams):
                        continue
                    if i == 0 and f in recent_first and len(set(recent_first)) < len(fams) - 2:
                        continue
                    for mo in moods:
                        if mo in used_m and len(used_m) < len(moods):
                            continue
                        dark = garden.is_dark(mo)
                        if dark and dark_used:
                            continue
                        if not fit(i, f, mo):
                            continue
                        sc = rng.random() + (0.4 if f in hf else 0.0) + (0.35 if mo in hm else 0.0) \
                            - (0.5 if f in yesterday else 0.0) - (0.6 if (f, mo) in recent_pairs else 0.0) \
                            - (0.30 if dark else 0.0) - (0.5 if i == 0 and mo in recent_first_mood else 0.0)
                        if best is None or sc > best[0]:
                            best = (sc, f, mo)
                if best is None:
                    ok = False
                    break
                f, mo = best[1], best[2]
            used_f.add(f)
            used_m.add(mo)
            dark_used = dark_used or garden.is_dark(mo)
            out.append({"family": f, "mood": mo})
        if ok and tuple((l["family"], l["mood"]) for l in out) not in old:
            return out
    stop("could not find a set of pictures that differs from every earlier set.")


# --------------------------------------------------------------------------- light and contrast

def to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lum(lin):
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def colour_lum(hex_colour):
    c = np.array([int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)], np.float64) / 255.0
    return float(lum(to_lin(c)))


def contrast_of(final, glyph, text_lum):
    """Contrast between the letters and the picture right around them: (typical, worst)."""
    ring = cv2.dilate(glyph, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) \
        & (1 - cv2.dilate(glyph, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))))
    L = cv2.GaussianBlur(lum(to_lin(final.astype(np.float64))).astype(F), (0, 0), 1.5)
    p5, p50, p95 = np.percentile(L[ring > 0], [5, 50, 95])

    def ratio(a, b):
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    worst_bg = p5 if text_lum < p50 else p95       # dark words fear dark spots, light words fear light spots
    return ratio(text_lum, p50), ratio(text_lum, worst_bg)


def shoot_art(page, svg, W, H):
    page.set_viewport_size({"width": W, "height": H})
    page.evaluate("h => { document.body.innerHTML = h; }", svg)
    png = page.screenshot(type="png", clip={"x": 0, "y": 0, "width": W, "height": H})
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(F) / 255.0


def make_one(page, spec, words, look, seed, variant=None):
    """Paint one picture round the words and check it. Returns (image 0..255 uint8, facts)."""
    W, H = spec["W"], spec["H"]
    x0, y0, x1, y1 = words["ink"]
    margins = dict(left=x0, right=W - x1, top=y0, bottom=H - y1)
    for side in ("left", "right", "top", "bottom"):
        if margins[side] < spec[side] - 3:
            stop(f"words reach {margins[side]} px from the {side} edge on the {spec['name']} picture; "
                 f"the rule is {spec[side]} px. Shorten that slide.")
    text_lum = colour_lum(garden.ink_colour(look["mood"]))
    a = words["layer"][..., 3:4]
    last = None
    for j in ([variant] if variant is not None else range(TRIES)):
        art = shoot_art(page, garden.paint_svg(look["family"], look["mood"], seed + 1000 * j, W, H, words["ink"], words["lines"]), W, H)
        final = art * (1 - a) + words["layer"][..., :3] * a
        typ, worst = contrast_of(final, words["glyph"], text_lum)
        last = (final, typ, worst, j)
        if typ >= MIN_TYPICAL and worst >= MIN_WORST:
            break
    else:
        stop(f"could not reach the contrast floor on a {look['family']} / {look['mood']} picture "
             f"(typical {last[1]:.1f}, worst {last[2]:.1f}). Pick another picture for that slide with \"looks\".")
    final, typ, worst, j = last
    # a whisper of grain, so the soft washes of colour do not show bands
    grain = np.random.default_rng(seed).normal(0.0, 0.006, final.shape[:2]).astype(F)[..., None]
    img = (np.clip(final + grain, 0, 1) * 255 + 0.5).astype(np.uint8)
    return img, dict(lines=words["n_lines"], margins=margins, typical=typ, worst=worst, variant=j)


# --------------------------------------------------------------------------- main

def load_history():
    if LOOKS_FILE.exists():
        return json.loads(LOOKS_FILE.read_text())
    return {"sets": []}


def print_list():
    print("Picture types (family):")
    for k in garden.FAMILIES:
        print(f"  {k:10s} {garden.NOTES.get(k, '')}")
    print("Colour stories (mood):")
    print("  " + ", ".join(k + (" (dark)" if garden.is_dark(k) else "") for k in garden.MOODS))
    print('Example: "looks": [null, {"family": "trellis", "mood": "blush"}]')


def main(argv):
    if "--list" in argv:
        print_list()
        return
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        stop("usage: python3 tools/make_slides.py slides.json out_dir [--no-record]   (or --list)")
    record = "--no-record" not in argv
    spec_in = json.loads(Path(args[0]).read_text())
    out = Path(args[1]).resolve()
    seed = int(spec_in.get("seed", 0))
    texts = [t for t in spec_in["slides"] if t.strip()]
    style = "normal" if spec_in.get("style") == "upright" else "italic"
    hook = bool(spec_in.get("hook"))
    if not seed:
        stop('slides.json needs "seed": the post date as a number, like 20261123.')
    if not 3 <= len(texts) <= 10:
        stop(f"{len(texts)} slides. Use 5 to 7 (never fewer than 3 or more than 10).")
    for name in (FONT_ITALIC, FONT_UPRIGHT):
        if not (FONT_DIR / name).exists():
            stop(f"the font file tools/fonts/{name} is missing.")
    slides = []
    for i, t in enumerate(texts, 1):
        main_text, ref = split_slide(t)
        if len(main_text) > MAX_CHARS:
            stop(f"slide {i} has {len(main_text)} characters. The limit is {MAX_CHARS}. Shorten it.")
        ws = main_text.split()
        slides.append(dict(text=main_text, ref=ref, words=ws, marks=[mark_word(w) for w in ws]))
    if hook:
        h0 = slides[0]
        if h0["ref"]:
            stop("slide 1 is the headline. It cannot carry a verse reference.")
        if len(h0["words"]) > HOOK_MAX_WORDS or len(h0["text"]) > HOOK_MAX_CHARS:
            stop(f"the headline on slide 1 has {len(h0['words'])} words and {len(h0['text'])} characters. "
                 f"Keep it to {HOOK_MAX_WORDS} words and {HOOK_MAX_CHARS} characters.")

    hist = load_history()
    earlier = [s["looks"] for s in hist["sets"] if int(s["seed"]) != seed]

    for d in ("feed", "story", "work"):
        (out / d).mkdir(parents=True, exist_ok=True)
    base = out / "work" / "base.html"
    base.write_text(BASE_HTML.format(fonts=FONT_DIR.as_uri(), ital=FONT_ITALIC, upr=FONT_UPRIGHT, style=style, lh=LINE_H))
    report = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto(base.as_uri())
        flat = [m for s in slides for m in s["marks"]]
        m = page.evaluate(MEASURE_JS, [flat, [mark_ref(s["ref"]) if s["ref"] else "" for s in slides]])
        k = 0
        for s, rw in zip(slides, m["refs"]):
            s["widths"], s["space"], s["refw"] = m["words"][k:k + len(s["words"])], m["space"], rw
            k += len(s["words"])

        # one size for the whole set: the biggest at which every slide still fits its box, measured on the real ink
        box_w = FEED["W"] - FEED["left"] - FEED["right"]
        box_h = FEED["H"] - FEED["top"] - FEED["bottom"]
        size = None
        body = slides[1:] if hook else slides
        # first try to leave ROOM for the picture; give that room up before the words get small
        plans = [(c, box_h - ROOM) for c in range(FONT_MAX, ROOM_MIN_FONT - 1, -1)] + [(c, box_h) for c in range(FONT_MAX, FONT_MIN - 1, -1)]
        for cand, max_h in plans:
            lay = [layout(s, cand, box_w - SLACK) for s in body]
            if not all(sp is not None and h <= max_h for sp, h in lay):
                continue
            shots = [shoot_words(page, FEED, s, sp, cand, "#000000") for s, (sp, _) in zip(body, lay)]
            if not all(ink_fits(FEED, w["ink"]) for w in shots):
                continue
            if not hook:
                st = shoot_words(page, STORY, slides[0], lay[0][0], cand, "#000000")
                if not ink_fits(STORY, st["ink"]):
                    continue
            size, spans = cand, [sp for sp, _ in lay]
            break
        if size is None:
            worst_i = max(range(len(body)), key=lambda i: len(body[i]["text"])) + (1 if hook else 0)
            stop(f"slide {worst_i + 1} is too long to fit at the smallest text size ({FONT_MIN}). Shorten it.")
        sizes = [size] * len(slides)
        if hook:
            # the headline: as big as it can be, clearly bigger than the other slides, with air around it
            hook_size = None
            for cand in range(HOOK_MAX, size + HOOK_STEP_UP - 1, -1):
                sp0, h = layout(slides[0], cand, box_w - SLACK)
                if sp0 is None or h > box_h - HOOK_ROOM:
                    continue
                w0 = shoot_words(page, FEED, slides[0], sp0, cand, "#000000")
                if not ink_fits(FEED, w0["ink"]):
                    continue
                st = shoot_words(page, STORY, slides[0], sp0, cand, "#000000")
                if not ink_fits(STORY, st["ink"]):
                    continue
                hook_size = cand
                break
            if hook_size is None:
                stop("the headline on slide 1 is too long to be set bigger than the other slides. Shorten it.")
            sizes[0], spans, shots = hook_size, [sp0] + spans, [w0] + shots

        def fit(i, fam, mood):
            w = shots[i]
            if not garden.fits(fam, mood, FEED["W"], FEED["H"], w["ink"], w["lines"]):
                return False
            return i != 0 or garden.fits(fam, mood, STORY["W"], STORY["H"], st["ink"], st["lines"])

        looks = choose_looks(slides, seed, earlier, spec_in.get("looks"), fit)

        feed, first_variant = [], 0
        for i, (s, sp, look) in enumerate(zip(slides, spans, looks), 1):
            words = shoot_words(page, FEED, s, sp, sizes[i - 1], garden.ink_colour(look["mood"]))
            img, facts = make_one(page, FEED, words, look, seed * 100 + i)
            if i == 1:
                first_variant = facts["variant"]
            Image.fromarray(img).save(out / "feed" / f"slide-{i:02d}.jpg", quality=92, subsampling=0, optimize=True)
            feed.append(img)
            mg = facts["margins"]
            report.append(f"slide {i}: {look['family']:9s} {look['mood']:10s} {len(s['text']):3d} chars, {facts['lines']} lines, "
                          f"margins L{mg['left']} R{mg['right']} T{mg['top']} B{mg['bottom']}, "
                          f"contrast typical {facts['typical']:.1f} worst {facts['worst']:.1f}")
        words = shoot_words(page, STORY, slides[0], spans[0], sizes[0], garden.ink_colour(looks[0]["mood"]))
        story, facts = make_one(page, STORY, words, looks[0], seed * 100 + 1, variant=first_variant)
        Image.fromarray(story).save(out / "story" / "story-single.jpg", quality=92, subsampling=0, optimize=True)
        mg = facts["margins"]
        report.append(f"story  : {looks[0]['family']:9s} {looks[0]['mood']:10s} margins L{mg['left']} R{mg['right']} "
                      f"T{mg['top']} B{mg['bottom']}, contrast typical {facts['typical']:.1f} worst {facts['worst']:.1f}")
        browser.close()

    # contact sheet
    th, gap = 540, 12
    tw, sw = int(th * 1080 / 1350), int(th * 1080 / 1920)
    cols = min(len(feed) + 1, 4)
    rows = (len(feed) + 1 + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (70, 66, 64))
    for i, img in enumerate(feed):
        sheet.paste(Image.fromarray(img).resize((tw, th), Image.LANCZOS),
                    (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    i = len(feed)
    sheet.paste(Image.fromarray(story).resize((sw, th), Image.LANCZOS),
                (gap + (i % cols) * (tw + gap) + (tw - sw) // 2, gap + (i // cols) * (th + gap)))
    sheet.save(out / "sheet.jpg", quality=90)

    fams = [l["family"] for l in looks]
    mds = [l["mood"] for l in looks]
    head = [(f"headline on slide 1: {sizes[0]} px (limit {HOOK_MAX}); every other slide: {size} px (limits {FONT_MIN} to {FONT_MAX})"
             if hook else f"text size on every slide: {size} px (limits {FONT_MIN} to {FONT_MAX})"),
            f"letters: EB Garamond semi-bold, {'upright' if style == 'normal' else 'swash italic'}",
            f"picture types: {', '.join(fams)}",
            f"colour stories: {', '.join(mds)}",
            f"no picture type repeated: {'yes' if len(set(fams)) == len(fams) else 'NO'}",
            f"no colour story repeated: {'yes' if len(set(mds)) == len(mds) else 'NO'}",
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
