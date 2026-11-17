#!/usr/bin/env python3
"""
Picture painter for the Come to the Fire slides.

Every picture is painted by code from a seed number: sky, land, water, plants and light.
No photos and no AI image tool are used, so a picture can never contain a person.

    paint(family, mood, seed, W, H) -> float32 array (H, W, 3), values 0..1

A "family" is the kind of scene (mountains, sea, stars ...). A "mood" is the light and colour.
The same family + mood + seed always gives the same picture. A new seed gives a new picture.
"""
import math
import colorsys
import numpy as np
import cv2
from scipy.ndimage import gaussian_filter1d

F = np.float32


# --------------------------------------------------------------------------- basics

class R:
    """Seeded chooser. Plain choices and noise use separate streams, so a picture keeps its
    look when it is painted at another size (feed slide and story frame)."""

    def __init__(self, seed):
        self.seed = int(seed)
        self.p = np.random.default_rng(self.seed)
        self.k = 0

    def u(self, a=0.0, b=1.0):
        return float(a + (b - a) * self.p.random())

    def i(self, a, b):
        return int(self.p.integers(a, b + 1))

    def pick(self, seq):
        return seq[int(self.p.integers(0, len(seq)))]

    def nrng(self):
        self.k += 1
        return np.random.default_rng([self.seed, self.k])


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], F) / 255.0


def mix(a, b, t):
    t = np.asarray(t, F)
    if t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def coords(H, W):
    X, Y = np.meshgrid(np.arange(W, dtype=F), np.arange(H, dtype=F))
    return X, Y


