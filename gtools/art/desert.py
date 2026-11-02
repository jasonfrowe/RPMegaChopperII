"""Stage 4, SCORCHED SANDS: desert dunes, rock plateaus, oases and a
railway, with a sandstorm drifting over it.

Ground (plane 0, palette SAND): rippled dunes; plateaus and oases cut by
marching squares; a railway running up the map on columns RAIL..RAIL+1,
which the armoured trains drive along. Turrets sit in bunkers on the
plateaus. Entries 2-4 rotate, so the oases shimmer.

Sky (plane 1, palette DUST): drifting banks of sand haze, scenery only.
The trains' art (stage-specific enemies) is in this stage's file too.
"""

import math

import numpy as np

import city
from kit import Material, Sprite, value_noise
from tiles import COLS, LOOP_ROWS, T

SAND = [
    (60, 34, 16),                                                       # 0 backdrop (opaque)
    (40, 110, 120), (60, 150, 150), (120, 200, 190),                    # 1-3 oasis water (2-3 rotate)
    (150, 200, 170),                                                    # 4 water glint (rotates)
    (120, 74, 36), (164, 108, 54), (200, 146, 78), (228, 182, 108), (246, 216, 150),  # 5-9 sand
    (70, 40, 22),                                                       # 10 shadow
    (96, 64, 52), (138, 98, 78),                                        # 11-12 rock
    (255, 60, 50), (120, 255, 160),                                     # 13-14 lamps (blink)
    (70, 120, 50),                                                      # 15 palm green
]
WATER = [1, 2, 3, 4]
DUNE = [5, 6, 7, 8, 9]
SHADOW, ROCK0, ROCK1, LAMP_R, LAMP_G, PALM = 10, 11, 12, 13, 14, 15

# Clouds of sand: the cloud tiles draw with entries 12 and 15.
DUST = [None] * 16
DUST[12] = (184, 132, 82)
DUST[15] = (226, 186, 128)

RAIL = 8  # the railway's left column; the track runs down its middle


def dune_tile(variant):
    """Rippled sand: wind ripples bent by noise, light on their windward side."""
    yy, xx = np.mgrid[0:T, 0:T]
    n = value_noise(T, T, 8, 1500 + variant)
    wave = np.sin((yy * 0.9 + xx * 0.25 + n * 6 + variant * 2.1))
    t = np.full((T, T), DUNE[2], dtype=np.uint8)
    t[wave > 0.55] = DUNE[3]
    t[wave > 0.85] = DUNE[4]
    t[wave < -0.6] = DUNE[1]
    t[(wave < -0.9)] = DUNE[0]
    return t


def _rock(seed):
    n = value_noise(T, T, 4, 1600 + seed)
    t = np.full((T, T), ROCK1, dtype=np.uint8)
    t[n < 0.42] = ROCK0
    t[n < 0.2] = SHADOW
    t[n > 0.75] = DUNE[1]
    return t


def _water(seed):
    n = value_noise(T, T, 4, 1700 + seed)
    t = np.full((T, T), WATER[0], dtype=np.uint8)
    t[n > 0.45] = WATER[1]
    t[n > 0.7] = WATER[2]
    t[n > 0.86] = WATER[3]
    return t


def _blend(c, inner, outer, rim, rim2, variant):
    """Marching squares: inner where the corners say so, a rim between."""
    tl, tr, br, bl = c
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T
    f = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v
    f = f + (value_noise(T, T, 4, 1800 + variant) - 0.5) * 0.15
    t = outer.copy()
    t[f >= 0.55] = inner[f >= 0.55]
    t[(f >= 0.48) & (f < 0.55)] = rim
    t[(f >= 0.42) & (f < 0.48)] = rim2
    return t


def rail_tile(side, variant):
    """Half of the track (side 0 left, 1 right): a gravel bed, timber
    sleepers across it, and one bright steel rail."""
    n = value_noise(T, T, 2, 1900 + side)
    t = np.where(n > 0.5, ROCK0, SHADOW).astype(np.uint8)
    edge = 0 if side == 0 else T - 1
    t[:, edge] = DUNE[1]  # the bed's sandy shoulder
    for y in range(0, T, 4):
        t[y:y + 2, (1 if side == 0 else 0):(T if side == 0 else T - 1)] = DUNE[0]
    rx = 9 if side == 0 else 5
    t[:, rx:rx + 2] = DUNE[4]
    t[:, rx + 2] = SHADOW
    return t


