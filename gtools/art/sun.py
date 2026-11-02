"""Stage 9, CORONA: low over the surface of the Sun.

Ground (plane 0, palette SUN): granulation, the boiling cells of the
photosphere, each cell in one of the rotating entries 2-4 so the surface
churns as the palette turns; dark sunspots with filamented penumbrae, and
bright faculae around them.

Sky (plane 1, palette FLARE): solar flares, loops and tongues of plasma
lying over the surface. They are drawn in two groups, A in entries 5-7
and B in 8-10, which the game keeps clear most of the time and lights in
turn (bg.c): a flicker of warning, then the eruption, which is fatal to
fly through. Shots and bullets pass through them. Their tile ids say
which group they belong to: A from FLARE_A, B from FLARE_B.
"""

import math

import numpy as np

from kit import BAYER4, value_noise
from orbit import TileSet
from tiles import COLS, LOOP_ROWS, T, _torus_noise

SUN = [
    (46, 6, 0),                                                         # 0 umbra (opaque)
    (96, 22, 0),                                                        # 1 umbra rim
    (188, 74, 4), (204, 92, 10), (222, 114, 22),                       # 2-4 granules (rotate: boil)
    (150, 48, 0),                                                       # 5 lanes between cells
    (112, 32, 0), (150, 58, 2),                                         # 6-7 penumbra
    (255, 222, 120), (255, 248, 210),                                   # 8-9 faculae
    None, None, None,                                                   # 10-12
    None, None,                                                         # 13-14 (no lamps)
    (255, 206, 88),                                                     # 15 penumbra filaments
]
UMBRA, UMBRA_RIM, LANE, PEN, PEN_HI, FAC, FAC_HI, FIL = 0, 1, 5, 6, 7, 8, 9, 15
GRAN = [2, 3, 4]

# The flare entries start clear; bg.c sets them as the flares go.
FLARE = [
    None, (60, 10, 0),                                                  # 0 clear, 1 outline
    None, None, None,                                                   # 2-4
    None, None, None,                                                   # 5-7 group A (bg.c)
    None, None, None,                                                   # 8-10 group B (bg.c)
    None, None, None, None, None,
]
GROUP = {"A": [5, 6, 7], "B": [8, 9, 10]}
# How the flares look, group A erupting and B dormant, for previews.
FLARE_VIEW = list(FLARE)
FLARE_VIEW[5:8] = [(230, 50, 10), (255, 190, 60), (255, 250, 210)]
FLARE_VIEW[8:11] = [(120, 30, 0), (136, 36, 0), (150, 44, 0)]


# ---- ground ----------------------------------------------------------------

MACRO = 4  # the granulation repeats every 4 x 4 tiles, so 16-row loops match