def noise2(H, W, rng, beta=2.4, feat=400.0, aniso=1.0):
    """Natural-looking noise, about mean 0 and spread 1. feat = size of the biggest shapes in px.
    aniso > 1 stretches the shapes sideways."""
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.rfftfreq(W)[None, :] * aniso
    f = np.sqrt(fx * fx + fy * fy)
    f0 = 1.0 / float(feat)
    f = np.maximum(f, 1e-9)
    amp = np.where(f < f0, (f / f0) ** 2 * f0 ** (-beta / 2), f ** (-beta / 2))
    amp[0, 0] = 0
    ph = rng.random((H, W // 2 + 1)) * 2 * np.pi
    n = np.fft.irfft2(amp * np.exp(1j * ph), s=(H, W))
    n -= n.mean()
    n /= (n.std() + 1e-9)
    return n.astype(F)


def noise1(W, rng, beta=2.2, feat=600.0):
    f = np.maximum(np.fft.rfftfreq(W), 1e-9)
    f0 = 1.0 / float(feat)
    amp = np.where(f < f0, (f / f0) ** 2 * f0 ** (-beta / 2), f ** (-beta / 2))
    amp[0] = 0
    ph = rng.random(W // 2 + 1) * 2 * np.pi
    n = np.fft.irfft(amp * np.exp(1j * ph), n=W)
    n -= n.mean()
    n /= (n.std() + 1e-9)
    return n.astype(F)


def screen(img, col, a):
    return 1 - (1 - img) * (1 - col[None, None, :] * a[..., None])


def glow(img, X, Y, cx, cy, rad, col, strength, power=1.6):
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / rad
    return screen(img, col, (np.exp(-d ** power) * strength).astype(F))


def disc(img, X, Y, cx, cy, rad, col, soft=1.5):
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    a = np.clip((rad - d) / soft + 0.5, 0, 1)[..., None]
    return img * (1 - a) + col[None, None, :] * a


def fill_below(img, ry, col_top, col_bot, span, Y, soft=1.2, grad=None):
    """Fill everything under the line ry (one y per column). Colour runs from col_top at the
    line `grad` (default: ry itself) to col_bot `span` pixels lower."""
    a = np.clip((Y - ry[None, :]) / soft + 0.5, 0, 1)[..., None]
    g = ry if grad is None else grad
    t = np.clip((Y - g[None, :]) / span, 0, 1)[..., None]
    col = col_top[None, None, :] * (1 - t) + col_bot[None, None, :] * t
    return img * (1 - a) + col * a


# --------------------------------------------------------------------------- moods (light and colour)

MOODS = {
    "rose_dawn": dict(sky=["#232c5a", "#5d5a94", "#cf8aa6", "#ffcfa3"], sun="#fff1dc", glow="#ffab9a",
                      haze="#c39fb8", far="#8d7ea6", near="#1b1630", chi="#ffd8cc", clo="#74659a",
                      water="#35366a", night=0.0),
    "gold_sunrise": dict(sky=["#17304f", "#496f97", "#eaa864", "#ffe0a3"], sun="#fff7e0", glow="#ffc070",
                         haze="#d2ad84", far="#8f8a8e", near="#1d140d", chi="#ffe6b8", clo="#5d6f8c",
                         water="#27435f", night=0.0),
    "fire_sunset": dict(sky=["#160f2e", "#52285c", "#cf4d4a", "#ffad5a"], sun="#ffecb8", glow="#ff7a45",
                        haze="#a35068", far="#6b3a5e", near="#140a12", chi="#ffb07a", clo="#4a2a55",
                        water="#2a1840", night=0.05),
    "violet_dusk": dict(sky=["#0c0f2e", "#2a285c", "#77568f", "#dfa29f"], sun="#ffe3d0", glow="#c98aa8",
                        haze="#69578a", far="#4b4274", near="#0a0916", chi="#e7b3b9", clo="#3a3466",
                        water="#1b1b44", night=0.35),
    "blue_hour": dict(sky=["#061124", "#102c55", "#2b6488", "#93c2c6"], sun="#e9f6ff", glow="#7fb5c9",
                      haze="#3c6783", far="#2c5070", near="#040a12", chi="#a9cfd6", clo="#1d3f5f",
                      water="#0d2740", night=0.45),
    "teal_dawn": dict(sky=["#0a2730", "#1c5560", "#68ac9f", "#f3dca6"], sun="#fff6da", glow="#bfe0b8",
                      haze="#5a9792", far="#3f7a7a", near="#051517", chi="#f8e7bd", clo="#2f6a70",
                      water="#123c44", night=0.0),
    "amber_haze": dict(sky=["#3d4c6c", "#a88375", "#eeb05c", "#ffe6ad"], sun="#fff8e4", glow="#ffbf66",
                       haze="#dcab6c", far="#a8825f", near="#261709", chi="#ffe9bd", clo="#8f7a7c",
                       water="#4b5068", night=0.0),
    "moonlit": dict(sky=["#040812", "#0c1830", "#1c3052", "#395676"], sun="#eef3ff", glow="#8fb0dc",
                    haze="#223655", far="#182a47", near="#02050a", chi="#9fb7d6", clo="#152642",
                    water="#0a1830", night=0.9),
    "deep_night": dict(sky=["#020309", "#060a1c", "#0e1736", "#1b2948"], sun="#f4f6ff", glow="#3f6a9a",
                       haze="#16233f", far="#0f1a33", near="#010205", chi="#5c7399", clo="#0c142b",
                       water="#060d1f", night=1.0),
    "storm_light": dict(sky=["#161b26", "#353e4f", "#83786d", "#efd69b"], sun="#fff4d2", glow="#f1c877",
                        haze="#666b76", far="#474c58", near="#0e1014", chi="#f3deaf", clo="#2a303c",
                        water="#232a36", night=0.0),
    "day_blue": dict(sky=["#0d3672", "#2c69ae", "#79aedb", "#d6ebf7"], sun="#ffffff", glow="#cfe6ff",
                     haze="#7ba5c6", far="#4f86a0", near="#12301a", chi="#ffffff", clo="#9db7cf",
                     water="#1f5c8f", night=0.0),
    "autumn_ember": dict(sky=["#261b36", "#733848", "#da7637", "#ffcc86"], sun="#fff0c8", glow="#ff9a4a",
                         haze="#ab643d", far="#7d4a3a", near="#190d07", chi="#ffc590", clo="#5e3446",
                         water="#3a2238", night=0.0),
    "mint_morning": dict(sky=["#1f4a63", "#5799ab", "#bfe2d2", "#fff2cb"], sun="#fffbe8", glow="#d9f0d0",
                         haze="#95c2b2", far="#5f9a8e", near="#0d2720", chi="#fff8e0", clo="#6c9aa6",
                         water="#2a6a7a", night=0.0),
    "magenta_twilight": dict(sky=["#100926", "#451858", "#a83674", "#ff9876"], sun="#ffe2c4", glow="#ff6f8a",
                             haze="#763874", far="#522a63", near="#0b0514", chi="#ff9fa0", clo="#3c1c52",
                             water="#22103a", night=0.2),
}

# Light palettes for the "soft lights" family.
LIGHTS = {
    "candle_gold": dict(bg=["#0e0704", "#3b1f0b"], lights=["#ffcf7a", "#ffb24d", "#ffe7b0", "#ff8a3d", "#fff3d6"]),
    "rose_lights": dict(bg=["#10050d", "#3a1230"], lights=["#ffb3c7", "#ff7fa3", "#ffd9a0", "#c58cff", "#ffe6ee"]),
    "teal_lights": dict(bg=["#03101a", "#0c3440"], lights=["#7fe0d8", "#bfe9ff", "#ffe7a8", "#4fb7d0", "#e8fbff"]),
    "silver_blue": dict(bg=["#05070f", "#1a2444"], lights=["#c9d8ff", "#8fb0ff", "#fff0c9", "#e9efff", "#7c93d8"]),
}


def _jit(hexstr, dh, ds, dv):
    r, g, b = [int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + dh) % 1.0
    s = min(1.0, max(0.0, s * ds))
    v = min(1.0, max(0.0, v * dv))
    return np.array(colorsys.hsv_to_rgb(h, s, v), F)


def mood_colors(table, name, r):
    """The mood's colours, nudged a little so no two days share exactly the same paint."""
    dh, ds, dv = r.u(-0.02, 0.02), r.u(0.93, 1.07), r.u(0.97, 1.03)
    m = {}
    for k, v in table[name].items():
        if isinstance(v, str):
            m[k] = _jit(v, dh, ds, dv)
        elif isinstance(v, list):
            m[k] = [_jit(x, dh, ds, dv) for x in v]
        else:
            m[k] = v
    return m


# --------------------------------------------------------------------------- building blocks

def sky(H, W, m, hy, r):
    ys = np.arange(H, dtype=F)
    t = np.clip(ys / max(hy, 1.0), 0, 1)
    pos = np.array([0.0, 0.45, 0.80, 1.0])        # the bright colours stay low, near the horizon
    g = np.stack([np.interp(t, pos, [c[k] for c in m["sky"]]) for k in range(3)], axis=1)
    g = gaussian_filter1d(g, sigma=H * 0.03, axis=0, mode="nearest").astype(F)
    img = np.repeat(g[:, None, :], W, axis=1)
    v = noise2(H, W, r.nrng(), beta=3.2, feat=W * 0.9, aniso=1.6)
    return img * (1 + 0.035 * v)[..., None]


def sun(img, X, Y, sx, sy, m, W, size=1.0):
    img = glow(img, X, Y, sx, sy, W * 0.80, m["glow"], 0.38 * size, 1.3)
    img = glow(img, X, Y, sx, sy, W * 0.30, mix(m["glow"], m["sun"], 0.5), 0.45 * size, 1.5)
    img = glow(img, X, Y, sx, sy, W * 0.085, m["sun"], 0.85, 1.8)
    return disc(img, X, Y, sx, sy, W * 0.032 * size, m["sun"])


def clouds(img, H, W, r, m, hy, X, Y, amount=0.4, sunpos=None, streak=2.6, feat=None, opacity=0.8):
    n = noise2(H, W, r.nrng(), beta=3.4, feat=feat or W * 0.5, aniso=streak)
    n = n + 0.2 * noise2(H, W, r.nrng(), beta=2.6, feat=W * 0.12, aniso=streak)
    band = np.exp(-(((Y / max(hy, 1.0)) - r.u(0.25, 0.7)) / 0.36) ** 2)
    dens = sstep(-0.1, 1.7, n * 0.9 + (band - 0.5) * 1.2 + (amount - 0.5) * 1.7)
    if sunpos is not None:
        sx, sy = sunpos
        lit = np.exp(-np.sqrt((X - sx) ** 2 + (Y - sy) ** 2) / W * 2.0)
        sgn = 1 if sx > W / 2 else -1
    else:
        lit = np.full((H, W), 0.3, F)
        sgn = 1
    nb = cv2.GaussianBlur(n, (0, 0), 6)
    relief = sstep(-0.3, 0.3, nb - np.roll(nb, (16, -20 * sgn), axis=(0, 1)))
    col = mix(m["clo"], m["chi"], np.clip(0.15 + 0.85 * lit * (0.4 + 0.6 * relief), 0, 1))
    a = dens * opacity * sstep(hy, hy - H * 0.07, Y)
    return img * (1 - a[..., None]) + col * a[..., None]


def stars(img, H, W, r, X, Y, ymax, n, strength=1.0, weight=None):
    rng = r.nrng()
    lay = np.zeros((H, W), F)
    n = int(n)
    xs = rng.integers(0, W, n)
    ys = np.clip((rng.random(n) ** 1.2) * ymax, 0, H - 1).astype(int)
    b = ((rng.random(n) ** 6) * 0.95 + 0.07).astype(F)
    if weight is not None:
        keep = rng.random(n) < weight[ys, xs]
        xs, ys, b = xs[keep], ys[keep], b[keep]
    np.maximum.at(lay, (ys, xs), b)
    s = cv2.GaussianBlur(lay, (0, 0), 0.75) * 2.4 + cv2.GaussianBlur(lay, (0, 0), 2.2) * 5.0
    s = np.clip(s, 0, 1) * strength * sstep(ymax, ymax * 0.72, Y)
    return screen(img, np.array([0.93, 0.96, 1.0], F), s.astype(F))


def milky_way(img, H, W, r, X, Y, ymax):
    ang = math.radians(r.u(38, 68)) * r.pick([-1, 1])
    cx, cy = W * r.u(0.3, 0.7), ymax * r.u(0.3, 0.55)
    nx, ny = -math.sin(ang), math.cos(ang)
    d = ((X - cx) * nx + (Y - cy) * ny) / (W * r.u(0.17, 0.25))
    band = np.exp(-d * d)
    n1 = noise2(H, W, r.nrng(), beta=2.6, feat=W * 0.5)
    n2 = noise2(H, W, r.nrng(), beta=2.2, feat=W * 0.2)
    cloud = sstep(-1.0, 1.6, n1) * band
    dust = sstep(0.1, 1.5, n2) * np.exp(-(d * 1.6) ** 2)
    mw = np.clip(cloud * (1 - 0.75 * dust), 0, 1) * sstep(ymax, ymax * 0.7, Y)
    col = mix(hexc("#9fb4e8"), hexc("#f1d9c4"), np.clip(1 - np.abs(d), 0, 1) ** 2)
    img = 1 - (1 - img) * (1 - col * (mw * 0.5)[..., None])
    return img, band


def pine_line(W, rng, count, hmin, hmax):
    """Skyline of fir trees: how far each column rises above the ground line."""
    count = max(int(count), 1)
    xs = rng.random(count) * W
    hs = hmin + (rng.random(count) ** 1.6) * (hmax - hmin)
    ws = hs * (0.26 + 0.16 * rng.random(count))
    x = np.arange(W, dtype=F)[None, :]
    dx = np.abs(x - xs[:, None]) / ws[:, None]
    nt = (4 + 4 * hs / max(hmax, 1.0))[:, None]
    prof = hs[:, None] * (1 - dx) + hs[:, None] * 0.06 * (((dx * nt) % 1.0) - 0.5)
    prof = np.where(dx < 1, prof, 0)
    return np.maximum(prof.max(axis=0), 0).astype(F)


def conifers(H, W, rng, ground, count, hmin, hmax):
    """Fir trees with drooping tiers of branches, standing on the line `ground`.
    Drawn at double size and shrunk so the edges are smooth. Returns a 0..1 mask."""
    S = 2
    mk = np.zeros((H * S, W * S), np.uint8)
    for x in np.sort(rng.random(max(int(count), 1)) * W):
        h = hmin + (rng.random() ** 1.4) * (hmax - hmin)
        w = h * (0.17 + 0.08 * rng.random())
        gy = float(ground[int(min(max(x, 0), W - 1))]) + h * 0.04
        n = int(5 + rng.integers(0, 4) + h / 60)
        top = gy - h
        left, right = [], []
        for j in range(n):
            y0 = top + h * (j / n) ** 1.08
            y1 = top + h * ((j + 1) / n) ** 1.08
            wi = w * (j + 0.35) / n * 0.55
            wo = w * (j + 1) / n * (1 + 0.18 * (rng.random() - 0.5))
            droop = (y1 - y0) * 0.28
            left += [(x - wi, y0), (x - wo, y1 + droop)]
            right += [(x + wi, y0), (x + wo, y1 + droop)]
        poly = [(x, top - h * 0.03)] + right + [(x + w * 0.10, gy), (x - w * 0.10, gy)] + left[::-1]
        cv2.fillPoly(mk, [np.array([[px * S, py * S] for px, py in poly], np.int32)], 255, cv2.LINE_AA)
    return cv2.resize(mk, (W, H), interpolation=cv2.INTER_AREA).astype(F) / 255.0


def land_layers(img, H, W, r, m, X, Y, y_top, y_bot, L, amp0=0.03, amp1=0.055, sharp=0.3,
                pines_from=0.5, mist=0.3, snow=False, far=None, near=None, pine_h=0.062, firs=True):
    """Ranges of hills from far (pale, hazy) to near (dark). The nearest range can carry fir trees."""
    far = m["far"] if far is None else far
    near = m["near"] if near is None else near
    haze = m["haze"]
    for i in range(L):
        t = i / max(L - 1, 1)
        last = i == L - 1
        base = y_top + (y_bot - y_top) * (t ** 1.2)
        amp = H * (amp0 + (amp1 - amp0) * t) * r.u(0.8, 1.25)
        feat = W * (1.0 - 0.45 * t)
        n = noise1(W, r.nrng(), beta=2.6 + 0.6 * t, feat=feat)
        sh = sharp * (1 - t) * r.u(0.5, 1.0)
        if sh > 0.02:  # pointed peaks for the far ranges
            rg = 1.25 - 2.1 * np.abs(noise1(W, r.nrng(), beta=3.0, feat=feat * 0.9))
            n = (1 - sh) * n + sh * rg + 0.06 * sh * noise1(W, r.nrng(), beta=1.8, feat=60)
        ground = base - amp * n
        ry = ground
        col = mix(far, near, t ** 1.1)
        col = mix(col, haze, 0.55 * (1 - t) ** 1.6)
        colb = mix(col, haze, mist * (1 - t))
        if t >= pines_from and last and firs:
            tm = conifers(H, W, r.nrng(), ground, W * r.u(0.012, 0.022), H * pine_h * 0.5, H * pine_h * r.u(1.3, 2.0))
            img = img * (1 - tm[..., None]) + col[None, None, :] * tm[..., None]
        elif t >= pines_from:  # a fringe of far-off trees along the ridge
            k = (t - pines_from) / max(1 - pines_from, 1e-6)
            hmax = H * pine_h * (0.2 + 0.8 * k)
            ry = ground - pine_line(W, r.nrng(), W * (0.06 - 0.03 * t), hmax * 0.35, hmax)
        img = fill_below(img, ry, col, colb, H * 0.10, Y, grad=ground)
        if snow and t < 0.5:  # snow caps on the higher peaks, thinning out down the slope
            cap = sstep(0.3, 1.3, (base - ground) / max(amp, 1e-6))
            depth = np.maximum(amp * (0.35 + 0.55 * cap), 1.0)
            edge = 0.75 + 0.25 * sstep(-1, 1, noise1(W, r.nrng(), beta=1.6, feat=70))
            d = (Y - ground[None, :]) / (depth * edge)[None, :]
            a = np.clip(1 - d, 0, 1) ** 1.3 * (d >= 0) * cap[None, :]
            a = cv2.GaussianBlur(a.astype(F), (0, 0), sigmaX=2.5, sigmaY=1.0)
            a = a * np.clip((Y - ground[None, :]) / 1.2 + 0.5, 0, 1)
            img = mix(img, mix(m["chi"], np.ones(3, F), 0.25), a * 0.85)
    return img


def water(img, H, W, hy, r, X, Y, m, sunpos=None, rough=1.0, mirror=0.86, k=1.0):
    """Turn everything under the horizon into water that mirrors what is above it."""
    t = np.clip((Y - hy) / max(H - hy, 1.0), 0, 1)
    rip = noise2(H, W, r.nrng(), beta=1.7, feat=16, aniso=11)
    mx = (W / 2 + (X - W / 2) / (0.28 + 0.72 * t)) % W
    my = (hy + (t ** 0.62) * (H - hy)) % H
    rp = cv2.remap(rip, mx.astype(F), my.astype(F), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    sx_ = X + rp * (3 + 16 * t) * rough
    sy_ = np.clip(hy - 1 - (Y - hy) * k + rp * (1 + 6 * t) * rough, 0, max(hy - 1, 0))
    refl = cv2.remap(img, sx_.astype(F), sy_.astype(F), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=2.5, sigmaY=0.8)
    depth = (0.10 + 0.36 * t)[..., None]
    wat = refl * (1 - depth) * mirror + m["water"][None, None, :] * depth
    wat = wat * (1 + 0.10 * rp * sstep(0.0, 0.5, t))[..., None]
    if sunpos is not None:
        sx, scol = sunpos
        w = W * (0.018 + 0.11 * t)
        g = np.exp(-((X - sx) / w) ** 2) * sstep(0.5, 1.9, rp) * (0.95 - 0.35 * t)
        wat = 1 - (1 - wat) * (1 - scol[None, None, :] * g[..., None])
    return np.where((Y >= hy)[..., None], wat, img).astype(F)


def tree_mask(H, W, r, x0, y0, height):
    """A broad tree, drawn at double size and shrunk so the edges are smooth."""
    S = 2
    mk = np.zeros((H * S, W * S), np.uint8)
    leaves = []

    def branch(x, y, ang, length, thick, depth):
        x2, y2 = x + math.cos(ang) * length, y + math.sin(ang) * length
        cv2.line(mk, (int(x * S), int(y * S)), (int(x2 * S), int(y2 * S)), 255, max(1, int(thick * S)), cv2.LINE_AA)
        if depth <= 4:
            leaves.append((x2, y2, depth))
        if depth == 0 or length < 5:
            return
        kids = 2 if r.u() < 0.7 else 3
        for j in range(kids):
            side = 1 if j % 2 == 0 else -1
            da = r.u(0.26, 0.62) * side * (1 + 0.15 * j)
            na = ang + da + (-math.pi / 2 - ang) * 0.10
            branch(x2, y2, na, length * r.u(0.68, 0.82), thick * 0.70, depth - 1)

    branch(x0, y0 + height * 0.02, -math.pi / 2 + r.u(-0.07, 0.07), height * 0.27, height * 0.05, 8)
    for (lx, ly, d) in leaves:
        rad = height * r.u(0.016, 0.040) * (0.8 + 0.12 * d)
        cv2.circle(mk, (int(lx * S), int(ly * S)), max(2, int(rad * S)), 255, -1, cv2.LINE_AA)
    # flare at the foot of the trunk
    fw = height * 0.06
    pts = np.array([[(x0 - fw) * S, (y0 + height * 0.03) * S], [(x0 + fw) * S, (y0 + height * 0.03) * S],
                    [x0 * S, (y0 - height * 0.10) * S]], np.int32)
    cv2.fillPoly(mk, [pts], 255, cv2.LINE_AA)
    return cv2.resize(mk, (W, H), interpolation=cv2.INTER_AREA).astype(F) / 255.0


# --------------------------------------------------------------------------- the scenes

def sc_ridges(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.62, 0.70)
    img = sky(H, W, m, hy + H * 0.06, r)
    if m["night"] > 0.25:
        img = stars(img, H, W, r, X, Y, hy, 900 * m["night"] * H / 1350, 0.9 * m["night"])
    sx, sy = W * r.u(0.18, 0.82), hy - H * r.u(-0.02, 0.10)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(0.85, 1.25))
    if r.u() < 0.8:
        img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.15, 0.5), sunpos=(sx, sy))
    snow = mood in ("rose_dawn", "blue_hour", "moonlit", "violet_dusk", "magenta_twilight") and r.u() < 0.6
    return land_layers(img, H, W, r, m, X, Y, hy, H * r.u(0.86, 0.93), r.i(5, 7), sharp=r.u(0.2, 0.7), snow=snow)


def sc_pines(H, W, r, m, X, Y, mood):
    img = sky(H, W, m, H * 0.78, r)
    fog = mix(m["haze"], m["sky"][3], 0.45)
    sx, sy = W * r.u(0.25, 0.75), H * r.u(0.14, 0.32)
    img = glow(img, X, Y, sx, sy, W * 0.75, m["glow"], 0.36, 1.3)
    img = glow(img, X, Y, sx, sy, W * 0.13, m["sun"], 0.7, 1.7)
    img = disc(img, X, Y, sx, sy, W * r.u(0.022, 0.034), mix(m["sun"], fog, 0.2))
    L = r.i(5, 7)
    drift = sstep(-1.2, 1.2, noise2(H, W, r.nrng(), beta=3.0, feat=W * 0.7, aniso=3.0))
    tilt = r.u(-0.10, 0.10)
    for i in range(L):
        t = i / (L - 1)
        base = H * (0.52 + 0.52 * t ** 1.15)
        ground = base - H * 0.025 * (1 + t) * noise1(W, r.nrng(), beta=3.2, feat=W * 0.9) + (X[0] - W / 2) * tilt * (1 + t)
        hmax = H * (0.05 + 0.20 * t)
        tm = conifers(H, W, r.nrng(), ground, W * (0.050 - 0.030 * t), hmax * 0.45, hmax)
        col = mix(mix(fog, m["far"], 0.35), m["near"], 0.05 + 0.95 * t ** 1.5)
        colb = mix(col, fog, 0.6 * (1 - t))
        a = np.maximum(tm, np.clip((Y - ground[None, :]) / 1.2 + 0.5, 0, 1))[..., None]
        tt = np.clip((Y - (ground - hmax * 0.3)[None, :]) / (H * 0.13), 0, 1)[..., None]
        img = img * (1 - a) + (col[None, None, :] * (1 - tt) + colb[None, None, :] * tt) * a
        if i < L - 1:
            band = np.exp(-((Y - (base + H * 0.045)) / (H * 0.04)) ** 2) * (0.30 * (1 - t)) * (0.5 + 0.5 * drift)
            img = mix(img, fog, band)
    return img


def sc_sea(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.70, 0.78)
    img = sky(H, W, m, hy, r)
    if m["night"] > 0.25:
        img = stars(img, H, W, r, X, Y, hy, 700 * m["night"] * H / 1350, 0.8 * m["night"])
    sx, sy = W * r.u(0.25, 0.75), hy - H * r.u(0.012, 0.08)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(0.9, 1.3))
    img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.25, 0.62), sunpos=(sx, sy))
    if r.u() < 0.6:  # far headland on one side
        side = r.pick([-1, 1])
        n = noise1(W, r.nrng(), beta=2.4, feat=W * 0.5)
        reach = sstep(W * r.u(0.30, 0.55), 0, X[0] if side < 0 else W - X[0])
        ry = hy - H * 0.05 * reach * (0.6 + 0.4 * sstep(-1, 1, n)) + 1
        img = fill_below(img, ry, mix(m["far"], m["haze"], 0.35), mix(m["far"], m["haze"], 0.5), H * 0.05, Y)
    img = glow(img, X, Y, sx, hy, W * 0.6, m["glow"], 0.22, 1.2)
    return water(img, H, W, hy, r, X, Y, m, sunpos=(sx, m["sun"]), rough=r.u(0.8, 1.3), k=r.u(0.9, 1.2))


