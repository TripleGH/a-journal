#!/usr/bin/env python3
"""
The painter for the Come to the Fire slides: the garden look (November 20, 2026).

Everything here is drawn by code as vector shapes (SVG) and rendered by Chromium. There are no
photos and no AI images, so a person can never appear. The style: soft painted florals, leaves,
garlands, lattice and stripe grounds, thin gold lines. Nothing here imitates paper.

The words never sit on a flower: every picture is built around a "quiet zone" (the box that holds
the words), and all art is kept out of it.
"""
import math
import random

# --------------------------------------------------------------------------- small helpers

def _f(v):
    return f"{v:.1f}"


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, t):
    a, b = hex2rgb(a), hex2rgb(b)
    return rgb2hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


class Ramp:
    """Three tones of one colour plus a line colour."""

    def __init__(self, name, light, mid, deep, line=None):
        self.name, self.light, self.mid, self.deep = name, light, mid, deep
        self.line = line or mix(deep, "#2a1a1a", 0.35)


# flower colours
R = {
    "blush":   Ramp("blush", "#fde9e6", "#f7c9c9", "#e79aa6"),
    "rose":    Ramp("rose", "#fbd3d8", "#f09fb0", "#d2607f"),
    "deeprose": Ramp("deeprose", "#f6b6c6", "#dd6f93", "#a93862"),
    "peach":   Ramp("peach", "#fee6d2", "#fbc5a2", "#ee9670"),
    "coral":   Ramp("coral", "#fdd2c4", "#f79f8b", "#e06a5c"),
    "cream":   Ramp("cream", "#fffaf0", "#fbefd8", "#ecd5ab", "#b89a66"),
    "white":   Ramp("white", "#ffffff", "#f6f3ee", "#dfd9d2", "#a79f9a"),
    "butter":  Ramp("butter", "#fff5cf", "#fde49a", "#f2c45c", "#b98a2c"),
    "lilac":   Ramp("lilac", "#efe4f7", "#d6bfe9", "#a988cf"),
    "violet":  Ramp("violet", "#dccdf0", "#b295da", "#7c5bb5"),
    "mauve":   Ramp("mauve", "#f1dbe8", "#dcabc9", "#b56f9c"),
    "sky":     Ramp("sky", "#e3f0f8", "#b9d7ec", "#7fb0d6"),
    "peri":    Ramp("peri", "#dfe4f8", "#b3bfec", "#7c8fd2"),
    "delft":   Ramp("delft", "#d5e0f3", "#8fa9d9", "#35549f", "#1f3470"),
    "cobalt":  Ramp("cobalt", "#b8c9ea", "#5f80c4", "#22408f", "#172c66"),
    "berry":   Ramp("berry", "#f4c1c9", "#d9667f", "#9c2f4f"),
    "gold":    Ramp("gold", "#f7e7b4", "#e3c477", "#b8924a", "#8a6a2c"),
}
# leaf colours
G = {
    "sage":    Ramp("sage", "#dfe8d3", "#b4c7a0", "#7f9a6e", "#566b4b"),
    "olive":   Ramp("olive", "#dfe3bd", "#b3bb7c", "#7f8a4c", "#565e30"),
    "fresh":   Ramp("fresh", "#dcefc9", "#a9d18c", "#6ea85f", "#447a41"),
    "eucal":   Ramp("eucal", "#dcebe6", "#a9c9c1", "#6f9d97", "#4a726e"),
    "forest":  Ramp("forest", "#c9dcc6", "#8bb08a", "#4f7f59", "#2f5a3d"),
    "bluegr":  Ramp("bluegr", "#d5e6e8", "#9fc0c6", "#64929d", "#41697a"),
    "delftleaf": Ramp("delftleaf", "#d9e3f4", "#9fb4dd", "#4c69ad", "#2a427f"),
    "dusk":    Ramp("dusk", "#b9c9b4", "#8aa588", "#5d7d63", "#3c5a47"),
}


def defs_for(ramps):
    """Gradients for every ramp: along a petal (base to tip, both ways) and across a leaf."""
    out = []
    for r in ramps:
        n = r.name
        out.append(f'<linearGradient id="pa_{n}" x1=".5" y1="1" x2=".5" y2="0">'
                   f'<stop offset="0" stop-color="{r.deep}"/><stop offset=".45" stop-color="{r.mid}"/>'
                   f'<stop offset="1" stop-color="{r.light}"/></linearGradient>')
        out.append(f'<linearGradient id="pb_{n}" x1=".5" y1="1" x2=".5" y2="0">'
                   f'<stop offset="0" stop-color="{r.mid}"/><stop offset=".6" stop-color="{r.light}"/>'
                   f'<stop offset="1" stop-color="{mix(r.light, r.mid, .5)}"/></linearGradient>')
        out.append(f'<linearGradient id="pc_{n}" x1=".5" y1="1" x2=".5" y2="0">'
                   f'<stop offset="0" stop-color="{mix(r.deep, r.line, .25)}"/><stop offset=".5" stop-color="{r.deep}"/>'
                   f'<stop offset="1" stop-color="{r.mid}"/></linearGradient>')
        out.append(f'<linearGradient id="lf_{n}" x1="0" y1=".5" x2="1" y2=".5">'
                   f'<stop offset="0" stop-color="{r.mid}"/><stop offset=".49" stop-color="{mix(r.mid, r.deep, .35)}"/>'
                   f'<stop offset=".51" stop-color="{mix(r.mid, r.deep, .8)}"/><stop offset="1" stop-color="{r.deep}"/></linearGradient>')
        out.append(f'<linearGradient id="lg_{n}" x1="0" y1=".5" x2="1" y2=".5">'
                   f'<stop offset="0" stop-color="{r.light}"/><stop offset=".49" stop-color="{mix(r.light, r.mid, .6)}"/>'
                   f'<stop offset=".51" stop-color="{r.mid}"/><stop offset="1" stop-color="{mix(r.mid, r.deep, .5)}"/></linearGradient>')
    return "".join(out)


# --------------------------------------------------------------------------- shapes (local units: 100 = one radius)

def petal_d(L, w, tip=0.0, notch=0.0, base=0.10, belly=0.58, skew=0.0):
    """A petal that points up from the origin. tip 0 round .. 1 pointed. notch = depth of a heart cut."""
    b = base * w
    wl, wr = w * (1 - skew), w * (1 + skew)
    ty = -L
    cx_tip = 0.62 * (1 - tip) + 0.04
    if notch > 0:
        nx = w * 0.30
        d = (f"M{_f(b)},0 C{_f(b + wr * .55)},{_f(-L * .04)} {_f(wr)},{_f(-L * (belly - .28))} {_f(wr)},{_f(-L * belly)} "
             f"C{_f(wr)},{_f(-L * (belly + .26))} {_f(nx + wr * .35)},{_f(ty)} {_f(nx)},{_f(ty)} "
             f"C{_f(nx * .55)},{_f(ty)} {_f(nx * .2)},{_f(ty + L * notch * .5)} 0,{_f(ty + L * notch)} "
             f"C{_f(-nx * .2)},{_f(ty + L * notch * .5)} {_f(-nx * .55)},{_f(ty)} {_f(-nx)},{_f(ty)} "
             f"C{_f(-nx - wl * .35)},{_f(ty)} {_f(-wl)},{_f(-L * (belly + .26))} {_f(-wl)},{_f(-L * belly)} "
             f"C{_f(-wl)},{_f(-L * (belly - .28))} {_f(-b - wl * .55)},{_f(-L * .04)} {_f(-b)},0 Z")
    else:
        d = (f"M{_f(b)},0 C{_f(b + wr * .55)},{_f(-L * .04)} {_f(wr)},{_f(-L * (belly - .28))} {_f(wr)},{_f(-L * belly)} "
             f"C{_f(wr)},{_f(-L * (belly + .24))} {_f(wr * cx_tip)},{_f(ty)} 0,{_f(ty)} "
             f"C{_f(-wl * cx_tip)},{_f(ty)} {_f(-wl)},{_f(-L * (belly + .24))} {_f(-wl)},{_f(-L * belly)} "
             f"C{_f(-wl)},{_f(-L * (belly - .28))} {_f(-b - wl * .55)},{_f(-L * .04)} {_f(-b)},0 Z")
    return d


def leaf_d(L, w, bend=0.0, belly=0.42):
    """A leaf that points up from the origin, pointed at both ends, with a little bend."""
    bx = bend * L
    return (f"M0,0 C{_f(w * 1.05 + bx * .2)},{_f(-L * (belly - .22))} {_f(w * .95 + bx * .6)},{_f(-L * (belly + .3))} {_f(bx)},{_f(-L)} "
            f"C{_f(-w * .75 + bx * .6)},{_f(-L * (belly + .3))} {_f(-w * 1.05 + bx * .2)},{_f(-L * (belly - .22))} 0,0 Z")


def rib_d(L, bend=0.0):
    bx = bend * L
    return f"M0,0 Q{_f(bx * .25)},{_f(-L * .55)} {_f(bx * .92)},{_f(-L * .93)}"


def tf(x, y, rot=0.0, s=1.0, sy=None):
    sc = f" scale({s:.4f})" if sy is None else f" scale({s:.4f},{sy:.4f})"
    return f'transform="translate({_f(x)},{_f(y)}) rotate({_f(rot)}){sc}"'


