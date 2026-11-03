"""Level 2: the boreal forest and its lakes, under the aurora.

Three painters, one per layer, the same sizes as level 1's (far.py,
mid.py, fg.py), so the world's layout is the same: prisons, border and
home base stand where they do in level 1. The colors are pal.B_FAR,
pal.B_MID and pal.B_FG, whose indices have the same jobs as level 1's
(the foreground's "steel" is timber here, so the prisons and the home
base are log built).
"""

from __future__ import annotations

import math

import numpy as np

from . import far, fg, mid
from .paint import bayer, fbm, wave

# --- Plane 0: aurora over forested ridges -----------------------------------

CURTAINS = [(74, 18, 58, (2, 3)), (44, 12, 34, (3, 4)), (100, 7, 22, (5, 7))]


def spruce_line(W, base, seed, lo=2, hi=7):
    """A treeline's top edge: rows of little spruce points along `base`."""
    rng = np.random.default_rng(seed)
    top = np.array(base, float)
    x = 0
    while x < W:
        w = int(rng.integers(3, 7))
        h = rng.uniform(lo, hi)
        for dx in range(w):
            t = 1 - abs(dx - (w - 1) / 2) / (w / 2)
            top[(x + dx) % W] -= h * t
        x += w - 1
    return top


def far_paint(seed=31):
    W, H = far.W, far.H
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    d8 = bayer(H, W, 8)
    far.sky(img, yy, d8)
    far.aurora(img, yy, xx, d8, seed, CURTAINS)

    # Two forested ridges, the far one higher and lit along its edge by
    # the aurora, the near one dark.
    ridge = np.full(W, H)
    for k, (base, amp, col, rim) in enumerate([(124, 9, 14, 15), (144, 6, 13, 14)]):
        line = spruce_line(W, base + wave(W, [(2, amp), (5, amp * 0.5), (9, 2)], seed + 50 + k), seed + 60 + k,
                           *((2, 5) if k == 0 else (3, 8)))
        inside = yy >= line[None, :]
        img[inside] = col
        edge = inside & ~np.roll(inside, 1, axis=0)
        img[edge] = rim
        if k == 0:
            # Faint light on the far ridge's upper slopes.
            glow = inside & (yy - line[None, :] < 5) & (d8 < 0.35)
            img[glow] = rim
        ridge = np.minimum(ridge, line.astype(int))
    far.stars(img, rng, ridge, n=170, top=110)
    return img


# --- Plane 1: the lake and the far shore -----------------------------------

SHORE = 48        # image row of the far shore's waterline (screen row 168)


def cabin(img, x, base):
    """A log cabin with a snowy roof and two lit windows."""
    W = img.shape[1]
    w, h = 16, 8
    for y in range(base - h, base + 1):
        for dx in range(w):
            img[y, (x + dx) % W] = 5 if (y - base) % 2 else 6
    for k in range(6):                                 # roof
        y = base - h - 1 - k
        for dx in range(-2 + k, w + 2 - k):
            img[y, (x + dx) % W] = 9 if dx < w // 2 else 8
    for y in range(base - 5, base - 2):
        for dx in (3, 4, 10, 11):
            img[y, (x + dx) % W] = 10


def lookout(img, x, base, h):
    """A fire lookout: a lattice tower with a cab on top and a beacon."""
    W = img.shape[1]
    for y in range(base - h, base + 1):
        t = (y - (base - h)) / h
        half = int(1 + t * 4)
        img[y, (x - half) % W] = 1
        img[y, (x + half) % W] = 1
        if (y - base) % 5 == 0:
            for dx in range(-half, half + 1):
                img[y, (x + dx) % W] = 6
    cab = base - h
    for y in range(cab - 6, cab):
        for dx in range(-4, 5):
            img[y, (x + dx) % W] = 6
    for dx in range(-2, 3):
        img[cab - 4, (x + dx) % W] = 10
        img[cab - 3, (x + dx) % W] = 10
    for dx in range(-5, 6):
        img[cab - 7, (x + dx) % W] = 8
    img[cab - 8, x] = 1
    img[cab - 9, x] = 11
    img[cab - 10, x] = 11