def sc_lake(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.68, 0.75)
    img = sky(H, W, m, hy, r)
    if m["night"] > 0.25:
        img = stars(img, H, W, r, X, Y, hy, 900 * m["night"] * H / 1350, 0.9 * m["night"])
    sx, sy = W * r.u(0.2, 0.8), hy - H * r.u(0.14, 0.30)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(0.75, 1.05))
    if r.u() < 0.75:
        img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.12, 0.4), sunpos=(sx, sy))
    snow = mood in ("rose_dawn", "blue_hour", "moonlit", "violet_dusk", "teal_dawn") and r.u() < 0.7
    img = land_layers(img, H, W, r, m, X, Y, hy - H * r.u(0.15, 0.22), hy - H * 0.012, r.i(3, 5),
                      amp0=0.065, amp1=0.02, sharp=r.u(0.35, 0.85), pines_from=0.72, mist=0.5, snow=snow,
                      pine_h=0.034)
    img = water(img, H, W, hy, r, X, Y, m, rough=r.u(0.25, 0.6), mirror=0.9, k=1.0)
    band = np.exp(-((Y - hy) / (H * 0.022)) ** 2) * 0.38
    return mix(img, mix(m["haze"], m["sky"][3], 0.5), band)


def sc_stars(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.76, 0.86)
    img = sky(H, W, m, hy, r)
    img = glow(img, X, Y, W * r.u(0.1, 0.9), hy + H * 0.03, W * 1.0, m["glow"], r.u(0.28, 0.48), 1.2)
    moon = mood == "moonlit"
    band = None
    if not moon:
        img, band = milky_way(img, H, W, r, X, Y, hy)
    img = stars(img, H, W, r, X, Y, hy, (1100 if moon else 2600) * H / 1350, 1.0)
    if band is not None:
        img = stars(img, H, W, r, X, Y, hy, 5200 * H / 1350, 0.85, weight=band)
    if moon:
        mx_, my_ = W * r.u(0.2, 0.8), hy * r.u(0.18, 0.4)
        img = sun(img, X, Y, mx_, my_, m, W, size=r.u(0.8, 1.0))
        img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.22, 0.42), sunpos=(mx_, my_), streak=3.5, opacity=0.6)
    if r.u() < 0.4:  # a shooting star
        lay = np.zeros((H, W), F)
        x0, y0 = W * r.u(0.15, 0.85), hy * r.u(0.08, 0.4)
        ang, ln = math.radians(r.u(18, 40)) * r.pick([-1, 1]), W * r.u(0.10, 0.20)
        for s in np.linspace(0, 1, 260):
            x, y = int(x0 + math.cos(ang) * ln * s), int(y0 + abs(math.sin(ang)) * ln * s)
            if 0 <= x < W and 0 <= y < H:
                lay[y, x] = max(lay[y, x], s ** 2.2)
        img = screen(img, np.ones(3, F), np.clip(cv2.GaussianBlur(lay, (0, 0), 1.1) * 3.2, 0, 1))
    return land_layers(img, H, W, r, m, X, Y, hy, H * 0.95, r.i(2, 3), amp0=0.02, amp1=0.035,
                       sharp=r.u(0, 0.4), pines_from=0.4, mist=0.15)