def bunker_tiles():
    big = np.concatenate([np.concatenate([_rock(20 + y * 2 + x) for x in range(2)], axis=1) for y in range(2)], axis=0)
    yy, xx = np.mgrid[0:32, 0:32]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 13] = DUNE[1]
    big[(d < 13) & (d > 11) & (xx + yy < 31)] = DUNE[3]
    big[(d < 13) & (d > 11) & (xx + yy >= 31)] = SHADOW
    big[d < 9] = ROCK0
    big[d < 7] = SHADOW
    big[d < 2.5] = LAMP_R
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def palm_tile():
    t = dune_tile(7)
    s = Sprite(T, T)
    for a in range(0, 360, 60):
        r = math.radians(a)
        s.line((8, 8), (8 + math.cos(r) * 7, 8 + math.sin(r) * 7), "palm", width=2)
    s.ellipse((6, 6, 10, 10), "trunk", z=1)
    img = s.render({"palm": Material([PALM], shaded=False), "trunk": Material([ROCK0], shaded=False)}, outline=SHADOW)
    t[img != 0] = img[img != 0]
    return t


def ground_tileset():
    tiles, ids = [], {}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"dune{k}", dune_tile(k))
    for cfg in range(1, 16):
        c = ((cfg >> 3) & 1, (cfg >> 2) & 1, (cfg >> 1) & 1, cfg & 1)
        add(f"rock{cfg}", _blend(c, _rock(cfg), dune_tile(cfg % 4), SHADOW, DUNE[1], cfg))
        add(f"oasis{cfg}", _blend(c, _water(cfg), dune_tile(cfg % 4), DUNE[4], PALM, cfg + 20))
    for side in range(2):
        add(f"rail{side}", rail_tile(side, side))
    for k, t in enumerate(bunker_tiles()):
        add(f"bunker{k}", t)
    add("palm", palm_tile())
    return tiles, ids


def ground_map(rows, ids, seed=4):
    """Stage order. Returns map, bunkers (row, col), and the rows with track."""
    rng = np.random.default_rng(seed)
    nr = value_noise(COLS + 1, rows + 1, 5, seed) * 0.7 + value_noise(COLS + 1, rows + 1, 2, seed + 1) * 0.3
    nw = value_noise(COLS + 1, rows + 1, 7, seed + 5)
    rock = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    water = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    for r in range(rows + 1):
        t = r / rows
        on = 0.06 < t < 0.92
        for c in range(COLS + 1):
            near_rail = RAIL - 1 <= c <= RAIL + 3
            if on and not near_rail:
                rock[r, c] = nr[r, c] > 0.62
                # Pools keep to the west, thinning out toward the railway.
                water[r, c] = (not rock[r, c]) and nw[r, c] > 0.68 + max(0, c - 2) * 0.07
    m = np.zeros((rows, COLS), dtype=np.uint8)
    for r in range(rows):
        for c in range(COLS):
            def cfg(g):
                return (g[r + 1, c] << 3) | (g[r + 1, c + 1] << 2) | (g[r, c + 1] << 1) | g[r, c]
            kr, kw = cfg(rock), cfg(water)
            if kr:
                m[r, c] = ids[f"rock{kr}"]
            elif kw:
                m[r, c] = ids[f"oasis{kw}"]
            else:
                m[r, c] = ids[f"dune{int(rng.integers(0, 4))}"]
                if rng.random() < 0.03 and c < RAIL - 1:
                    m[r, c] = ids["palm"]
        m[r, RAIL], m[r, RAIL + 1] = ids["rail0"], ids["rail1"]
    bunkers = []
    used = np.zeros((rows, COLS), dtype=bool)
    full = ids["rock15"]
    for r in range(1, rows - 1):
        for c in range(COLS - 1):
            if all(m[r + dy, c + dx] == full for dy in (0, 1) for dx in (0, 1)) and not used[r:r + 2, c:c + 2].any() \
                    and rng.random() < 0.3:
                m[r + 1, c], m[r + 1, c + 1] = ids["bunker0"], ids["bunker1"]
                m[r, c], m[r, c + 1] = ids["bunker2"], ids["bunker3"]
                used[max(0, r - 3):r + 5, max(0, c - 3):c + 5] = True
                bunkers.append((r, c))
    return m, bunkers