def granulation():
    """Granules: a seamless Voronoi tiling of a 4 x 4 tile block, each cell
    one of the rotating shades, dark lanes between them. Returns its tiles,
    row by row."""
    size = MACRO * T
    rng = np.random.default_rng(1500)
    pts = rng.random((60, 2)) * size
    yy, xx = np.mgrid[0:size, 0:size]
    best = np.full((size, size), 1e9)
    second = np.full((size, size), 1e9)
    cell = np.zeros((size, size), dtype=int)
    for i, (px, py) in enumerate(pts):
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                d = np.hypot(xx + 0.5 - px - ox, yy + 0.5 - py - oy)
                closer = d < best
                second = np.where(closer, best, np.minimum(second, d))
                cell = np.where(closer, i, cell)
                best = np.minimum(best, d)
    t = np.array(GRAN)[cell % 3].astype(np.uint8)
    t[(second - best) < 1.3] = LANE
    return [t[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(MACRO) for x in range(MACRO)]


def sunspot(size, seed):
    """A sunspot size tiles across in the middle of a 4 x 4 block: a dark
    umbra, a penumbra of radial filaments, faculae flecked round it, over
    the granulation."""
    n = MACRO * T
    g = granulation()
    base = np.concatenate([np.concatenate(g[y * MACRO:(y + 1) * MACRO], axis=1) for y in range(MACRO)], axis=0)
    yy, xx = np.mgrid[0:n, 0:n]
    c = n / 2 - 0.5
    a = np.arctan2(yy - c, xx - c)
    wob = value_noise(n, n, 4, 1600 + seed) - 0.5
    d = np.hypot(xx - c, yy - c) / (size * T / 2 - 1) + wob * 0.25
    bay = BAYER4[yy % 4, xx % 4] + 0.5
    t = base.copy()
    fac = (d > 0.95) & (d < 1.3) & (value_noise(n, n, 3, 1700 + seed) > 0.55)
    t[fac] = FAC
    t[fac & (bay < 0.3)] = FAC_HI
    pen = d < 0.95
    stripes = np.cos(a * (10 + 2 * size) + wob * 6) > 0.1
    t[pen] = PEN
    t[pen & stripes] = PEN_HI
    t[pen & stripes & (d > 0.7) & (bay < 0.4)] = FIL
    t[d < 0.5] = UMBRA_RIM
    t[d < 0.4] = UMBRA
    return [t[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(MACRO) for x in range(MACRO)]


def ground_map(rows, seed=9):
    """Stage order, bottom row first: granulation, and sunspots on its
    4 x 4 grid."""
    rng = np.random.default_rng(seed)
    ts = TileSet()
    g = granulation()
    gid = [ts.add(("gran", k), lambda t=t: t) for k, t in enumerate(g)]
    m = np.array([[gid[(MACRO - 1 - r % MACRO) * MACRO + c % MACRO] for c in range(COLS)] for r in range(rows)],
                 dtype=np.uint8)
    spots = [sunspot(2.6, 0), sunspot(2.0, 1), sunspot(1.6, 2)]
    spot_ids = [[ts.add(("spot", k, i), lambda t=t: t) for i, t in enumerate(sp)] for k, sp in enumerate(spots)]
    r = 6
    while r < rows - 6:
        k = int(rng.choice(3, p=[0.3, 0.35, 0.35]))
        c = int(rng.integers(0, COLS // MACRO)) * MACRO
        for y in range(MACRO):
            for x in range(MACRO):
                m[r + MACRO - 1 - y, c + x] = spot_ids[k][y * MACRO + x]
        r += MACRO * int(rng.integers(2, 6))
    return ts, m


def stage9_ground(total_rows=208):
    body_rows = total_rows - 2 * LOOP_ROWS
    ts, body = ground_map(body_rows)
    rng = np.random.default_rng(99)
    # The loop picks up the granulation where the body left off.
    loop = np.array([[ts.ids[("gran", (MACRO - 1 - (body_rows + r) % MACRO) * MACRO + c % MACRO)]
                      for c in range(COLS)] for r in range(LOOP_ROWS)], dtype=np.uint8)
    stage = np.concatenate([body, loop, loop], axis=0)
    assert len(ts.tiles) <= 256
    return ts.tiles, stage[::-1].copy()


# ---- sky: the flares ---------------------------------------------------------

def _shade(f, group, bay):
    """Plasma by strength f (0-1): the group's three entries, dithered."""
    e = GROUP[group]
    lvl = np.clip(np.floor(f * 3 + (bay - 0.5) * 0.6), 0, 2).astype(int)
    return np.array(e)[lvl]


def loop(w, h, seed, group):
    """A prominence loop, an arch of plasma w x h tiles, its feet at the
    bottom."""
    W, H = w * T, h * T
    yy, xx = np.mgrid[0:H, 0:W]
    bay = BAYER4[yy % 4, xx % 4] + 0.5
    n = value_noise(W, H, 3, 1800 + seed)
    cx, rx, ry = W / 2 - 0.5, W / 2 - 4, H - 4
    # Distance from an elliptical arch with its ends at the bottom edge.
    d = np.abs(np.hypot((xx - cx) / rx, (yy - H + 1) / ry) - 1) * min(rx, ry) + (n - 0.5) * 3
    thick = 3.2 + 1.5 * np.sin(np.arctan2(H - 1 - yy, xx - cx) * 3 + seed)
    body = d < thick
    f = np.clip(1 - d / thick, 0, 1) + (n - 0.5) * 0.4
    img = np.zeros((H, W), dtype=np.uint8)
    img[body] = _shade(f, group, bay)[body]
    return img


def tongue(w, h, seed, group):
    """A flare tongue, licking up the screen from its root, w x h tiles."""
    W, H = w * T, h * T
    yy, xx = np.mgrid[0:H, 0:W]
    bay = BAYER4[yy % 4, xx % 4] + 0.5
    n = value_noise(W, H, 4, 1900 + seed)
    t = (H - 1 - yy) / (H - 1)                       # 0 at the root, 1 at the tip
    cx = W / 2 - 0.5 + np.sin(t * math.pi * 2 + seed) * W * 0.22
    half = (W / 2 - 2) * (1 - t ** 1.5) + 1
    d = np.abs(xx - cx) / half + (n - 0.5) * 0.5
    body = d < 1
    f = np.clip(1 - d, 0, 1) * 0.85 + (1 - t) * 0.25 + (n - 0.5) * 0.3
    img = np.zeros((H, W), dtype=np.uint8)
    img[body] = _shade(f, group, bay)[body]
    return img


# (kind, w, h) in tiles
SHAPES = [("loop", 3, 2), ("loop", 4, 3), ("tongue", 2, 3), ("tongue", 2, 4)]


def stage9_sky(rows, intro_rows=18, tail_rows=17, seed=9):
    """Flares in both groups, laid out so each group alone always leaves a
    way through. Returns tiles, the map (top row first), and the first tile
    id of each group."""
    rng = np.random.default_rng(seed)
    tiles = [np.zeros((T, T), dtype=np.uint8)]
    first, tmpl = {}, {}
    for group in ("A", "B"):
        first[group] = len(tiles)
        for k, (kind, w, h) in enumerate(SHAPES):
            img = (loop if kind == "loop" else tongue)(w, h, k, group)
            ids = np.zeros((h, w), dtype=int)
            for r in range(h):
                for c in range(w):
                    t = img[r * T:(r + 1) * T, c * T:(c + 1) * T]
                    if t.any():
                        ids[r, c] = len(tiles)
                        tiles.append(t.copy())
            tmpl[group, k] = ids
    sky = np.zeros((rows, COLS), dtype=np.uint8)
    used = {g: np.zeros((rows, COLS), dtype=bool) for g in "AB"}
    any_used = np.zeros((rows, COLS), dtype=bool)
    end = rows - tail_rows

    def passable(g, r0, h):
        for r in range(r0, r0 + h):
            run = best = 0
            for c in range(COLS):
                run = 0 if used[g][r, c] else run + 1
                best = max(best, run)
            if best < 5:
                return False
        return True

    r = intro_rows
    while r < end - 5:
        g = "AB"[int(rng.integers(0, 2))]
        k = int(rng.integers(0, len(SHAPES)))
        ids = tmpl[g, k]
        h, w = ids.shape
        for _ in range(8):
            c = int(rng.integers(0, COLS - w + 1))
            if any_used[max(r - 1, 0):r + h + 1, max(c - 1, 0):c + w + 1].any():
                continue
            used[g][r:r + h, c:c + w] = True
            if not passable(g, r, h):
                used[g][r:r + h, c:c + w] = False
                continue
            any_used[r:r + h, c:c + w] = True
            for y in range(h):
                for x in range(w):
                    if ids[y, x]:
                        sky[r + h - 1 - y, c + x] = ids[y, x]
            break
        r += int(rng.integers(1, 4))
    sky[end:, :] = 0
    assert len(tiles) <= 256
    return tiles, sky[::-1].copy(), first["A"], first["B"]