AURORA = [("#3dffa2", "#8b5cff"), ("#62ffd0", "#ff5fa8"), ("#8dff6a", "#3fb7ff"), ("#37f0c0", "#b57bff")]


def sc_aurora(H, W, r, m, X, Y, mood):
    lake = r.u() < 0.6
    hy = H * (r.u(0.70, 0.78) if lake else r.u(0.78, 0.86))
    img = sky(H, W, m, hy, r)
    img = stars(img, H, W, r, X, Y, hy, 1500 * H / 1350, 0.85)
    lo, hi = [hexc(c) for c in r.pick(AURORA)]
    lay = np.zeros((H, W, 3), F)
    for _ in range(r.i(2, 3)):
        base = hy * r.u(0.42, 0.78)
        path = base + noise1(W, r.nrng(), beta=3.2, feat=W * 0.9) * H * 0.06 + (X[0] - W / 2) * r.u(-0.22, 0.22)
        length = H * r.u(0.20, 0.36)
        above = path[None, :] - Y
        inten = np.where(above > 0, np.exp(-above / length), np.exp(above / (H * 0.010)))
        rays = 0.5 + 0.5 * sstep(-1.0, 1.0, noise1(W, r.nrng(), beta=1.3, feat=70))[None, :]
        fold = 0.45 + 0.55 * sstep(-1.2, 1.2, noise1(W, r.nrng(), beta=2.6, feat=W * 0.5))[None, :]
        a = inten * rays * fold * r.u(0.55, 0.85)
        col = mix(lo, hi, np.clip(above / length, 0, 1) ** 0.8)
        lay += col * a[..., None]
    lay = cv2.GaussianBlur(lay, (0, 0), 3.0)
    img = 1 - (1 - img) * (1 - np.clip(lay, 0, 1) * 0.9)
    far = mix(m["far"], lo, 0.18)
    img = land_layers(img, H, W, r, m, X, Y, hy - H * r.u(0.10, 0.16), hy - H * 0.01 if lake else H * 0.95,
                      r.i(3, 4), amp0=0.055, amp1=0.022, sharp=r.u(0.4, 0.85), pines_from=0.7, mist=0.2,
                      snow=True, far=far, pine_h=0.034)
    if lake:
        img = water(img, H, W, hy, r, X, Y, m, rough=r.u(0.3, 0.6), mirror=0.92)
    return img