def stage4_ground(total_rows=208):
    tiles, ids = ground_tileset()
    body_rows = total_rows - 2 * LOOP_ROWS
    body, bunkers = ground_map(body_rows, ids)
    rng = np.random.default_rng(44)
    loop = np.array([[ids[f"dune{int(rng.integers(0, 4))}"] for _ in range(COLS)] for _ in range(LOOP_ROWS)],
                    dtype=np.uint8)
    loop[:, RAIL], loop[:, RAIL + 1] = ids["rail0"], ids["rail1"]
    stage = np.concatenate([body, loop, loop], axis=0)
    return tiles, stage[::-1].copy(), bunkers


def stage4_sky(rows, seed=31):
    """Sand haze: wide, thin banks drifting over, empty for the last screen."""
    tiles = [np.zeros((T, T), dtype=np.uint8)]
    ids = {}
    for cfg in range(1, 16):
        c = ((cfg >> 3) & 1, (cfg >> 2) & 1, (cfg >> 1) & 1, cfg & 1)
        ids[f"cloud{cfg}"] = len(tiles)
        tiles.append(city.cloud_tile(c, cfg + 60))
    ids["cloud15b"] = len(tiles)
    tiles.append(city.cloud_tile((1, 1, 1, 1), 97))
    rng = np.random.default_rng(seed)
    corners = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    end = rows - 17
    r = 12
    while r < end - 4:
        cw, ch = int(rng.integers(5, 10)), int(rng.integers(1, 3))
        cc = int(rng.integers(-2, COLS - cw + 2))
        city._place_cloud(corners, r, max(0, cc), cw, ch, rng)
        r += ch + int(rng.integers(4, 10))
    sky = np.zeros((rows, COLS), dtype=np.uint8)
    for y in range(rows):
        for x in range(COLS):
            tl, tr = corners[y + 1, x], corners[y + 1, x + 1]
            bl, br = corners[y, x], corners[y, x + 1]
            cfg = (tl << 3) | (tr << 2) | (br << 1) | bl
            if cfg == 15 and (x + y) % 3 == 0:
                sky[y, x] = ids["cloud15b"]
            elif cfg:
                sky[y, x] = ids[f"cloud{cfg}"]
    sky[end:, :] = 0
    # Haze, not cloud: every other pixel clear, so the desert shows through.
    yy, xx = np.mgrid[0:T, 0:T]
    for t in tiles:
        t[((xx + yy) & 1) == 1] = 0
    return tiles, sky[::-1].copy()


TRAIN_MATS = {
    "metal": Material([2, 3, 4, 5]),
    "paint": Material([6, 7, 8, 9]),
    "glow": Material([10, 11], shaded=False),
    "dark": Material([14], shaded=False),
    "canopy": Material([12, 13], dither=0.0),
}


def train():
    """32x32 armoured train cars on the rails, heading up the screen, in
    the enemy palettes (paint carries the chain color). Frames: the
    locomotive, then a gun car."""
    out = []
    for loco in (True, False):
        s = Sprite(32, 32)
        # Wheels and bogies under the body.
        for y in (4, 22):
            s.rect((8, y, 24, y + 6), "dark", z=0.4, amp=0.4, bevel=1)
        s.rect((9, 1 if loco else 2, 23, 31), "metal", z=1, amp=2.0, bevel=2.5)
        if loco:
            s.poly([(9, 8), (16, 0), (23, 8)], "metal", z=1, amp=1.5, bevel=1.5)
            s.rect((11, 12, 21, 20), "paint", z=2.5, amp=1.2, bevel=1.5)
            s.rect((12.5, 13, 19.5, 15), "canopy", z=3.5, amp=0.4, profile="flat")
            s.rect((13, 22, 19, 29), "dark", z=2.5, amp=0.5, profile="flat")
            s.dot(14, 3, "glow", z=3)
            s.dot(17, 3, "glow", z=3)
        else:
            s.rect((11, 4, 21, 28), "paint", z=2.2, amp=1.0, bevel=1.5)
            s.ellipse((11, 10, 21, 20), "metal", z=3, amp=1.5)
            s.line((16, 15), (16, 4), "dark", width=3, z=4)
            s.line((16, 15), (16, 4), "metal", width=1, z=4.5)
            s.dot(15, 14, "glow", z=5)
        out.append(s.render(TRAIN_MATS, gloss=0.3))
    return out