def tile_x(a, width):
    """Repeat `a` (one row of values) across `width` columns."""
    return np.tile(a, width // a.shape[-1])


def mid_paint(seed=41):
    """The layer is built to repeat, so it fits its tile budget: the far
    shore every 256 pixels, the water every 64, and the points of forest
    on the near shore are one stand drawn the same way each time."""
    W, H = mid.W, mid.H
    P = 256
    img = np.zeros((H, W), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    d8 = bayer(H, W, 8)

    # The far shore: low hills, then a dense treeline down to the water.
    hill = tile_x(SHORE - 14 + wave(P, [(1, 4), (3, 2)], seed), W)
    img[yy >= hill[None, :]] = 5
    trees = tile_x(spruce_line(P, SHORE - 3 + wave(P, [(2, 2), (5, 1)], seed + 1), seed + 2, 6, 16), W)
    t = (yy >= trees[None, :]) & (yy < SHORE)
    img[t] = 2
    # The aurora lights the tops of the trees.
    top = t & ~np.roll(t, 1, axis=0)
    img[top & (d8 < 0.7)] = 4
    img[t & np.roll(top, 1, axis=0) & (d8 < 0.4)] = 3

    # The lake: still dark water, a shadow of the treeline along the shore,
    # thin ripples, and the aurora's light in broken streaks.
    Q = 64
    water = yy >= SHORE
    img[water] = 12
    depth = yy - SHORE
    rng = np.random.default_rng(seed + 3)
    pattern = np.full((H, Q), 12, np.uint8)
    for y in range(SHORE, H):
        dy = y - SHORE
        if dy < 3:
            pattern[y, :] = 1                              # the treeline's shadow
            continue
        if dy < 6:
            pattern[y, :] = np.where(rng.random(Q) < 0.5 - dy * 0.06, 1, 12)
            continue
        if dy % 3 == 0:                                   # ripples
            for _ in range(2):
                x0, n = int(rng.integers(0, Q)), int(rng.integers(4, 12))
                pattern[y, [(x0 + k) % Q for k in range(n)]] = 13
        if 8 <= dy < 40 and dy % 2 == 1:                  # the aurora, in streaks
            for cx, w in ((14, 6), (44, 9)):
                if rng.random() < 0.75:
                    n = int(rng.integers(2, w))
                    x0 = cx + int(rng.integers(-3, 4))
                    c = 15 if (dy > 14 and dy < 26 and n > 4) else 14
                    pattern[y, [(x0 + k) % Q for k in range(n)]] = c
    img[water] = np.tile(pattern, W // Q)[water]

    # Cabins and a fire lookout along the far shore, their lights in the water.
    for cx in (140, 470, 820):
        cabin(img, cx, SHORE - 1)
        for dx in (3, 10):
            for y in range(SHORE + 2, SHORE + 14, 2):
                img[y, (cx + dx) % W] = 10
                img[y, (cx + dx + 1) % W] = 10 if y < SHORE + 8 else 13
    lookout(img, 640, SHORE - 2, 30)

    # Points of forest on the near shore, between the stretches of water:
    # one stand, drawn the same way each time, on the same water.
    for px in (0, 384, 704):
        rng = np.random.default_rng(seed + 9)
        x = px
        n = 7
        for j in range(n):
            x += int(rng.integers(6, 10))
            edge = min(j, n - 1 - j)
            h = int(rng.integers(20, 28)) + min(edge, 3) * 4
            mid.pine(img, x % W, 92, h, rng)
        for dx in range(px, px + 72):
            for y in range(84, 96):
                if img[y, dx % W] in (12, 13, 14, 15, 1, 10):
                    img[y, dx % W] = 7 if y > 86 or (dx + y) % 3 else 8
    return img


# --- Plane 2: the forest floor ---------------------------------------------

STANDS = [
    [(14, 58), (30, 76), (46, 54), (62, 68), (80, 46)],
    [(24, 66), (42, 84), (60, 58)],
    [(44, 72), (62, 52)],
]


def stand(c, x0, k):
    rng = np.random.default_rng(200 + k)
    for dx, h in STANDS[k]:
        fg.pine(c, x0 + dx, h, rng)


def pond(c, x0, w):
    """A frozen pond: smooth ice with glints and the aurora's green in it,
    banked with snow at either end."""
    S = fg.SURF
    for x in range(x0, x0 + w):
        for y in range(S - 1, S + 7):
            c.px(x, y, 3 if y > S + 2 else 4)
        c.px(x, S - 1, 5 if (x // 2) % 3 else 6)
    for k, (dx, y, n) in enumerate(((8, S + 1, 18), (40, S + 3, 26), (70, S + 1, 12), (24, S + 4, 10))):
        for x in range(x0 + dx, min(x0 + w - 4, x0 + dx + n)):
            c.px(x, y, 12 if k % 2 else 6)
    for x in range(x0 + 4, x0 + w - 4, 9):
        c.px(x, S + 2, 5)
    fg.drift(c, x0 - 10, 20, 4)
    fg.drift(c, x0 + w - 10, 20, 4)


def woodpile(c, x0):
    """Cut logs stacked under a little snow: their ends show as rings."""
    S = fg.SURF
    for row, n in ((0, 4), (1, 3), (2, 2)):
        for k in range(n):
            cx = x0 + k * 7 + row * 3 + 3
            cy = S - 3 - row * 6
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    r = dx * dx + dy * dy
                    if r <= 10:
                        c.px(cx + dx, cy + dy, 1 if r > 6 else (10 if r > 2 else 9))
            c.px(cx, cy, 8)
    c.snowcap(x0 + 6, x0 + 18, S - 18, thick=3)


def stump(c, x, rng):
    """A cut stump with snow on it."""
    S = fg.SURF
    c.box(x, S - 9, x + 10, S + 1, 8, light=9, dark=7)
    c.rect(x + 1, S - 9, x + 9, S - 8, 10)
    c.snowcap(x, x + 10, S - 9, thick=3)


def fg_paint(seed=23):
    rng = np.random.default_rng(seed)
    c = fg.Canvas(fg.W, fg.H)
    fg.ground(c, seed)
    busy = []
    for col in fg.COMPOUND_COLS:
        fg.compound(c, col, np.random.default_rng(seed + 5))
        busy.append((col * fg.T - 24, (col + fg.COMPOUND_W) * fg.T + 24))
    fg.helipad(c)
    fg.flagpole(c)
    fg.checkpoint(c)
    busy.append((fg.BORDER_X - 50, fg.BORDER_X + 70))
    fg.hangar(c, rng)
    busy.append((fg.HANGAR_COL * fg.T - 40, fg.W))

    def free(x0, x1):
        return all(x1 < a or x0 > b for a, b in busy)

    # One prop per 128-pixel slot, always drawn the same way in its slot,
    # as in level 1: thick spruce, frozen ponds, woodpiles and stumps.
    for x0 in range(64, fg.HANGAR_COL * fg.T - 160, fg.SLOT):
        if not free(x0 - 8, x0 + fg.SLOT + 8):
            continue
        r = rng.random()
        if r < 0.55:
            stand(c, x0, int(rng.integers(0, len(STANDS))))
        elif r < 0.75:
            pond(c, x0 + 16, 96)
        elif r < 0.87:
            woodpile(c, x0 + 52)
        else:
            stump(c, x0 + 58, rng)

    # The breached door, as in level 1.
    b = fg.Canvas(fg.W, fg.H)
    b.a[:] = c.a
    col = fg.COMPOUND_COLS[0]
    fg.bunker(b, col * fg.T, np.random.default_rng(seed + 5), breached=True)
    x0 = (col + fg.DOOR_COL) * fg.T
    S = fg.SURF
    door_open = b.a[S - fg.DOOR_H * fg.T:S, x0:x0 + fg.DOOR_W * fg.T].copy()
    above = b.a[S - (fg.DOOR_H + 1) * fg.T:S - fg.DOOR_H * fg.T, x0:x0 + fg.DOOR_W * fg.T].copy()
    return c.a, np.vstack([above, door_open])