def sc_dunes(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.60, 0.70)
    img = sky(H, W, m, hy + H * 0.04, r)
    if m["night"] > 0.25:
        img = stars(img, H, W, r, X, Y, hy, 1200 * m["night"] * H / 1350, m["night"])
    sx, sy = W * r.pick([r.u(0.12, 0.38), r.u(0.62, 0.88)]), hy - H * r.u(0.03, 0.2)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(0.9, 1.3))
    if r.u() < 0.5:
        img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.1, 0.32), sunpos=(sx, sy), streak=4.0)
    ld = 1.0 if sx < W / 2 else -1.0
    sand_l = mix(mix(m["haze"], m["glow"], 0.55), m["sun"], 0.3)
    sand_s = mix(m["near"], m["far"], 0.5)
    grain = 1 + 0.025 * noise2(H, W, r.nrng(), beta=1.6, feat=40, aniso=3.0)
    L = r.i(4, 6)
    for i in range(L):
        t = i / (L - 1)
        base = hy + (H * 1.04 - hy) * (t ** 1.2) * 0.84
        amp = H * (0.022 + 0.07 * t) * r.u(0.8, 1.2)
        ry = base - amp * noise1(W, r.nrng(), beta=3.6, feat=W * (1.5 - 0.5 * t))
        slope = np.gradient(gaussian_filter1d(ry, 10, mode="wrap"))
        d = np.clip(Y - ry[None, :], 0, None)
        xs = np.clip(X - d * r.u(0.35, 0.8) * ld, 0, W - 1).astype(np.int32)
        shade = cv2.GaussianBlur(sstep(-0.02, 0.02, slope * ld)[xs].astype(F), (0, 0), 1.5)
        lc = mix(sand_l, m["haze"], 0.55 * (1 - t))
        sc = mix(sand_s, m["haze"], 0.45 * (1 - t))
        col = lc[None, None, :] * (1 - shade[..., None]) + sc[None, None, :] * shade[..., None]
        kk = (sstep(0, H * 0.2, d) * 0.5)[..., None]
        col = col * (1 - kk) + ((lc + sc) / 2)[None, None, :] * kk
        rim = (np.exp(-d / 5.0) * (1 - shade) * 0.3)[..., None]          # sunlit edge of each crest
        col = col * (1 - rim) + m["sun"][None, None, :] * rim
        a = np.clip((Y - ry[None, :]) / 1.2 + 0.5, 0, 1)[..., None]
        img = img * (1 - a) + col * grain[..., None] * a
    return img