def brush_d(pts, widths):
    """A stroke whose width changes along its length (a pen flourish). pts: [(x,y)], widths: one per point."""
    n = len(pts)
    left, right = [], []
    for i in range(n):
        x0, y0 = pts[max(i - 1, 0)]
        x1, y1 = pts[min(i + 1, n - 1)]
        dx, dy = x1 - x0, y1 - y0
        m = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / m, dx / m
        h = widths[i] / 2.0
        left.append((pts[i][0] + nx * h, pts[i][1] + ny * h))
        right.append((pts[i][0] - nx * h, pts[i][1] - ny * h))
    poly = left + right[::-1]
    return "M" + " L".join(f"{_f(x)},{_f(y)}" for x, y in poly) + " Z"


# --------------------------------------------------------------------------- flowers
# Each returns SVG for one flower drawn around (0,0) with radius about 100, to be wrapped in a <g transform>.

MUL = 'style="mix-blend-mode:multiply"'


def _ring(rng, n, L, w, ramp, kind="pa", op=0.9, tip=0.0, notch=0.0, rot0=0.0, jit=10.0, base=0.12, belly=0.58, line=0.30, lw=1.3, mul=False, fill=None):
    out = []
    order = list(range(n))
    rng.shuffle(order)
    for k in order:
        a = rot0 + 360.0 * k / n + rng.uniform(-jit, jit)
        l = L * rng.uniform(0.92, 1.08)
        ww = w * rng.uniform(0.9, 1.1)
        d = petal_d(l, ww, tip=tip, notch=notch, base=base, belly=belly * rng.uniform(0.94, 1.06), skew=rng.uniform(-0.08, 0.08))
        st = f' stroke="{ramp.line}" stroke-opacity="{line:.2f}" stroke-width="{lw}" vector-effect="non-scaling-stroke"' if line > 0 else ""
        fl = fill or f"url(#{kind}_{ramp.name})"
        out.append(f'<path d="{d}" fill="{fl}" fill-opacity="{op:.2f}"{st} transform="rotate({_f(a)})" {MUL if mul else ""}/>')
    return "".join(out)


def crescent_d(r, span, k, a0):
    """A curved petal edge seen from above: the sliver between two arcs."""
    a1 = a0 + span
    x0, y0 = r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0))
    x1, y1 = r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1))
    big = 1 if span > 180 else 0
    return (f"M{_f(x0)},{_f(y0)} A{_f(r)},{_f(r)} 0 {big} 1 {_f(x1)},{_f(y1)} A{_f(r * k)},{_f(r * k)} 0 0 0 {_f(x0)},{_f(y0)} Z",
            f"M{_f(x1)},{_f(y1)} A{_f(r * k)},{_f(r * k)} 0 0 0 {_f(x0)},{_f(y0)}")


def _crescents(rng, n, r, span, k, fill, ramp, rot0=0.0, op=0.95, edge=0.40):
    out = []
    order = list(range(n))
    rng.shuffle(order)
    for i in order:
        a0 = rot0 + 360.0 * i / n + rng.uniform(-14, 14)
        body, inner = crescent_d(r * rng.uniform(0.93, 1.07), span * rng.uniform(0.9, 1.1), k * rng.uniform(0.95, 1.08), a0)
        out.append(f'<path d="{body}" fill="{fill}" fill-opacity="{op:.2f}" stroke="{ramp.line}" stroke-opacity=".20" stroke-width="1" vector-effect="non-scaling-stroke"/>'
                   f'<path d="{inner}" fill="none" stroke="{ramp.deep}" stroke-opacity="{edge:.2f}" stroke-width="2.2" stroke-linecap="round" vector-effect="non-scaling-stroke"/>')
    return "".join(out)


def _swirl(rng, ramp, r=26.0, turns=3):
    out = []
    for k in range(turns + 2):
        a0 = rng.uniform(0, 360)
        span = rng.uniform(110, 210)
        rr = r * (0.25 + 0.75 * (k + 1) / (turns + 2))
        pts, ws = [], []
        m = 12
        for i in range(m + 1):
            t = i / m
            a = math.radians(a0 + span * t)
            rad = rr * (1 + 0.10 * math.sin(t * math.pi))
            pts.append((math.cos(a) * rad, math.sin(a) * rad * 0.92))
            ws.append((2.0 + 4.5 * math.sin(t * math.pi)) * (0.7 + 0.5 * rng.random()))
        out.append(f'<path d="{brush_d(pts, ws)}" fill="{ramp.line}" fill-opacity="{rng.uniform(.30, .55):.2f}"/>')
    return "".join(out)


def rose(rng, ramp, open_=0.5):
    """A garden rose seen from above: soft outer petals, then curled petals turning in to the heart."""
    s = []
    s.append(_ring(rng, rng.choice([5, 6]), 100, 62, ramp, "pb", op=0.90, jit=12, belly=0.60, line=0.22, mul=True))
    s.append(_ring(rng, 5, 84, 54, ramp, "pb", op=0.85, rot0=rng.uniform(20, 50), jit=12, belly=0.6, line=0.24))
    s.append(_crescents(rng, 5, 66, 128, 1.55, mix(ramp.light, ramp.mid, 0.45), ramp, rot0=rng.uniform(0, 72), edge=0.30))
    s.append(_crescents(rng, 5, 50, 138, 1.50, mix(ramp.light, ramp.mid, 0.75), ramp, rot0=rng.uniform(0, 72), edge=0.36))
    s.append(_crescents(rng, 4, 35, 150, 1.45, mix(ramp.mid, ramp.deep, 0.15), ramp, rot0=rng.uniform(0, 90), edge=0.50))
    s.append(_crescents(rng, 3, 22, 165, 1.40, mix(ramp.mid, ramp.deep, 0.65), ramp, rot0=rng.uniform(0, 120), edge=0.62))
    s.append(f'<circle r="11" fill="{mix(ramp.deep, ramp.line, 0.25)}" fill-opacity=".95"/>')
    s.append(_crescents(rng, 2, 9, 170, 1.5, mix(ramp.mid, ramp.deep, 0.5), ramp, rot0=rng.uniform(0, 180), edge=0.7))
    return "".join(s)


def peony(rng, ramp, center=None):
    """A full, ruffled bloom with many petals."""
    s = []
    s.append(_ring(rng, 8, 100, 46, ramp, "pb", op=0.86, jit=10, notch=0.10, belly=0.66, line=0.20, mul=True))
    s.append(_ring(rng, 8, 86, 43, ramp, "pb", op=0.88, rot0=22, jit=12, notch=0.12, belly=0.66, line=0.24))
    s.append(_ring(rng, 7, 69, 38, ramp, "pb", op=0.92, rot0=rng.uniform(0, 50), jit=14, notch=0.14, belly=0.64, line=0.28,
                   fill=mix(ramp.light, ramp.mid, 0.55)))
    s.append(_ring(rng, 6, 52, 31, ramp, "pb", op=0.94, rot0=rng.uniform(0, 60), jit=16, notch=0.12, belly=0.62, line=0.32,
                   fill=mix(ramp.light, ramp.mid, 0.85)))
    s.append(_ring(rng, 5, 35, 23, ramp, "pa", op=0.95, rot0=rng.uniform(0, 70), jit=18, belly=0.6, line=0.34,
                   fill=mix(ramp.mid, ramp.deep, 0.35)))
    if center is not None:
        s.append(f'<circle r="13" fill="{mix(ramp.mid, ramp.deep, 0.6)}" fill-opacity=".9"/>')
        for _ in range(18):
            a, rr = rng.uniform(0, 6.283), rng.uniform(1, 12)
            s.append(f'<circle cx="{_f(math.cos(a) * rr)}" cy="{_f(math.sin(a) * rr)}" r="{rng.uniform(1.8, 3.0):.1f}" fill="{center.mid}"/>')
    else:
        s.append(_crescents(rng, 3, 15, 160, 1.45, mix(ramp.mid, ramp.deep, 0.6), ramp, rot0=rng.uniform(0, 120), edge=0.5))
        s.append(f'<circle r="6" fill="{ramp.deep}"/>')
    return "".join(s)


def ranunculus(rng, ramp, leaf=None):
    """Tight rings of thin petals, like a rosette."""
    s = []
    s.append(_ring(rng, 9, 100, 58, ramp, "pb", op=0.90, jit=7, belly=0.72, base=0.3, line=0.24, mul=True))
    rings = [(86, 9, 52, 0.25), (72, 8, 45, 0.45), (59, 8, 37, 0.62), (46, 7, 30, 0.80), (34, 6, 23, 1.0), (22, 5, 15, 1.2)]
    for i, (L, n, w, t) in enumerate(rings):
        col = mix(ramp.light, ramp.mid, t) if t <= 1 else mix(ramp.mid, ramp.deep, (t - 1) * 2.2)
        s.append(_ring(rng, n, L, w, ramp, "pb", op=0.96, rot0=i * 17 + rng.uniform(0, 10), jit=7, belly=0.72, base=0.3, line=0.34, lw=1.1, fill=col))
    c = leaf.mid if leaf is not None else ramp.deep
    s.append(f'<circle r="8.5" fill="{c}"/><circle r="4" fill="{mix(c, "#ffffff", 0.35)}"/>')
    return "".join(s)


def anemone(rng, ramp, dark="#2c2740"):
    """Wide open petals round a dark eye."""
    s = []
    s.append(_ring(rng, rng.choice([6, 7, 8]), 100, 50, ramp, "pb", op=0.92, jit=8, belly=0.62, line=0.28, mul=True))
    s.append(_ring(rng, 5, 78, 44, ramp, "pb", op=0.90, rot0=rng.uniform(15, 40), jit=10, belly=0.62, line=0.24))
    s.append(f'<circle r="27" fill="{ramp.deep}" fill-opacity=".35" {MUL}/>')
    for k in range(26):
        a = 6.283 * k / 26 + rng.uniform(-.08, .08)
        rr = rng.uniform(19, 25)
        s.append(f'<circle cx="{_f(math.cos(a) * rr)}" cy="{_f(math.sin(a) * rr)}" r="{rng.uniform(2.2, 3.4):.1f}" fill="{dark}" fill-opacity=".85"/>')
    s.append(f'<circle r="15" fill="{dark}"/><circle cx="-4" cy="-5" r="5" fill="#ffffff" fill-opacity=".22"/>')
    return "".join(s)


