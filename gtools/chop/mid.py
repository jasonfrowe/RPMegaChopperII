"""Plane 1: snowy hills and pine forest between the mountains and the ground.

The layer is 1024 pixels wide and repeats; it scrolls at half the ground's
speed. Row 0 of the image is screen row MID_Y. Index 0 is transparent.
"""

from __future__ import annotations

import numpy as np

from . import pal
from .paint import bayer, fbm, wave

W = 1024
MID_Y = 120
H = 96          # down to screen row 216, under the ground


def pine(img, x, base, h, rng, far=False):
    """A pine standing with its foot at (x, base), h pixels tall."""
    Hh, Ww = img.shape
    dark, mid, lit, snow = (1, 2, 3, 7) if far else (2, 3, 4, 8)
    tiers = max(2, h // 6)
    for y in range(base - h, base + 1):
        t = (y - (base - h)) / max(1, h)           # 0 at the tip, 1 at the foot
        tier_t = (t * tiers) % 1.0                  # 0 at each tier's top
        half = (0.5 + 2.6 * t * 0.5 + tier_t * 2.2 * (0.4 + t)) * (h / 18.0) * 1.6
        half = max(0.5, half)
        if y >= base - 1:
            half = 0.8                              # the trunk
        for dx in range(-int(half), int(half) + 1):
            xx = (x + dx) % Ww
            if not 0 <= y < Hh:
                continue
            c = mid
            if dx < -half * 0.35:
                c = lit
            elif dx > half * 0.3:
                c = dark
            if tier_t < 0.28 and dx <= 0 and y < base - 2 and rng.random() < 0.8:
                c = snow                            # snow on the tier's top
            img[y, xx] = c


def cabin(img, x, base):
    """A log cabin with a snowy roof and a lit window."""
    w, h = 18, 10
    for y in range(base - h, base + 1):
        for dx in range(w):
            img[y, (x + dx) % W] = 12 if dx < 2 or y == base else 13
    for k in range(7):                               # roof
        y = base - h - 1 - k
        for dx in range(-2 + k, w + 2 - k):
            img[y, (x + dx) % W] = 9 if k < 2 or dx < w // 2 else 8
    for y in range(base - 6, base - 2):
        for dx in (5, 6, 7, 11, 12, 13):
            img[y, (x + dx) % W] = 10
    for y in range(base - h - 9, base - h - 3):      # chimney
        img[y, (x + 14) % W] = 12
        img[y, (x + 15) % W] = 13


def mast(img, x, base, h):
    """A lattice radio mast with a beacon on top."""
    for y in range(base - h, base + 1):
        t = (y - (base - h)) / h
        half = int(1 + t * 3)
        img[y, (x - half) % W] = 12
        img[y, (x + half) % W] = 12
        if (y - base) % 4 == 0:
            for dx in range(-half, half + 1):
                img[y, (x + dx) % W] = 13
    img[base - h - 1, x] = pal.MID_BEACON
    img[base - h - 2, x] = pal.MID_BEACON


def paint(seed=11):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    d8 = bayer(H, W, 8)

    # Two rows of hills: a far one in blue shadow, a near one in snow.
    for k, (base, amp, cols) in enumerate([(34, 8, (1, 5, 6)), (52, 7, (1, 5, 6, 7, 8))]):
        top = base + wave(W, [(3, amp), (5, amp * 0.6), (11, amp * 0.25), (23, 1.2)], seed + k)
        slope = np.gradient(top)
        below = yy - top[None, :]
        m = below >= 0
        # Near the crest the snow follows the hill's shape; lower down it is
        # a plain fade by screen height, so those tiles repeat.
        near = (0.95 - slope[None, :] * 0.7 - below / 18.0 + (d8 - 0.5) * 0.3)
        deep = 0.62 - (yy - base) / 70.0 + (d8 - 0.5) * 0.3
        v = np.where(below < 10, np.maximum(near, deep), deep)
        idx = np.clip(np.round(v * (len(cols) - 1)), 0, len(cols) - 1).astype(int)
        img[m] = np.array(cols)[idx][m]
        crest = m & ~np.roll(m, 1, axis=0)
        img[crest] = cols[-1] if k else 7
        # Forest along this row of hills.
        x = 0
        while x < W:
            if rng.random() < (0.7 if k else 0.6):
                n = int(rng.integers(6, 22))
                px = x
                for j in range(n):
                    px += int(rng.integers(3, 7))
                    edge = min(j, n - 1 - j)                     # taller in the middle of a stand
                    h = int(rng.integers(7, 12) if k == 0 else rng.integers(12, 20)) + min(edge, 4) * (1 if k == 0 else 2)
                    pine(img, px % W, int(top[px % W]) + 4, h, rng, far=(k == 0))
                x = px + int(rng.integers(16, 50))
            else:
                x += int(rng.integers(30, 80))
        if k == 1:
            for cx in (180, 610, 890):
                cabin(img, cx, int(top[cx + 9]) + 2)
            mast(img, 420, int(top[420]) + 2, 34)
            mast(img, 760, int(top[760]) + 2, 26)
    return img