CROPS = [("#9a72c8", "#2a3722"), ("#e6b85c", "#7a5620"), ("#7fae45", "#213f18"), ("#d9788f", "#27401f")]


def sc_field(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.68, 0.76)
    img = sky(H, W, m, hy, r)
    sx, sy = W * r.u(0.2, 0.8), hy - H * r.u(0.015, 0.11)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(0.9, 1.25))
    img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.2, 0.55), sunpos=(sx, sy))
    # far tree line and low hills on the horizon
    img = land_layers(img, H, W, r, m, X, Y, hy - H * 0.035, hy - H * 0.004, 2, amp0=0.022, amp1=0.008,
                      sharp=0.0, pines_from=0.9, mist=0.4, pine_h=0.02)
    crest, valley = [hexc(c) for c in r.pick(CROPS)]
    light = mix(np.ones(3, F), m["glow"], 0.45)
    crest, valley = crest * light, valley * mix(np.ones(3, F), m["haze"], 0.25)
    t = np.clip((Y - hy) / max(H - hy, 1.0), 1e-4, 1)
    vx = W * r.u(0.3, 0.7)
    u = (X - vx) / (t * W)
    stripe = (0.5 + 0.5 * np.cos(2 * np.pi * u * r.u(5.5, 9.0))) ** 1.6
    con = sstep(0.012, 0.22, t)
    tex = noise2(H, W, r.nrng(), beta=1.3, feat=9)
    v = (stripe * con + 0.45 * (1 - con))
    col = crest[None, None, :] * v[..., None] + valley[None, None, :] * (1 - v[..., None])
    col = col * (1 + 0.10 * tex * con)[..., None]
    far = mix(m["haze"], m["sky"][3], 0.35)
    col = mix(col, far, np.exp(-t * 5.5) * 0.9)
    col = col * (1 - 0.30 * sstep(0.55, 1.0, t))[..., None]      # the near ground falls into shade
    img = np.where((Y >= hy)[..., None], col, img)
    return glow(img, X, Y, sx, hy, W * 0.55, m["glow"], 0.22, 1.2)