def blossom(rng, ramp, center=None):
    """A five-petal blossom (wild rose, cherry, dogwood) with a heart cut in each petal."""
    s = []
    s.append(_ring(rng, 5, 100, 58, ramp, "pb", op=0.92, jit=6, notch=0.16, belly=0.62, line=0.30, mul=True))
    c = center or R["butter"]
    s.append(f'<circle r="15" fill="{c.mid}" fill-opacity=".9"/>')
    for k in range(14):
        a = 6.283 * k / 14 + rng.uniform(-.15, .15)
        r1 = rng.uniform(20, 34)
        s.append(f'<line x1="{_f(math.cos(a) * 9)}" y1="{_f(math.sin(a) * 9)}" x2="{_f(math.cos(a) * r1)}" y2="{_f(math.sin(a) * r1)}" stroke="{c.line}" stroke-width="1.4" stroke-opacity=".7"/>'
                 f'<circle cx="{_f(math.cos(a) * r1)}" cy="{_f(math.sin(a) * r1)}" r="2.8" fill="{c.deep}"/>')
    return "".join(s)


def daisy(rng, ramp, center=None):
    """Slender petals round a yellow eye (cosmos, daisy)."""
    s = []
    n = rng.choice([9, 10, 11, 12])
    s.append(_ring(rng, n, 100, 26, ramp, "pb", op=0.94, jit=5, notch=0.07, belly=0.66, base=0.3, line=0.30, mul=True))
    c = center or R["butter"]
    s.append(f'<circle r="20" fill="{c.mid}"/><circle r="20" fill="{c.deep}" fill-opacity=".35"/>')
    for _ in range(22):
        a, rr = rng.uniform(0, 6.283), rng.uniform(3, 17)
        s.append(f'<circle cx="{_f(math.cos(a) * rr)}" cy="{_f(math.sin(a) * rr)}" r="2" fill="{c.line}" fill-opacity=".55"/>')
    return "".join(s)


def floret(rng, ramp, eye):
    s = ['<circle r="52" fill="#fffdf9"/>', _ring(rng, 4, 100, 62, ramp, "pb", op=0.90, rot0=rng.uniform(0, 90), jit=8, tip=0.35, belly=0.6, base=0.2, line=0.32, mul=True)]
    s.append(f'<circle r="11" fill="{eye}" fill-opacity=".85"/>')
    return "".join(s)


def hydrangea(rng, ramps, eye="#f5ecd0"):
    """A dome of small four-petal florets."""
    pts = []
    tries = 0
    while len(pts) < 34 and tries < 900:
        tries += 1
        a, rr = rng.uniform(0, 6.283), 84 * math.sqrt(rng.random())
        x, y = math.cos(a) * rr, math.sin(a) * rr * 0.92
        if all((x - px) ** 2 + (y - py) ** 2 > 21 ** 2 for px, py, _ in pts):
            pts.append((x, y, rng.uniform(17, 23)))
    pts.sort(key=lambda p: -(p[0] ** 2 + p[1] ** 2))
    s = []
    for x, y, r in pts:
        shade = (x + y) / 170.0
        ramp = ramps[min(len(ramps) - 1, max(0, int((shade + 0.5 + rng.uniform(-.3, .3)) * len(ramps))))]
        s.append(f'<g {tf(x, y, rng.uniform(0, 90), r / 100.0)}>{floret(rng, ramp, eye)}</g>')
    return "".join(s)


def bud(rng, ramp, leaf):
    """A closed bud on its green cup."""
    s = [f'<path d="{petal_d(100, 34, tip=0.55, belly=0.5)}" fill="url(#pa_{ramp.name})" fill-opacity=".92" stroke="{ramp.line}" stroke-opacity=".3" stroke-width="1.2" vector-effect="non-scaling-stroke"/>',
         f'<path d="{petal_d(78, 20, tip=0.6, belly=0.5)}" fill="url(#pc_{ramp.name})" fill-opacity=".45" transform="rotate(9)"/>']
    for a in (-24, 0, 24):
        s.append(f'<path d="{leaf_d(48, 13)}" fill="{leaf.deep}" fill-opacity=".9" transform="rotate({a})"/>')
    return "".join(s)


def leaf(rng, ramp, L=100, w=30, kind="lf", bend=None, rib=True, op=0.9):
    b = rng.uniform(-0.18, 0.18) if bend is None else bend
    s = f'<path d="{leaf_d(L, w, b)}" fill="url(#{kind}_{ramp.name})" fill-opacity="{op:.2f}" stroke="{ramp.line}" stroke-opacity=".22" stroke-width="1" vector-effect="non-scaling-stroke" {MUL}/>'
    if rib:
        s += f'<path d="{rib_d(L, b)}" fill="none" stroke="{ramp.line}" stroke-opacity=".45" stroke-width="1.2" vector-effect="non-scaling-stroke" stroke-linecap="round"/>'
    return s


# --------------------------------------------------------------------------- sprigs (drawn in page pixels, not in units)

def _curve_pts(x, y, ang, length, curl, n=14):
    """Points along a gently curving stem that starts at (x,y) heading `ang` degrees (0 = right, -90 = up)."""
    pts = []
    a = math.radians(ang)
    px, py = x, y
    step = length / n
    for i in range(n + 1):
        pts.append((px, py, math.degrees(a)))
        a += math.radians(curl) / n
        px += math.cos(a) * step
        py += math.sin(a) * step
    return pts


def _clear_path(x, y, ang, length, curl, n=14):
    """Points along a stem, cut short before it would run into the words.
    Returns (points, length) or (None, 0) when there is no room for it."""
    pts = _curve_pts(x, y, ang, length, curl, n)
    geo = _CTX["geo"]
    if geo is None:
        return pts, length
    full = min(70.0, 0.20 * length)
    for i, (px, py, _) in enumerate(pts):
        m = 6.0 + full * min(1.0, i / (0.35 * n))
        if not geo.clear(px, py, m / 0.94):
            keep = (i - 1) / n
            if keep < 0.38:
                return None, 0.0
            return _curve_pts(x, y, ang, length * keep, curl * keep, n), length * keep
    return pts, length


def _stem(pts, color, w0, w1, op=0.85):
    xy = [(p[0], p[1]) for p in pts]
    n = len(xy)
    ws = [w0 + (w1 - w0) * i / (n - 1) for i in range(n)]
    return f'<path d="{brush_d(xy, ws)}" fill="{color}" fill-opacity="{op}"/>'


def leaf_sprig(rng, x, y, ang, length, ramp, lw=0.30, n=None, kind=None, taper=True, round_=False):
    """A stem with leaves on both sides, smaller toward the tip."""
    curl = rng.uniform(-55, 55)
    pts, length = _clear_path(x, y, ang, length, curl)
    if pts is None:
        return ""
    s = [_stem(pts, ramp.line, max(2.0, length * 0.016), 1.0)]
    n = n or max(5, int(length / 34))
    kind = kind or rng.choice(["lf", "lg"])
    for i in range(n):
        t = 0.16 + 0.80 * i / max(n - 1, 1)
        px, py, pa = pts[min(len(pts) - 1, int(t * (len(pts) - 1)))]
        side = -1 if i % 2 else 1
        size = length * (0.30 if round_ else 0.34) * ((1.0 - 0.55 * t) if taper else 1.0) * rng.uniform(0.85, 1.12)
        a = pa + 90 + side * rng.uniform(46, 68)
        w = (62 if round_ else 100 * lw) * rng.uniform(0.9, 1.1)
        s.append(f'<g {tf(px, py, a, size / 100.0)}>{leaf(rng, ramp, 100, w, kind, rib=not round_)}</g>')
    px, py, pa = pts[-1]
    s.append(f'<g {tf(px, py, pa + 90, length * 0.20 / 100.0)}>{leaf(rng, ramp, 100, 100 * lw, kind)}</g>')
    return "".join(s)


def fern(rng, x, y, ang, length, ramp):
    curl = rng.uniform(-70, 70)
    pts, length = _clear_path(x, y, ang, length, curl, n=22)
    if pts is None:
        return ""
    s = [_stem(pts, ramp.line, max(1.8, length * 0.012), 0.8)]
    for i in range(2, len(pts) - 1):
        t = i / (len(pts) - 1)
        px, py, pa = pts[i]
        size = length * 0.22 * math.sin(min(1.0, t * 1.25) * math.pi) ** 0.8 + 6
        for side in (-1, 1):
            a = pa + 90 + side * 62
            s.append(f'<path d="{leaf_d(100, 15, side * 0.12)}" fill="{ramp.mid if (i + side) % 3 else ramp.deep}" fill-opacity=".85" {tf(px, py, a, size / 100.0)} {MUL}/>')
    return "".join(s)


def spike(rng, x, y, ang, length, ramp, green):
    """A flowering spike (lavender, larkspur): a stem with small buds that thin toward the tip."""
    curl = rng.uniform(-30, 30)
    pts, length = _clear_path(x, y, ang, length, curl, n=20)
    if pts is None:
        return ""
    s = [_stem(pts, green.line, max(1.8, length * 0.012), 0.9)]
    for i in range(6, len(pts)):
        t = (i - 6) / (len(pts) - 6)
        px, py, pa = pts[i]
        size = length * 0.085 * (1.05 - 0.6 * t)
        for side in (-1, 1):
            a = pa + 90 + side * rng.uniform(35, 60)
            col = ramp.deep if rng.random() < 0.45 else ramp.mid
            s.append(f'<path d="{petal_d(100, 42, tip=0.3)}" fill="{col}" fill-opacity=".85" {tf(px, py, a, size / 100.0)} {MUL}/>')
    return "".join(s)


