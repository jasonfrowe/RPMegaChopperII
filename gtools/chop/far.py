"""Plane 0: the night sky, the aurora and the far mountains.

The layer is 512 pixels wide and repeats; it scrolls at a quarter of the
ground's speed. Row 0 of the image is screen row FAR_Y.
"""

from __future__ import annotations

import math

import numpy as np

from . import pal
from .paint import bayer, fbm, wave

W = 512
FAR_Y = 16      # screen row of the image's top
H = 200         # down to screen row 216, under the hills by then
HORIZON = 150   # image row where the sky is at its lightest


CURTAINS = [(78, 16, 46, (2, 3)), (46, 10, 30, (3, 5))]


def sky(img, yy, d8):
    """A gradient through the six sky colors, dithered so each band of
    tiles is the same all the way across."""
    t = np.clip(yy / HORIZON, 0, 1) ** 1.25 * 5
    img[:] = np.clip(np.floor(t + d8), 0, 5).astype(np.uint8)


def aurora(img, yy, xx, d8, seed, curtains=CURTAINS):
    """Curtains hanging from wavy lower edges, (lower edge row, its sway,
    height, (cycles across the layer)) each. Brightest at the lower edge and
    fading upward in vertical rays. Each pixel's slot (8-12) picks which
    step of the brightness wave it shows, so the game's palette rotation
    sends light rippling along the curtain."""
    aur = np.zeros((H, W))
    phase = np.zeros((H, W))
    for k, (base, amp, height, cyc) in enumerate(curtains):
        edge = base + wave(W, [(cyc[0], amp), (cyc[1], amp * 0.45), (7, 2.5)], seed + k)
        hgt = height + wave(W, [(2, height * 0.3), (5, height * 0.15)], seed + 10 + k)
        rays = 0.55 + 0.45 * fbm(1, W, 6, seed + 20 + k, octaves=2)[0]
        rays = rays * (0.75 + 0.25 * np.sin(2 * math.pi * 23 * np.arange(W) / W + k))
        up = (edge[None, :] - yy)                       # pixels above the lower edge
        inside = (up >= -2) & (up <= hgt[None, :])
        fall = np.where(up < 0, 1.0 + up * 0.45, np.exp(-np.clip(up, 0, None) / (hgt[None, :] * 0.42)))
        strength = np.where(inside, fall * rays[None, :], 0) * (1.0 if k == 0 else 0.7)
        aur = np.maximum(aur, strength)
        phase = np.where(strength > 0, (xx / 5.0 + up / 9.0 + k * 2), phase)
    slot = (np.floor(phase) % 5).astype(np.uint8)
    lit = aur > (0.10 + d8 * 0.85)
    img[lit] = pal.FAR_AURORA + slot[lit]


def stars(img, rng, ridge, n=140, top=120):
    """Stars in clear sky above the ridge line, a few bright ones with a
    cross of dim light."""
    clear = img < len(pal.SKY)
    for _ in range(n):
        x, y = rng.integers(0, W), rng.integers(0, top)
        if not clear[y, x] or y >= ridge[x] - 6:
            continue
        if rng.random() < 0.18 and 1 <= y < H - 1:
            img[y, x] = 7
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if clear[y + dy, (x + dx) % W]:
                    img[y + dy, (x + dx) % W] = 6
        else:
            img[y, x] = 7 if rng.random() < 0.3 else 6


def paint(seed=7):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    d8 = bayer(H, W, 8)
    sky(img, yy, d8)
    aurora(img, yy, xx, d8, seed)

    # Mountains: a range of peaks, each a pair of faces meeting at a ridge
    # line. The left face takes the light, the right face is in shadow, and
    # snow gullies run down both along the fall line.
    peaks = []
    x = 0.0
    while x < W:
        w = rng.uniform(40, 90)
        py = rng.uniform(84, 126)
        peaks.append((x + w * 0.5, py, rng.uniform(0.6, 1.0), rng.uniform(0.6, 1.0)))
        x += w * rng.uniform(0.5, 0.75)
    # Back to front: the lower a peak's summit, the nearer it stands.
    peaks.sort(key=lambda p: p[1])
    jag = (fbm(1, W, 3, seed + 35, octaves=2)[0] - 0.5) * 7
    top = np.full((H, W), np.inf)
    side = np.zeros((H, W))
    seam = np.zeros((H, W), bool)
    for i, (px, py, sl, sr) in enumerate(peaks):
        for wrap in (-W, 0, W):
            dx = xx - (px + wrap)
            surf = py + np.where(dx < 0, -dx * sl, dx * sr) + jag[None, :] * np.clip(np.abs(dx) / 6, 0, 1)
            inside = yy >= surf
            # Where a nearer peak's outline crosses one behind it, draw a seam.
            seam = np.where(inside, (yy - surf < 1.0) & np.isfinite(top), seam)
            top = np.where(inside, surf, top)
            side = np.where(inside, dx, side)
    below = yy - top
    mount = np.isfinite(top)
    tex = fbm(H, W, 6, seed + 33, octaves=3)
    # Gullies: noise sampled along the fall line, so streaks run diagonally.
    sl_dir = np.where(side < 0, 1.0, -1.0)
    gx = (xx + sl_dir * yy * 0.8) % W
    gul = fbm(1, W, 5, seed + 34, octaves=2)[0][gx.astype(int)]
    lit = side < 0
    depth = np.clip(below / 60.0, 0, 1)
    v = np.where(lit, 0.82, 0.38) - depth * 0.35 + (gul - 0.5) * 0.55 + (d8 - 0.5) * 0.3
    col = np.where(v > 0.78, 15, np.where(v > 0.55, 14, np.where(v > 0.32, 13, np.where(v > 0.15, 4, 3))))
    # Exposed rock on the shadowed faces, high up.
    rock = (~lit) & (tex > 0.6) & (below > 3) & (below < 40)
    col = np.where(rock, 3, col)
    # The ridge line itself is bright where the lit face meets the sky.
    edge = mount & ~np.roll(mount, 1, axis=0)
    col = np.where(edge & lit, 15, col)
    col = np.where(edge & ~lit, 14, col)
    # The base fades into haze where the hills will cover it.
    haze = depth > 0.8
    col = np.where(haze & (d8 < (depth - 0.8) * 5), 5, col)
    img[mount] = col[mount].astype(np.uint8)
    img[mount & seam & ~edge] = 3
    ridge = np.where(mount, yy, H).min(axis=0)

    # Foothills in front: low, smooth and in shadow, so they cost few tiles.
    ridge2 = 160 + wave(W, [(3, 5), (5, 4), (8, 2)], seed + 40)
    below2 = yy - ridge2[None, :]
    m2 = below2 >= 0
    v2 = 0.55 - np.clip(below2 / 30.0, 0, 1) * 0.4 + (d8 - 0.5) * 0.3
    c2 = np.where(v2 > 0.5, 13, np.where(v2 > 0.3, 4, 3))
    img[m2] = c2[m2].astype(np.uint8)
    img[m2 & ~np.roll(m2, 1, axis=0)] = 14

    # Stars: only in clear sky above the mountains.
    stars(img, rng, ridge)
    return img