def sc_cloudsea(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.58, 0.68)
    img = sky(H, W, m, hy, r)
    if m["night"] > 0.25:
        img = stars(img, H, W, r, X, Y, hy, 700 * m["night"] * H / 1350, 0.8 * m["night"])
    sx, sy = W * r.u(0.2, 0.8), hy - H * r.u(0.0, 0.06)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(1.0, 1.4))
    img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.12, 0.3), sunpos=(sx, sy), streak=5.0)
    T = 1024
    tex = noise2(T, T, r.nrng(), beta=3.4, feat=420) + 0.18 * noise2(T, T, r.nrng(), beta=2.6, feat=90)
    texb = cv2.GaussianBlur(tex, (0, 0), 9)
    t = np.clip((Y - hy) / max(H - hy, 1.0), 1e-3, 1)
    su = r.u(0.5, 0.75)
    sv = su * 1.2                                   # keeps the cloud shapes round instead of streaked
    mx = ((((X - W / 2) / (t * W)) * su) % 1.0) * T
    my = (((1.0 / t) * sv) % 1.0) * T
    h1 = cv2.remap(tex, mx.astype(F), my.astype(F), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    h2 = cv2.remap(texb, mx.astype(F), my.astype(F), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    k = sstep(0.04, 0.35, t)
    h = cv2.GaussianBlur(h2 * (1 - k) + h1 * k, (0, 0), 1.5)
    hb = cv2.GaussianBlur(h, (0, 0), 5)
    sgn = 1 if sx > W / 2 else -1
    relief = sstep(-0.22, 0.22, hb - np.roll(hb, (12, -14 * sgn), axis=(0, 1)))     # tops lit from the sun side
    col = mix(mix(m["clo"], m["chi"], 0.3), m["chi"], sstep(-1.5, 1.5, h) * (0.5 + 0.5 * relief))
    col = mix(col, mix(m["sky"][3], m["glow"], 0.3), np.exp(-t * 6.0))
    img = np.where((Y >= hy)[..., None], col, img)
    for _ in range(r.i(0, 2)):  # a mountain top or two rising through the cloud
        by = hy + (H - hy) * r.u(0.08, 0.20)
        x0, w = W * r.u(0.12, 0.88), W * r.u(0.14, 0.26)
        bump = np.clip(1 - np.abs(X[0] - x0) / w, 0, 1) ** 1.25
        bump = bump * (1 + 0.16 * noise1(W, r.nrng(), beta=2.4, feat=W * 0.12))
        ry = by - bump * H * r.u(0.06, 0.11)
        a = np.clip((Y - ry[None, :]) / 1.2 + 0.5, 0, 1) * sstep(by + H * 0.03, by - H * 0.012, Y) * (bump > 0.02)[None, :]
        img = mix(img, mix(m["near"], m["far"], 0.45), a)
    img = glow(img, X, Y, sx, hy, W * 0.6, m["glow"], 0.28, 1.2)
    return np.clip(img, 0, 1)


def sc_rays(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.70, 0.80)
    img = sky(H, W, m, hy, r)
    sx, sy = W * r.u(0.3, 0.7), H * r.u(0.15, 0.28)
    img = glow(img, X, Y, sx, sy, W * 0.6, m["glow"], 0.6, 1.3)
    img = glow(img, X, Y, sx, sy, W * 0.17, m["sun"], 0.9, 1.6)
    n = noise2(H, W, r.nrng(), beta=3.5, feat=W * 0.6, aniso=1.5) + 0.2 * noise2(H, W, r.nrng(), beta=2.6, feat=W * 0.14)
    d = np.sqrt((X - sx) ** 2 + ((Y - sy) * 1.25) ** 2) / W
    dens = sstep(-0.5, 0.9, n * 0.75 + sstep(0.05, 0.34, d) * 1.25 - 0.55) * sstep(hy, hy - H * 0.05, Y)
    edge = dens * (1 - dens) * 4
    lit = np.exp(-d * 3.0)
    ccol = mix(m["clo"] * 0.62, m["chi"], np.clip(edge * lit * 1.5 + lit * 0.3, 0, 1))
    img = img * (1 - (dens * 0.94)[..., None]) + ccol * (dens * 0.94)[..., None]
    th = np.arctan2(Y - sy, X - sx)
    N = 4096
    rn = sstep(0.0, 1.6, noise1(N, r.nrng(), beta=2.7, feat=520))       # a few broad beams, not a starburst
    ray = rn[np.clip(((th / np.pi) % 1.0) * (N - 1), 0, N - 1).astype(np.int32)]
    rr = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
    inten = ray * np.exp(-rr / (H * 0.95)) * sstep(W * 0.05, W * 0.30, rr) * (Y > sy) * (1 - 0.55 * dens)
    img = 1 - (1 - img) * (1 - m["chi"][None, None, :] * (inten * 0.5)[..., None])
    if r.u() < 0.5:
        img = land_layers(img, H, W, r, m, X, Y, hy, H * 0.95, r.i(2, 4), amp0=0.02, amp1=0.04,
                          sharp=r.u(0, 0.5), pines_from=0.5, mist=0.45)
    else:
        img = water(img, H, W, hy, r, X, Y, m, sunpos=(sx, m["chi"]), rough=r.u(0.8, 1.2), mirror=0.8)
    return img


def sc_tree(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.78, 0.84)
    img = sky(H, W, m, hy + H * 0.05, r)
    if m["night"] > 0.25:
        img = stars(img, H, W, r, X, Y, hy, 1400 * m["night"] * H / 1350, m["night"])
    tx = W * r.u(0.30, 0.70)
    sx = tx + W * r.u(0.10, 0.30) * r.pick([-1, 1])
    sy = hy - H * r.u(0.02, 0.14)
    img = sun(img, X, Y, sx, sy, m, W, size=r.u(1.0, 1.4))
    if r.u() < 0.7:
        img = clouds(img, H, W, r, m, hy, X, Y, amount=r.u(0.12, 0.42), sunpos=(sx, sy))
    img = land_layers(img, H, W, r, m, X, Y, hy - H * 0.03, hy + H * 0.02, 2, amp0=0.03, amp1=0.02,
                      sharp=0.1, pines_from=2.0, mist=0.5)
    # the hill the tree stands on
    hill = hy + H * 0.05 - H * 0.045 * np.exp(-((X[0] - tx) / (W * 0.55)) ** 2) + H * 0.012 * noise1(W, r.nrng(), 3.2, W * 0.8)
    dark = mix(m["near"], m["far"], 0.06)
    img = fill_below(img, hill - pine_line(W, r.nrng(), W * 0.5, 2, H * 0.006), dark, m["near"], H * 0.2, Y)
    th = H * r.u(0.36, 0.46) * (1350.0 / H) ** 0.35
    a = tree_mask(H, W, r, tx, float(hill[int(np.clip(tx, 0, W - 1))]), th)
    return img * (1 - a[..., None]) + dark[None, None, :] * a[..., None]


def sc_bokeh(H, W, r, m, X, Y, mood):
    pal = mood_colors(LIGHTS, mood, r)
    cx, cy = W * r.u(0.25, 0.75), H * r.u(0.35, 0.8)
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / (0.95 * H)
    img = mix(pal["bg"][1], pal["bg"][0], np.clip(d, 0, 1) ** 0.9)
    img = img * (1 + 0.05 * noise2(H, W, r.nrng(), beta=3.0, feat=W * 0.8))[..., None]
    lay = np.zeros((H, W, 3), F)
    for _ in range(r.i(80, 130)):
        rad = W * math.exp(r.u(math.log(0.012), math.log(0.09)))
        x, y = r.u(-0.05, 1.05) * W, r.u(-0.05, 1.05) * H
        col = r.pick(pal["lights"])
        al = r.u(0.05, 0.26) * (0.035 * W / rad) ** 0.4
        x0, x1 = int(max(0, x - rad - 3)), int(min(W, x + rad + 3))
        y0, y1 = int(max(0, y - rad - 3)), int(min(H, y + rad + 3))
        if x1 <= x0 or y1 <= y0:
            continue
        dd = np.sqrt((X[y0:y1, x0:x1] - x) ** 2 + (Y[y0:y1, x0:x1] - y) ** 2)
        mk = np.clip((rad - dd) / (rad * 0.08 + 1), 0, 1)
        ring = np.exp(-((dd - rad * 0.93) / (rad * 0.07 + 1)) ** 2) * 0.6
        lay[y0:y1, x0:x1] += col[None, None, :] * (mk * (1 + ring) * al)[..., None]
    lay = lay + cv2.GaussianBlur(lay, (0, 0), 14) * 0.5
    return 1 - (1 - np.clip(img, 0, 1)) * (1 - np.clip(lay, 0, 1))


def sc_meadow(H, W, r, m, X, Y, mood):
    hy = H * r.u(0.64, 0.72)
    img = sky(H, W, m, hy + H * 0.03, r)
    sx, sy = W * r.u(0.15, 0.85), hy * r.u(0.15, 0.45)
    img = glow(img, X, Y, sx, sy, W * 0.6, m["glow"], 0.35, 1.3)
    n = noise2(H, W, r.nrng(), beta=3.6, feat=W * 0.45, aniso=1.6) + 0.15 * noise2(H, W, r.nrng(), beta=2.7, feat=W * 0.1)
    dens = sstep(0.1, 1.3, n + (r.u(0.25, 0.5) - 0.5) * 1.6) * sstep(hy, hy - H * 0.12, Y)
    nb = cv2.GaussianBlur(n, (0, 0), 8)
    relief = sstep(-0.3, 0.3, nb - np.roll(nb, (22, 0), axis=(0, 1)))            # bright tops, soft grey bases
    ccol = mix(m["clo"], m["chi"], 0.3 + 0.7 * relief)
    img = img * (1 - (dens * 0.9)[..., None]) + ccol * (dens * 0.9)[..., None]
    grass_far = mix(m["far"], hexc("#7fa56a"), 0.5)
    grass_near = mix(m["near"], hexc("#234f1f"), 0.65)
    L = r.i(4, 5)
    for i in range(L):
        t = i / (L - 1)
        base = hy + (H * 1.0 - hy) * (t ** 1.2) * 0.8
        ry = base - H * (0.03 + 0.035 * t) * noise1(W, r.nrng(), beta=3.5, feat=W * (1.2 - 0.4 * t))
        col = mix(mix(grass_far, m["haze"], 0.55 * (1 - t)), grass_near, t ** 1.1)
        top = mix(col, mix(m["chi"], hexc("#d7e59a"), 0.6), 0.22)                 # sun on the brow of each hill
        img = fill_below(img, ry, top, col * 0.9, H * 0.12, Y)
    # a scatter of small flowers on the nearest slope
    rng = r.nrng()
    cnt = int(260 * W / 1080)
    fx = rng.integers(0, W, cnt)
    fy = (ry[fx] + H * 0.01 + (rng.random(cnt) ** 0.7) * (H - ry[fx])).astype(int)
    ok = (fy >= 0) & (fy < H)
    lay = np.zeros((H, W, 3), F)
    cols = np.stack([hexc(c) for c in ("#fff6c2", "#ffd24a", "#ffb3cf", "#ffffff")])
    lay[fy[ok], fx[ok]] = cols[rng.integers(0, 4, cnt)][ok]
    lay = cv2.GaussianBlur(lay, (0, 0), 2.6) * (2 * np.pi * 2.6 * 2.6) * 0.5
    return np.clip(img + lay * 0.6, 0, 1)


# family -> (painter, moods it may use, colour table)
FAMILIES = {
    "ridges": (sc_ridges, ["rose_dawn", "gold_sunrise", "fire_sunset", "violet_dusk", "blue_hour", "teal_dawn",
                           "amber_haze", "moonlit", "autumn_ember", "magenta_twilight", "mint_morning"]),
    "pines": (sc_pines, ["teal_dawn", "blue_hour", "amber_haze", "storm_light", "violet_dusk", "mint_morning"]),
    "sea": (sc_sea, ["rose_dawn", "gold_sunrise", "fire_sunset", "violet_dusk", "blue_hour", "moonlit",
                     "magenta_twilight", "amber_haze"]),
    "lake": (sc_lake, ["rose_dawn", "teal_dawn", "blue_hour", "violet_dusk", "moonlit", "fire_sunset", "gold_sunrise"]),
    "stars": (sc_stars, ["deep_night", "moonlit", "blue_hour"]),
    "aurora": (sc_aurora, ["deep_night"]),
    "dunes": (sc_dunes, ["fire_sunset", "amber_haze", "violet_dusk", "moonlit", "rose_dawn", "autumn_ember"]),
    "field": (sc_field, ["fire_sunset", "amber_haze", "rose_dawn", "violet_dusk", "gold_sunrise", "magenta_twilight"]),
    "cloudsea": (sc_cloudsea, ["rose_dawn", "gold_sunrise", "fire_sunset", "violet_dusk", "magenta_twilight", "blue_hour"]),
    "rays": (sc_rays, ["storm_light", "violet_dusk", "fire_sunset", "blue_hour"]),
    "tree": (sc_tree, ["gold_sunrise", "fire_sunset", "rose_dawn", "violet_dusk", "deep_night", "amber_haze",
                       "magenta_twilight"]),
    "bokeh": (sc_bokeh, ["candle_gold", "rose_lights", "teal_lights", "silver_blue"]),
    "meadow": (sc_meadow, ["day_blue", "mint_morning"]),
}


def paint(family, mood, seed, W=1080, H=1350):
    fn, moods = FAMILIES[family]
    if mood not in moods:
        raise ValueError(f"{family} cannot use the mood {mood}")
    r = R(seed)
    m = mood_colors(MOODS, mood, r) if mood in MOODS else None
    X, Y = coords(H, W)
    img = np.clip(fn(H, W, r, m, X, Y, mood), 0, 1).astype(F)
    # soft darkening toward the corners, then fine grain so smooth skies do not band
    d = np.sqrt(((X - W / 2) / (W * 0.72)) ** 2 + ((Y - H / 2) / (H * 0.72)) ** 2)
    img = img * (1 - 0.22 * sstep(0.55, 1.25, d))[..., None]
    g = r.nrng().normal(0, 0.011, (H, W)).astype(F)
    return np.clip(img + g[..., None], 0, 1)


if __name__ == "__main__":
    import sys
    from PIL import Image
    fam, mood, seed, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    Image.fromarray((paint(fam, mood, seed) * 255 + 0.5).astype(np.uint8)).save(out, quality=92)