def berries(rng, x, y, ang, length, ramp, green):
    """A thin branching stem with small round berries."""
    curl = rng.uniform(-40, 40)
    pts, length = _clear_path(x, y, ang, length, curl, n=12)
    if pts is None:
        return ""
    s = [_stem(pts, green.line, max(1.6, length * 0.012), 0.8)]
    for i in range(4, len(pts), 2):
        px, py, pa = pts[i]
        side = -1 if (i // 2) % 2 else 1
        a = math.radians(pa + side * rng.uniform(40, 70))
        l = length * rng.uniform(0.10, 0.18)
        ex, ey = px + math.cos(a) * l, py + math.sin(a) * l
        r = length * rng.uniform(0.032, 0.045)
        s.append(f'<line x1="{_f(px)}" y1="{_f(py)}" x2="{_f(ex)}" y2="{_f(ey)}" stroke="{green.line}" stroke-width="1.3" stroke-opacity=".8"/>'
                 f'<circle cx="{_f(ex)}" cy="{_f(ey)}" r="{_f(r)}" fill="{ramp.mid}"/><circle cx="{_f(ex)}" cy="{_f(ey)}" r="{_f(r)}" fill="{ramp.deep}" fill-opacity=".35"/>'
                 f'<circle cx="{_f(ex - r * .3)}" cy="{_f(ey - r * .35)}" r="{_f(r * .28)}" fill="#ffffff" fill-opacity=".55"/>')
    px, py, _ = pts[-1]
    r = length * 0.04
    s.append(f'<circle cx="{_f(px)}" cy="{_f(py)}" r="{_f(r)}" fill="{ramp.mid}"/><circle cx="{_f(px - r * .3)}" cy="{_f(py - r * .35)}" r="{_f(r * .28)}" fill="#ffffff" fill-opacity=".55"/>')
    return "".join(s)


def place(kind, rng, x, y, r, pal, rot=None):
    """One flower of the named kind at (x,y) with radius r, in the colours of palette `pal`."""
    rot = rng.uniform(0, 360) if rot is None else rot
    fl = pal["flowers"]
    ramp = rng.choice(fl)
    if kind == "rose":
        inner = rose(rng, ramp)
    elif kind == "peony":
        inner = peony(rng, ramp, center=R["butter"] if rng.random() < 0.5 else None)
    elif kind == "ranunculus":
        inner = ranunculus(rng, ramp, leaf=pal["leaves"][0])
    elif kind == "anemone":
        inner = anemone(rng, rng.choice(pal.get("pale", fl)), dark=pal.get("eye", "#2c2740"))
    elif kind == "blossom":
        inner = blossom(rng, rng.choice(pal.get("pale", fl)), center=pal.get("center"))
    elif kind == "daisy":
        inner = daisy(rng, rng.choice(pal.get("pale", fl)), center=pal.get("center"))
    elif kind == "hydrangea":
        inner = hydrangea(rng, pal.get("hydrangea", fl))
    elif kind == "bud":
        inner = bud(rng, ramp, pal["leaves"][0])
    else:
        raise ValueError(kind)
    base_r = {"rose": 82, "peony": 80, "ranunculus": 86, "anemone": 74, "blossom": 56, "daisy": 34, "bud": 0, "hydrangea": 0}[kind]
    base = f'<circle r="{base_r}" fill="{pal.get("under", "#fffdf9")}"/>' if base_r else ""
    return f'<g {tf(x, y, rot, r / 100.0)}>{base}<g style="isolation:isolate">{inner}</g></g>'


FILTERS = """
<filter id="wc" x="-6%" y="-6%" width="112%" height="112%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="0.011" numOctaves="2" seed="{s1}" result="n1"/>
  <feDisplacementMap in="SourceGraphic" in2="n1" scale="{d1}" xChannelSelector="R" yChannelSelector="G" result="a"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.07" numOctaves="2" seed="{s2}" result="n2"/>
  <feDisplacementMap in="a" in2="n2" scale="{d2}" xChannelSelector="G" yChannelSelector="B" result="b"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="{s3}" result="n3"/>
  <feColorMatrix in="n3" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -0.55 1.22" result="soft"/>
  <feComposite in="b" in2="soft" operator="in"/>
</filter>
<filter id="wcf" x="-6%" y="-6%" width="112%" height="112%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="0.011" numOctaves="2" seed="{s2}" result="n1"/>
  <feDisplacementMap in="SourceGraphic" in2="n1" scale="{d1}" xChannelSelector="R" yChannelSelector="G" result="a"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.07" numOctaves="2" seed="{s1}" result="n2"/>
  <feDisplacementMap in="a" in2="n2" scale="{d2}" xChannelSelector="G" yChannelSelector="B"/>
</filter>
"""


# --------------------------------------------------------------------------- moods (colour stories)

def _mood(ground, wash, ink, flowers, pale, leaves, spikes, accent, hyd, focal, second, small,
          panel="#fffbf5", lattice="#ffffff", dark=False, eye="#2c2740", center="butter", pattern=None):
    return dict(ground=ground, wash=wash, ink=ink, flowers=[R[k] for k in flowers], pale=[R[k] for k in pale],
                leaves=[G[k] for k in leaves], spikes=[R[k] for k in spikes], accent=R[accent],
                hydrangea=[R[k] for k in hyd], focal=focal, second=second, small=small, panel=panel, lattice=lattice,
                dark=dark, eye=eye, center=R[center], pattern=pattern or mix(ground, ink, 0.10))


MOODS = {
    "blush": _mood("#fbece6", ["#f8d8d4", "#fdf4ec", "#f6dfe3"], "#47222f", ["blush", "rose", "peach"], ["white", "cream", "blush"],
                   ["sage", "olive", "eucal"], ["mauve", "lilac"], "coral", ["blush", "rose", "mauve"],
                   ["rose", "peony"], ["ranunculus", "rose", "anemone"], ["blossom", "daisy"]),
    "sage": _mood("#edf1e4", ["#dfe8d2", "#f6f5e9", "#e3ecdd"], "#27382c", ["cream", "white", "blush", "peach"], ["white", "cream"],
                  ["sage", "forest", "olive"], ["cream", "lilac"], "gold", ["cream", "white", "blush"],
                  ["rose", "ranunculus", "peony"], ["anemone", "ranunculus", "blossom"], ["blossom", "daisy"]),
    "sky": _mood("#e6f0f3", ["#d6e7ee", "#f1f6f4", "#dbe8f1"], "#1e3048", ["white", "cream", "blush", "coral"], ["white", "cream"],
                 ["sage", "bluegr", "eucal"], ["sky", "peri"], "coral", ["sky", "peri", "lilac"],
                 ["hydrangea", "rose", "peony"], ["hydrangea", "anemone", "ranunculus"], ["blossom", "daisy"]),
    "lilac": _mood("#f1eaf5", ["#e6dbef", "#f8f1f6", "#e9e2f3"], "#38234b", ["lilac", "violet", "mauve"], ["white", "lilac", "cream"],
                   ["eucal", "sage", "dusk"], ["violet", "peri"], "berry", ["lilac", "peri", "mauve"],
                   ["peony", "rose", "hydrangea"], ["anemone", "ranunculus", "rose"], ["blossom", "daisy"]),
    "butter": _mood("#fbf3da", ["#f8eac2", "#fdf8ea", "#f6edd0"], "#3f2c1b", ["butter", "cream", "peach"], ["white", "cream"],
                    ["fresh", "sage", "olive"], ["sky", "peri"], "coral", ["cream", "butter", "white"],
                    ["rose", "ranunculus", "peony"], ["daisy", "ranunculus", "anemone"], ["blossom", "daisy"], center="gold"),
    "ivory": _mood("#faf5ec", ["#f5ead9", "#fdfaf3", "#f6e6da"], "#3d2a25", ["peach", "coral", "blush", "cream"], ["cream", "white"],
                   ["sage", "olive", "eucal"], ["mauve", "peach"], "gold", ["peach", "blush", "cream"],
                   ["peony", "rose"], ["ranunculus", "rose", "anemone"], ["blossom", "daisy"]),
    "porcelain": _mood("#f2f5fa", ["#e2e9f5", "#fafbfd", "#e6edf7"], "#1c2b4f", ["delft", "cobalt", "sky"], ["white", "sky"],
                       ["delftleaf", "bluegr"], ["cobalt", "delft"], "delft", ["sky", "delft", "peri"],
                       ["peony", "rose", "hydrangea"], ["anemone", "blossom", "ranunculus"], ["blossom", "daisy"],
                       eye="#1b2a5c", center="sky"),
    "peach": _mood("#fdede2", ["#fadbc8", "#fef6ec", "#f9e2d6"], "#4a2a22", ["coral", "peach", "cream"], ["cream", "white", "peach"],
                   ["eucal", "sage", "bluegr"], ["peach", "mauve"], "coral", ["peach", "coral", "cream"],
                   ["rose", "peony", "ranunculus"], ["anemone", "rose", "daisy"], ["blossom", "daisy"]),
    "mint": _mood("#e8f3ed", ["#d7eadf", "#f3f8f2", "#dcece6"], "#1f3c38", ["rose", "blush", "white"], ["white", "blush"],
                  ["fresh", "forest", "sage"], ["mauve", "lilac"], "berry", ["blush", "rose", "white"],
                  ["peony", "rose"], ["ranunculus", "anemone", "blossom"], ["blossom", "daisy"]),
    "rosewater": _mood("#f9e3e6", ["#f4cfd6", "#fcf0ee", "#f6d9df"], "#4b1f2f", ["deeprose", "rose", "blush", "cream"], ["cream", "white", "blush"],
                       ["sage", "forest", "dusk"], ["mauve", "berry"], "berry", ["rose", "mauve", "blush"],
                       ["rose", "peony"], ["ranunculus", "rose", "anemone"], ["blossom", "daisy"]),
    "midnight": _mood("#1f2b49", ["#243154", "#1c2845", "#263459"], "#fbf3e4", ["blush", "peach", "cream", "rose"], ["white", "cream", "blush"],
                      ["dusk", "sage", "eucal"], ["lilac", "sky"], "gold", ["sky", "peri", "lilac"],
                      ["rose", "peony"], ["ranunculus", "anemone", "rose"], ["blossom", "daisy"], dark=True, eye="#1b2140"),
    "plum": _mood("#3b2342", ["#412747", "#36203d", "#44294b"], "#fbf1e6", ["blush", "mauve", "cream", "lilac"], ["white", "cream", "blush"],
                  ["dusk", "sage", "eucal"], ["lilac", "mauve"], "gold", ["lilac", "mauve", "blush"],
                  ["peony", "rose"], ["ranunculus", "anemone", "rose"], ["blossom", "daisy"], dark=True, eye="#2a1830"),
    "dove": _mood("#f0eeed", ["#e4e1e2", "#f8f6f3", "#e9e4e6"], "#2f2b34", ["blush", "mauve", "white"], ["white", "blush"],
                  ["eucal", "dusk", "sage"], ["mauve", "lilac"], "berry", ["mauve", "blush", "lilac"],
                  ["peony", "rose"], ["anemone", "ranunculus", "rose"], ["blossom", "daisy"]),
}


# --------------------------------------------------------------------------- arrangements

def _relax(items, rounds=12):
    """Nudge flowers apart so big blooms do not sit right on top of each other."""
    for _ in range(rounds):
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                dx, dy = b[1] - a[1], b[2] - a[2]
                d = math.hypot(dx, dy) or 0.01
                need = 0.72 * (a[0] + b[0])
                if d < need:
                    push = (need - d) / 2
                    ux, uy = dx / d, dy / d
                    a[1] -= ux * push; a[2] -= uy * push
                    b[1] += ux * push; b[2] += uy * push
    return items


def bouquet(rng, cx, cy, size, facing, pal, fan=115.0, lush=1.0, focal_n=None):
    """A cluster of blooms with leaves fanning out behind them. Returns (leaves_svg, flowers_svg)."""
    back, front = [], []
    for _ in range(int(rng.randint(6, 8) * lush)):
        a = facing + rng.uniform(-fan, fan)
        L = size * rng.uniform(0.95, 1.6)
        ramp = rng.choice(pal["leaves"])
        ox, oy = cx + rng.uniform(-.12, .12) * size, cy + rng.uniform(-.12, .12) * size
        u = rng.random()
        for da in (0, 24, -24, 48, -48, 75, -75):          # if the words are in the way, lean the stem aside
            if u < 0.55:
                s = leaf_sprig(rng, ox, oy, a + da, L, ramp, lw=rng.choice([0.22, 0.30, 0.36]))
            elif u < 0.78:
                s = leaf_sprig(rng, ox, oy, a + da, L * 0.9, pal["leaves"][-1], round_=True, taper=False)
            else:
                s = fern(rng, ox, oy, a + da, L, ramp)
            if s:
                back.append(s)
                break
    for _ in range(rng.randint(2, 4)):
        a = facing + rng.uniform(-fan * 0.9, fan * 0.9)
        L = size * rng.uniform(1.2, 1.8)
        u = rng.random()
        for da in (0, 24, -24, 48, -48, 75, -75):
            if u < 0.6:
                s = spike(rng, cx, cy, a + da, L, rng.choice(pal["spikes"]), pal["leaves"][0])
            else:
                s = berries(rng, cx, cy, a + da, L, pal["accent"], pal["leaves"][0])
            if s:
                back.append(s)
                break
    items = []
    for _ in range(focal_n or rng.choice([1, 2, 2, 3])):
        d, a = size * rng.uniform(0.0, 0.34), rng.uniform(0, 6.283)
        items.append([size * rng.uniform(0.36, 0.47), cx + math.cos(a) * d, cy + math.sin(a) * d, rng.choice(pal["focal"])])
    for _ in range(rng.randint(3, 5)):
        a, d = math.radians(facing + rng.uniform(-fan, fan)), size * rng.uniform(0.5, 0.95)
        items.append([size * rng.uniform(0.20, 0.29), cx + math.cos(a) * d, cy + math.sin(a) * d, rng.choice(pal["second"])])
    for _ in range(rng.randint(2, 4)):
        a, d = math.radians(facing + rng.uniform(-fan, fan)), size * rng.uniform(0.85, 1.25)
        items.append([size * rng.uniform(0.11, 0.155), cx + math.cos(a) * d, cy + math.sin(a) * d, rng.choice(pal["small"])])
    _relax(items)
    items = _fit(items)
    items.sort(key=lambda t: t[0])
    for r, x, y, kind in items:
        if kind == "hydrangea":
            r *= 1.12
        front.append(place(kind, rng, x, y, r, pal))
    return "".join(back), "".join(front)


def garland(rng, pts, pal, scale, every=None, big_at=None):
    """Leaves and blooms strung along a line. pts = [(x, y, angle)], scale = size of a medium bloom."""
    back, front = [], []
    xy = [(p[0], p[1]) for p in pts]
    back.append(f'<path d="M{" L".join(_f(x) + "," + _f(y) for x, y in xy)}" fill="none" stroke="{pal["leaves"][0].line}" stroke-width="2.4" stroke-opacity=".7" stroke-linecap="round"/>')
    total = sum(math.hypot(xy[i + 1][0] - xy[i][0], xy[i + 1][1] - xy[i][1]) for i in range(len(xy) - 1))
    step_leaf = scale * 0.34
    n_leaf = max(4, int(total / step_leaf))
    for i in range(n_leaf):
        t = (i + rng.random() * 0.5) / n_leaf
        x, y, a = pts[min(len(pts) - 1, int(t * (len(pts) - 1)))]
        side = rng.choice([-1, 1])
        L = scale * rng.uniform(1.0, 1.7)
        ramp = rng.choice(pal["leaves"])
        u = rng.random()
        ang = a + side * rng.uniform(30, 85)
        if u < 0.62:
            back.append(leaf_sprig(rng, x, y, ang, L, ramp, lw=rng.choice([0.24, 0.32])))
        elif u < 0.80:
            back.append(spike(rng, x, y, ang, L * 1.1, rng.choice(pal["spikes"]), pal["leaves"][0]))
        elif u < 0.92:
            back.append(berries(rng, x, y, ang, L, pal["accent"], pal["leaves"][0]))
        else:
            back.append(fern(rng, x, y, ang, L, ramp))
    every = every or scale * 1.02
    n = max(3, int(total / every))
    items = []
    for i in range(n):
        t = (i + 0.5 + rng.uniform(-0.25, 0.25)) / n
        x, y, a = pts[min(len(pts) - 1, int(t * (len(pts) - 1)))]
        w = 1.0
        if big_at is not None:
            w = 0.62 + 0.75 * max(0.0, 1 - min(abs(t - b) for b in big_at) * 3.2)
        r = scale * 0.5 * w * rng.uniform(0.8, 1.15)
        kind = rng.choice(pal["focal"] if w > 1.05 else (pal["second"] if w > 0.8 else pal["small"] + pal["second"]))
        off = rng.uniform(-0.25, 0.25) * scale
        items.append([r, x - math.sin(math.radians(a)) * off, y + math.cos(math.radians(a)) * off, kind])
    _relax(items, 6)
    items = _fit(items)
    items.sort(key=lambda t: t[0])
    for r, x, y, kind in items:
        front.append(place(kind, rng, x, y, r, pal))
    return "".join(back), "".join(front)


def line_pts(x0, y0, x1, y1, sag=0.0, n=40):
    """Points from one end to the other, hanging down by `sag` in the middle (a swag)."""
    out = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t + sag * math.sin(t * math.pi)
        out.append([x, y, 0.0])
    for i in range(len(out)):
        a, b = out[max(i - 1, 0)], out[min(i + 1, n)]
        out[i][2] = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return out


def ellipse_pts(cx, cy, a, b, n=90, start=0.0, sweep=360.0):
    out = []
    for i in range(n + 1):
        t = math.radians(start + sweep * i / n)
        out.append([cx + a * math.cos(t), cy + b * math.sin(t), 0.0])
    for i in range(len(out)):
        p, q = out[max(i - 1, 0)], out[min(i + 1, n)]
        out[i][2] = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
    return out


def splatter(rng, cx, cy, radius, color, n=26):
    s = []
    for _ in range(n):
        a, d = rng.uniform(0, 6.283), radius * (0.35 + 0.75 * rng.random() ** 0.7)
        r = rng.choice([1.6, 2.0, 2.4, 3.0, 3.6, 5.0])
        s.append(f'<circle cx="{_f(cx + math.cos(a) * d)}" cy="{_f(cy + math.sin(a) * d)}" r="{r}" fill="{color}" fill-opacity="{rng.uniform(.55, .95):.2f}"/>')
    return "".join(s)


# --------------------------------------------------------------------------- the page: ground, quiet zone, panels, gold

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


_CTX = {"geo": None}


def _fit(items):
    """Move each bloom clear of the words, or drop it. A flower is never cut off by the quiet zone."""
    geo = _CTX["geo"]
    if geo is None:
        return items
    out = []
    for it in items:
        p = geo.settle(it[1], it[2], it[0])
        if p is not None:
            it[1], it[2] = p
            out.append(it)
    return out


class Geo:
    """Where the words sit on the page, and how much room is left around them."""

    def __init__(self, W, H, ink, lines=None, pad_x=44, pad_y=36):
        self.W, self.H, self.ink = W, H, ink
        x0, y0, x1, y1 = ink
        src_rects = lines or [ink]
        self.rects = [(a - 38, b - 26, c + 38, d + 26) for a, b, c, d in src_rects]
        self.zx0, self.zy0 = max(0.0, x0 - pad_x), max(0.0, y0 - pad_y)
        self.zx1, self.zy1 = min(float(W), x1 + pad_x), min(float(H), y1 + pad_y)
        self.top, self.bot = self.zy0, H - self.zy1
        self.left, self.right = self.zx0, W - self.zx1
        self.cx, self.cy = (self.zx0 + self.zx1) / 2, (self.zy0 + self.zy1) / 2

    def clear(self, x, y, r, extra=0.0):
        for a, b, c, d in self.rects:
            nx, ny = min(max(x, a), c), min(max(y, b), d)
            if (x - nx) ** 2 + (y - ny) ** 2 < (r * 0.94 + extra) ** 2:
                return False
        return True

    def settle(self, x, y, r):
        if self.clear(x, y, r, 18):
            return x, y
        dx, dy = x - self.cx, y - self.cy
        m = math.hypot(dx, dy) or 1.0
        ways = ((0.0, 1.0 if dy >= 0 else -1.0), (1.0 if dx >= 0 else -1.0, 0.0), (dx / m, dy / m))
        for step in range(1, 14):
            for ux, uy in ways:
                nx, ny = x + ux * step * r * 0.12, y + uy * step * r * 0.12
                if self.clear(nx, ny, r, 18):
                    return nx, ny
        return None

    def panel(self, grow_x=24, grow_y=22, edge=30):
        """The box for a panel behind the words: the quiet zone grown a little, kept off the page edge."""
        return (max(edge, self.zx0 - grow_x), max(edge, self.zy0 - grow_y),
                min(self.W - edge, self.zx1 + grow_x), min(self.H - edge, self.zy1 + grow_y))


def d_round(b, r=28):
    x0, y0, x1, y1 = b
    return (f"M{_f(x0 + r)},{_f(y0)} H{_f(x1 - r)} A{r},{r} 0 0 1 {_f(x1)},{_f(y0 + r)} V{_f(y1 - r)} A{r},{r} 0 0 1 {_f(x1 - r)},{_f(y1)} "
            f"H{_f(x0 + r)} A{r},{r} 0 0 1 {_f(x0)},{_f(y1 - r)} V{_f(y0 + r)} A{r},{r} 0 0 1 {_f(x0 + r)},{_f(y0)} Z")


def d_notch(b, r=34):
    """A box whose corners are scooped out, like an engraved plate."""
    x0, y0, x1, y1 = b
    return (f"M{_f(x0 + r)},{_f(y0)} H{_f(x1 - r)} A{r},{r} 0 0 0 {_f(x1)},{_f(y0 + r)} V{_f(y1 - r)} A{r},{r} 0 0 0 {_f(x1 - r)},{_f(y1)} "
            f"H{_f(x0 + r)} A{r},{r} 0 0 0 {_f(x0)},{_f(y1 - r)} V{_f(y0 + r)} A{r},{r} 0 0 0 {_f(x0 + r)},{_f(y0)} Z")


def d_scallop(b, s=24):
    """A box with a scalloped edge."""
    x0, y0, x1, y1 = b
    nx = max(4, int(round((x1 - x0) / (2 * s))))
    ny = max(4, int(round((y1 - y0) / (2 * s))))
    sx, sy = (x1 - x0) / (2 * nx), (y1 - y0) / (2 * ny)
    d = [f"M{_f(x0)},{_f(y0)}"]
    for i in range(nx):
        d.append(f"A{_f(sx)},{_f(sx)} 0 0 1 {_f(x0 + 2 * sx * (i + 1))},{_f(y0)}")
    for i in range(ny):
        d.append(f"A{_f(sy)},{_f(sy)} 0 0 1 {_f(x1)},{_f(y0 + 2 * sy * (i + 1))}")
    for i in range(nx):
        d.append(f"A{_f(sx)},{_f(sx)} 0 0 1 {_f(x1 - 2 * sx * (i + 1))},{_f(y1)}")
    for i in range(ny):
        d.append(f"A{_f(sy)},{_f(sy)} 0 0 1 {_f(x0)},{_f(y1 - 2 * sy * (i + 1))}")
    return " ".join(d) + " Z"


def d_arch(b, rise):
    """A box with an arched top, like a garden gate."""
    x0, y0, x1, y1 = b
    rx = (x1 - x0) / 2
    return f"M{_f(x0)},{_f(y1)} V{_f(y0)} A{_f(rx)},{_f(rise)} 0 0 1 {_f(x1)},{_f(y0)} V{_f(y1)} Z"


def panel_svg(d, pal, gold=True, fill=None, op=0.97):
    """A light panel behind the words, edged with two fine gold lines."""
    fill = fill or pal["panel"]
    s = f'<path d="{d}" fill="{fill}" fill-opacity="{op}"/>'
    if gold:
        s += (f'<path d="{d}" fill="none" stroke="url(#gold)" stroke-width="11" stroke-linejoin="round"/>'
              f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="5.5" stroke-linejoin="round"/>')
    return s


def curl_pts(x, y, ang, length, hand=1, turns=1.15, n=60):
    """A pen flourish: it starts straight and winds itself into a curl."""
    pts, ws = [], []
    px, py = x, y
    ds = length / n
    for i in range(n + 1):
        t = i / n
        pts.append((px, py))
        ws.append(0.7 + 5.2 * (math.sin(math.pi * min(1.0, t * 1.15)) ** 0.8) * (1 - 0.55 * t))
        a2 = math.radians(ang) + hand * turns * 2 * math.pi * (t ** 2.4)
        px += math.cos(a2) * ds * (1 - 0.45 * t)
        py += math.sin(a2) * ds * (1 - 0.45 * t)
    return pts, ws


def flourish(x, y, ang, length, hand=1, turns=1.15, scale=1.0, fill="url(#gold)"):
    pts, ws = curl_pts(x, y, ang, length, hand, turns)
    return f'<path d="{brush_d(pts, [w * scale for w in ws])}" fill="{fill}"/>'


def divider(cx, cy, half, fill="url(#gold)"):
    """A small ornament: two curls running out from a diamond."""
    s = [flourish(cx + 12, cy, 0, half, hand=1, fill=fill), flourish(cx - 12, cy, 180, half, hand=-1, fill=fill),
         flourish(cx + 12, cy, 0, half * 0.55, hand=-1, turns=0.9, scale=0.8, fill=fill),
         flourish(cx - 12, cy, 180, half * 0.55, hand=1, turns=0.9, scale=0.8, fill=fill),
         f'<path d="M{_f(cx)},{_f(cy - 9)} L{_f(cx + 9)},{_f(cy)} L{_f(cx)},{_f(cy + 9)} L{_f(cx - 9)},{_f(cy)} Z" fill="{fill}"/>']
    return "".join(s)


def ground_svg(rng, geo, pal):
    W, H = geo.W, geo.H
    s = [f'<rect width="{W}" height="{H}" fill="{pal["ground"]}"/>', '<g filter="url(#soft)">']
    for _ in range(7):
        c = rng.choice(pal["wash"])
        s.append(f'<ellipse cx="{_f(rng.uniform(0, W))}" cy="{_f(rng.uniform(0, H))}" rx="{_f(rng.uniform(.25, .5) * W)}" ry="{_f(rng.uniform(.14, .3) * H)}" fill="{c}" fill-opacity="{rng.uniform(.55, .9):.2f}"/>')
    s.append("</g>")
    return "".join(s)


def lattice_svg(geo, pal, step=96, ang=58, width=7):
    W, H = geo.W, geo.H
    dx = H / math.tan(math.radians(ang))
    out = []
    k = -int(dx // step) - 2
    while k * step < W + step:
        x = k * step
        for sgn in (1, -1):
            xa, xb = (x, x + dx) if sgn == 1 else (x + dx, x)
            out.append(f'<line x1="{_f(xa)}" y1="0" x2="{_f(xb)}" y2="{H}"/>')
        k += 1
    lines = "".join(out)
    return (f'<g stroke="{mix(pal["ground"], pal["ink"], 0.22)}" stroke-opacity=".28" stroke-width="{width}" transform="translate(2.5,3)">{lines}</g>'
            f'<g stroke="{pal["lattice"]}" stroke-opacity=".92" stroke-width="{width}">{lines}</g>')


def stripes_svg(geo, pal, band=60):
    W, H = geo.W, geo.H
    light = mix(pal["ground"], "#ffffff", 0.62)
    pin = mix(pal["ground"], pal["ink"], 0.16)
    out = []
    n = int(math.ceil(W / band))
    off = (W - n * band) / 2
    for i in range(n + 1):
        x = off + i * band
        if i % 2 == 0:
            out.append(f'<rect x="{_f(x)}" y="0" width="{band}" height="{H}" fill="{light}"/>')
        out.append(f'<line x1="{_f(x + 7)}" y1="0" x2="{_f(x + 7)}" y2="{H}" stroke="{pin}" stroke-width="1.6" stroke-opacity=".55"/>')
        out.append(f'<line x1="{_f(x + band - 7)}" y1="0" x2="{_f(x + band - 7)}" y2="{H}" stroke="{pin}" stroke-width="1.6" stroke-opacity=".55"/>')
    return "".join(out)


def dots_svg(geo, pal, step=58, r=7.5):
    W, H = geo.W, geo.H
    col = mix(pal["ground"], "#ffffff", 0.10 if pal["dark"] else 0.62)
    out = []
    j = 0
    y = step / 2
    while y < H + r:
        x = step / 2 + (step / 2 if j % 2 else 0) - step
        while x < W + r:
            out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{r}"/>')
            x += step
        y += step * 0.866
        j += 1
    return f'<g fill="{col}">{"".join(out)}</g>'


def ditsy_svg(rng, geo, pal, cell=150):
    """An all-over scatter of tiny blooms and leaves, like a printed cotton."""
    W, H = geo.W, geo.H
    back, front = [], []
    j = 0
    y = cell * 0.3
    while y < H + cell * 0.5:
        x = cell * 0.3 + (cell * 0.5 if j % 2 else 0) - cell * 0.5
        while x < W + cell * 0.5:
            px, py = x + rng.uniform(-.2, .2) * cell, y + rng.uniform(-.2, .2) * cell
            r = cell * rng.uniform(0.13, 0.19)
            a0 = rng.uniform(0, 360)
            for da in (rng.uniform(-50, -20), rng.uniform(150, 200)):
                back.append(leaf_sprig(rng, px, py, a0 + da, r * rng.uniform(2.2, 3.0), rng.choice(pal["leaves"]), n=3))
            front.append(place(rng.choice(["blossom", "daisy", "blossom", "ranunculus"]), rng, px, py, r, pal))
            for _ in range(2):
                qx, qy = px + rng.uniform(-.5, .5) * cell, py + rng.uniform(-.5, .5) * cell
                front.append(f'<circle cx="{_f(qx)}" cy="{_f(qy)}" r="{rng.uniform(3, 5):.1f}" fill="{pal["accent"].mid}" fill-opacity=".8"/>')
            x += cell
        y += cell * 0.82
        j += 1
    return "".join(back), "".join(front)


# --------------------------------------------------------------------------- the pictures (families)

def _pair(rng, geo, pal, lush=1.0, fan=115.0):
    """Two bouquets in opposite corners of the page."""
    W, H = geo.W, geo.H
    flip = rng.random() < 0.5
    sA = clamp(geo.top * 0.74, 150, 330)
    sB = clamp(geo.bot * 0.70, 150, 330)
    ax = W * 0.10 if not flip else W * 0.90
    ay = min(geo.top * 0.40, sA * 0.55)
    bx, by = W - ax, H - min(geo.bot * 0.38, sB * 0.55)
    fa = 42 if not flip else 138
    b1 = bouquet(rng, ax, ay, sA, fa, pal, fan=fan, lush=lush)
    b2 = bouquet(rng, bx, by, sB, fa + 180, pal, fan=fan, lush=lush)
    gold = splatter(rng, ax, ay, sA * 1.7, "url(#gold)") + splatter(rng, bx, by, sB * 1.7, "url(#gold)")
    return b1[0] + b2[0], b1[1] + b2[1], gold


def scene_corners(rng, geo, pal):
    back, front, gold = _pair(rng, geo, pal)
    return dict(back=back, front=front, over=gold)


def scene_dots(rng, geo, pal):
    back, front, gold = _pair(rng, geo, pal, lush=0.9)
    return dict(pattern=dots_svg(geo, pal), back=back, front=front, over=gold)


def scene_hydrangea(rng, geo, pal):
    p2 = dict(pal)
    p2["focal"], p2["second"], p2["small"] = ["hydrangea"], ["hydrangea", "hydrangea", "blossom"], ["blossom"]
    back, front, gold = _pair(rng, geo, p2, lush=0.85)
    return dict(back=back, front=front, over=gold)


def scene_garland(rng, geo, pal):
    W, H = geo.W, geo.H
    scale = clamp(geo.top * 0.36, 80, 165)
    g1 = garland(rng, line_pts(-70, geo.top * 0.14, W + 70, geo.top * 0.14, sag=geo.top * 0.40), pal, scale, big_at=[0.04, 0.5, 0.96])
    sB = clamp(geo.bot * 0.34, 70, 150)
    yb = H - geo.bot * 0.46
    g2 = garland(rng, line_pts(W * 0.16, yb, W * 0.84, yb, sag=geo.bot * 0.14), pal, sB, big_at=[0.5])
    gold = splatter(rng, W / 2, geo.top * 0.5, W * 0.42, "url(#gold)", n=30)
    return dict(back=g1[0] + g2[0], front=g1[1] + g2[1], over=gold)


def scene_border(rng, geo, pal):
    """A flower bed growing up from the bottom edge, with a light spray in each top corner."""
    W, H = geo.W, geo.H
    back, front, items = [], [], []
    n = rng.randint(9, 11)
    for i in range(n):
        x = -20 + (W + 40) * (i + rng.uniform(0.2, 0.8)) / n
        r = clamp(geo.bot * rng.uniform(0.15, 0.25), 36, 112)
        h = min(geo.bot * rng.uniform(0.42, 0.95), geo.bot - r * 0.75)
        pts = _curve_pts(x, H + 30, -90 + rng.uniform(-12, 12), h + 30, rng.uniform(-22, 22), n=14)
        green = rng.choice(pal["leaves"])
        back.append(_stem(pts, green.line, 4.2, 1.6))
        for t in (0.22, 0.46, 0.70):
            px, py, pa = pts[int(t * (len(pts) - 1))]
            side = rng.choice([-1, 1])
            back.append(f'<g {tf(px, py, pa + 90 + side * rng.uniform(40, 70), h * rng.uniform(0.24, 0.38) / 100.0)}>'
                        f'{leaf(rng, green, 100, rng.uniform(24, 36), rng.choice(["lf", "lg"]))}</g>')
        items.append([r, pts[-1][0], pts[-1][1], rng.choice(pal["focal"] + pal["second"] + pal["second"] + pal["small"])])
    for _ in range(rng.randint(10, 13)):
        x, L, a, u = rng.uniform(-20, W + 20), geo.bot * rng.uniform(0.35, 0.82), -90 + rng.uniform(-28, 28), rng.random()
        if u < 0.42:
            back.append(leaf_sprig(rng, x, H + 20, a, L, rng.choice(pal["leaves"])))
        elif u < 0.74:
            back.append(spike(rng, x, H + 20, a, L * 1.05, rng.choice(pal["spikes"]), pal["leaves"][0]))
        elif u < 0.90:
            back.append(fern(rng, x, H + 20, a, L, rng.choice(pal["leaves"])))
        else:
            back.append(berries(rng, x, H + 20, a, L, pal["accent"], pal["leaves"][0]))
    _relax(items, 6)
    items = _fit(items)
    items.sort(key=lambda t: t[0])
    for r, x, y, kind in items:
        front.append(place(kind, rng, x, y, r, pal))
    sT = clamp(geo.top * 0.5, 100, 200)
    t1 = bouquet(rng, W * 0.05, geo.top * 0.16, sT, 40, pal, lush=0.6, focal_n=1)
    t2 = bouquet(rng, W * 0.95, geo.top * 0.16, sT, 140, pal, lush=0.6, focal_n=1)
    gold = splatter(rng, W / 2, H - geo.bot * 0.6, W * 0.45, "url(#gold)", n=30)
    return dict(back="".join(back) + t1[0] + t2[0], front="".join(front) + t1[1] + t2[1], over=gold)


def _frame_corners(rng, geo, pal, b, lush=1.0):
    x0, y0, x1, y1 = b
    flip = rng.random() < 0.5
    sA = clamp(y0 * 0.80, 120, 270)
    sB = clamp((geo.H - y1) * 0.72, 120, 270)
    A = (x0 + 12, y0 + 8, 225) if not flip else (x1 - 12, y0 + 8, 315)
    B = (x1 - 12, y1 - 8, 45) if not flip else (x0 + 12, y1 - 8, 135)
    b1 = bouquet(rng, A[0], A[1], sA, A[2], pal, fan=128, lush=lush)
    b2 = bouquet(rng, B[0], B[1], sB, B[2], pal, fan=128, lush=lush)
    gold = splatter(rng, A[0], A[1], sA * 1.5, "url(#gold)", n=18) + splatter(rng, B[0], B[1], sB * 1.5, "url(#gold)", n=18)
    return b1[0] + b2[0], b1[1] + b2[1], gold


def scene_frame(rng, geo, pal):
    """The words inside a fine gold frame, with bouquets over two of its corners."""
    b = geo.panel(22, 26, 34)
    d = rng.choice([d_notch(b, 36), d_round(b, 30), d_notch(b, 22)])
    under = panel_svg(d, pal, fill=mix(pal["ground"], "#ffffff", 0.70), op=0.92)
    back, front, gold = _frame_corners(rng, geo, pal, b)
    return dict(under=under, back=back, front=front, over=gold)


def scene_trellis(rng, geo, pal):
    """A garden lattice with a panel for the words and flowers climbing two corners."""
    b = geo.panel(24, 24, 36)
    under = lattice_svg(geo, pal) + panel_svg(d_round(b, 30), pal)
    back, front, gold = _frame_corners(rng, geo, pal, b, lush=0.9)
    return dict(under=under, back=back, front=front, over=gold)


def scene_stripe(rng, geo, pal):
    """Soft stripes, a panel for the words, a bouquet on the panel's top and bottom edge."""
    H = geo.H
    b = geo.panel(24, 24, 40)
    x0, y0, x1, y1 = b
    under = stripes_svg(geo, pal) + panel_svg(d_notch(b, 34), pal)
    sA = clamp(y0 * 0.62, 110, 230)
    sB = clamp((H - y1) * 0.50, 100, 200)
    b1 = bouquet(rng, (x0 + x1) / 2, y0 - 6, sA, -90, pal, fan=90)
    b2 = bouquet(rng, (x0 + x1) / 2, y1 + 6, sB, 90, pal, fan=90, lush=0.8)
    return dict(under=under, back=b1[0] + b2[0], front=b1[1] + b2[1], over="")


def scene_ditsy(rng, geo, pal):
    """An all-over scatter of tiny blooms, with a scalloped panel for the words."""
    b = geo.panel(24, 24, 36)
    d = d_scallop(b, 24)
    back, front = ditsy_svg(rng, geo, pal)
    return dict(back=back, front=front, top=panel_svg(d, pal), keep=d)


def _branch(rng, x, y, ang, length, pal, wood, depth=0):
    back, front = [], []
    pts, length = _clear_path(x, y, ang, length, rng.uniform(-26, 26), n=18)
    if pts is None:
        return "", ""
    back.append(_stem(pts, wood, max(2.2, length * 0.022), 1.4, op=0.9))
    n = max(3, int(length / 95))
    for i in range(n):
        t = 0.18 + 0.8 * (i + rng.uniform(-.3, .3)) / n
        px, py, pa = pts[min(len(pts) - 1, max(0, int(t * (len(pts) - 1))))]
        side = rng.choice([-1, 1])
        a = math.radians(pa + side * rng.uniform(50, 100))
        d = rng.uniform(10, 34)
        r = rng.uniform(26, 44) * (1.0 if depth == 0 else 0.85)
        fx, fy = px + math.cos(a) * d, py + math.sin(a) * d
        back.append(f'<line x1="{_f(px)}" y1="{_f(py)}" x2="{_f(fx)}" y2="{_f(fy)}" stroke="{wood}" stroke-width="2" stroke-opacity=".8"/>')
        geo = _CTX["geo"]
        if geo is not None and not geo.clear(fx, fy, r, 18):
            continue
        if rng.random() < 0.72:
            front.append(place("blossom", rng, fx, fy, r, pal))
        else:
            front.append(place("bud", rng, fx, fy, r * 0.5, pal, rot=math.degrees(a) + 90))
        if rng.random() < 0.6:
            back.append(f'<g {tf(px, py, pa + 90 - side * rng.uniform(40, 80), rng.uniform(.34, .52))}>{leaf(rng, rng.choice(pal["leaves"]), 100, 30)}</g>')
    if depth < 2:
        for _ in range(rng.randint(2, 3)):
            t = rng.uniform(0.22, 0.72)
            px, py, pa = pts[int(t * (len(pts) - 1))]
            sb, sf = _branch(rng, px, py, pa + rng.choice([-1, 1]) * rng.uniform(22, 48), length * rng.uniform(0.38, 0.55), pal, wood, depth + 1)
            back.append(sb)
            front.append(sf)
    return "".join(back), "".join(front)


def scene_branch(rng, geo, pal):
    """Blossoming branches reaching in from two corners."""
    W, H = geo.W, geo.H
    wood = mix(pal["ink"], pal["ground"], 0.42)
    flip = rng.random() < 0.5
    p2 = dict(pal)
    p2["pale"] = pal["pale"] + pal["flowers"][:2]
    ya = clamp(geo.top * 0.34, 40, 170)
    yb = H - clamp(geo.bot * 0.36, 50, 190)
    if not flip:
        a = _branch(rng, -30, ya * 0.6, 8, W * 0.86, p2, wood)
        b = _branch(rng, W + 30, yb + (H - yb) * 0.4, 188, W * 0.86, p2, wood)
    else:
        a = _branch(rng, W + 30, ya * 0.6, 172, W * 0.86, p2, wood)
        b = _branch(rng, -30, yb + (H - yb) * 0.4, -8, W * 0.86, p2, wood)
    gold = splatter(rng, W / 2, ya, W * 0.5, "url(#gold)", n=22) + splatter(rng, W / 2, yb, W * 0.5, "url(#gold)", n=22)
    return dict(back=a[0] + b[0], front=a[1] + b[1], over=gold)


def scene_arch(rng, geo, pal):
    """A garden arch: an arched panel for the words with a garland over the top."""
    H = geo.H
    b = geo.panel(24, 20, 40)
    x0, y0, x1, y1 = b
    rise = clamp(y0 * 0.42, 40, 150)
    d = d_arch(b, rise)
    under = panel_svg(d, pal, fill=mix(pal["ground"], "#ffffff", 0.72), op=0.94)
    cx, rx = (x0 + x1) / 2, (x1 - x0) / 2
    pts = ellipse_pts(cx, y0, rx, rise, n=60, start=180, sweep=180)
    scale = clamp(y0 * 0.30, 60, 120)
    g = garland(rng, pts, pal, scale, big_at=[0.5])
    sB = clamp((H - y1) * 0.55, 100, 210)
    b1 = bouquet(rng, x0 + 16, y1 - 6, sB, 135, pal, fan=110, lush=0.8)
    b2 = bouquet(rng, x1 - 16, y1 - 6, sB, 45, pal, fan=110, lush=0.8)
    return dict(under=under, back=g[0] + b1[0] + b2[0], front=g[1] + b1[1] + b2[1], over="")


FAMILIES = {
    "corners": scene_corners, "garland": scene_garland, "border": scene_border, "frame": scene_frame,
    "trellis": scene_trellis, "stripe": scene_stripe, "ditsy": scene_ditsy, "branch": scene_branch,
    "hydrangea": scene_hydrangea, "dots": scene_dots, "arch": scene_arch,
}

GOLD_DEF = ('<linearGradient id="gold" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="230" y2="170" spreadMethod="reflect">'
            '<stop offset="0" stop-color="#b08a42"/><stop offset=".35" stop-color="#e9d08a"/><stop offset=".6" stop-color="#c7a258"/>'
            '<stop offset=".85" stop-color="#f2e0a3"/><stop offset="1" stop-color="#b9934b"/></linearGradient>')


def paint_svg(family, mood, seed, W, H, ink, lines=None):
    """The whole picture as SVG, built around the words. `ink` = (x0, y0, x1, y1) is the box that holds
    all the words; `lines` is the same for each line of words, so flowers can come close where a line is short."""
    rng = random.Random(f"{family}|{mood}|{seed}|{W}x{H}")
    pal = MOODS[mood]
    geo = Geo(W, H, ink, lines)
    _CTX["geo"] = geo
    try:
        sc = FAMILIES[family](rng, geo, pal)
    finally:
        _CTX["geo"] = None
    ramps = list(R.values()) + list(G.values())
    if sc.get("keep"):
        shape, mblur = f'<path d="{sc["keep"]}" fill="#000"/>', 1.5
    else:
        shape = "".join(f'<rect x="{_f(a)}" y="{_f(b)}" width="{_f(c - a)}" height="{_f(d - b)}" rx="30" fill="#000"/>' for a, b, c, d in geo.rects)
        mblur = 11
    filt = FILTERS.format(s1=rng.randint(1, 999), s2=rng.randint(1, 999), s3=rng.randint(1, 999), d1=15, d2=6)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'<defs>{defs_for(ramps)}{GOLD_DEF}{filt}'
        f'<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="85"/></filter>'
        f'<filter id="mb" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="{mblur}"/></filter>'
        f'<mask id="keep" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="#fff"/><g filter="url(#mb)">{shape}</g></mask></defs>'
        f'{ground_svg(rng, geo, pal)}{sc.get("under", "")}'
        f'<g mask="url(#keep)">{sc.get("pattern", "")}'
        f'<g filter="url(#wc)" style="isolation:isolate">{sc.get("back", "")}</g>'
        f'<g filter="url(#wcf)">{sc.get("front", "")}</g>{sc.get("over", "")}</g>'
        f'{sc.get("top", "")}</svg>')


# --------------------------------------------------------------------------- what fits where

OPEN = ("corners", "garland", "border", "branch", "hydrangea", "dots")       # no panel: the words sit on the ground colour
NOTES = {
    "corners": "a bouquet in two opposite corners",
    "garland": "a swag of flowers across the top, a small one below",
    "border": "a flower bed growing up from the bottom edge",
    "frame": "a fine gold frame with bouquets over two corners",
    "trellis": "a garden lattice with flowers climbing a panel",
    "stripe": "soft stripes, a panel, a bouquet above and below",
    "ditsy": "an all-over scatter of tiny blooms with a scalloped panel",
    "branch": "blossoming branches from two corners",
    "hydrangea": "hydrangea heads in two corners",
    "dots": "soft dots with a bouquet in two corners",
    "arch": "a garden arch with a garland over it",
}


def fits(family, mood, W, H, ink, lines=None):
    """Can this picture be made well around these words?"""
    geo = Geo(W, H, ink, lines)
    if MOODS[mood]["dark"] and family not in OPEN:
        return False
    if family == "garland":
        return geo.top >= 175 and geo.bot >= 190
    if family == "arch":
        return geo.top >= 190 and geo.bot >= 190
    if family == "border":
        return geo.bot >= 215
    return True


def ink_colour(mood):
    return MOODS[mood]["ink"]


def is_dark(mood):
    return MOODS[mood]["dark"]
