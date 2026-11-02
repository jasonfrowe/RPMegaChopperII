"""Stage 5, FROZEN STRAIT: pack ice over a black sea, with icebergs towering
out of it and snow blowing across.

Ground (plane 0, palette ICE): stretches of solid ice shelf, cut by plowed
roads (tanks drive along them) and dotted with bunkers (turrets), and
stretches of open water with floes drifting in it (icebreaker gunboats).
Floes and shelf edges are cut by marching squares. Entries 2-4 rotate, so
the water ripples. The map's top loops over the shelf, for the crawler.

Sky (plane 1, palette FROST): icebergs, much nearer than the sea, so they
scroll past faster. A berg's top is solid where three or more of a tile's
corners are ice, and the ship crashes into it; its south face is a dark
cliff. Drifts of blowing snow between them are only scenery.
"""

import numpy as np

from kit import value_noise
from tiles import COLS, LOOP_ROWS, T, _torus_noise

ICE = [
    (2, 8, 20),                                                         # 0 backdrop (opaque)
    (6, 20, 44),                                                        # 1 deep water
    (12, 32, 64), (16, 40, 76), (20, 48, 88),                           # 2-4 water (rotate, kept close)
    (56, 80, 118), (92, 124, 164), (132, 164, 200), (178, 204, 232), (226, 238, 252),  # 5-9 ice and snow
    (16, 26, 50),                                                       # 10 shadow
    (52, 56, 72), (92, 98, 116),                                        # 11-12 rock, concrete
    (255, 60, 60), (120, 255, 200),                                     # 13-14 lamps (blink)
    (120, 200, 236),                                                    # 15 slush, glints
]
WATER = [1, 2, 3, 4]
SNOW = [5, 6, 7, 8, 9]
SHADOW, ROCK0, ROCK1, LAMP_R, LAMP_G, GLINT = 10, 11, 12, 13, 14, 15

FROST = [
    None,                                                               # 0 clear
    (8, 16, 36),                                                        # 1 outline
    (110, 200, 255), (170, 230, 255), (230, 250, 255),                  # 2-4 crevasse glints (rotate)
    (48, 84, 136), (78, 120, 176), (122, 166, 214), (176, 210, 240), (232, 246, 255),  # 5-9 berg ice
    (4, 8, 20),                                                         # 10 shadow
    (30, 52, 96),                                                       # 11 cliff face
    (170, 190, 216),                                                    # 12 snow, shaded
    (255, 60, 60), (255, 160, 40),                                      # 13-14 (unused)
    (244, 250, 255),                                                    # 15 snow
]
BERG = [5, 6, 7, 8, 9]
OUT, SH, FACE, SNOW_D, FLAKE = 1, 10, 11, 12, 15
CREV = [2, 3, 4]


# ---- ground --------------------------------------------------------------

def snow_tile(variant):
    """Wind-packed snow: low ripples (sastrugi) bent by noise, seamless so
    it can tile at random."""
    n = _torus_noise(T, 8, 300 + variant)
    yy, xx = np.mgrid[0:T, 0:T]
    wave = np.sin(2 * np.pi * (xx * 1 + yy * 2) / T + n * 4 + variant * 1.7)
    t = np.full((T, T), SNOW[2], dtype=np.uint8)
    t[wave > 0.7] = SNOW[3]
    t[(wave > 0.93) & (n > 0.5)] = SNOW[4]
    t[(wave < -0.85) & ((xx + yy) % 2 == 0)] = SNOW[1]
    if variant == 3:
        # A crack across the ice.
        for x in range(T):
            y = int(7 + 3 * np.sin(x * 0.6))
            t[y, x] = SNOW[0]
            t[min(T - 1, y + 1), x] = SNOW[3]
    return t


def water_tile(variant):
    n = _torus_noise(T, 4, 340 + variant) * 0.6 + _torus_noise(T, 8, 360 + variant) * 0.4
    yy, xx = np.mgrid[0:T, 0:T]
    band = (np.sin((xx * 0.3 + yy * 0.9 + variant * 2.5) * 0.8) + 1) / 2
    v = n * 0.7 + band * 0.3
    t = np.full((T, T), WATER[0], dtype=np.uint8)
    t[v > 0.42] = WATER[1]
    t[v > 0.64] = WATER[2]
    t[v > 0.82] = WATER[3]
    return t


def edge_tile(c, variant):
    """Marching squares: ice where the corners say so, a lit rim on top, a
    shadowed lip where the ice drops into the water, slush around it."""
    tl, tr, br, bl = c
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T
    f = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v
    f = f + (value_noise(T, T, 4, 380 + variant) - 0.5) * 0.14
    # Which way the ice edge faces: down the screen is south, in shadow.
    south = (bl + br) < (tl + tr)
    t = water_tile(variant % 4)
    inner = snow_tile(variant % 3)
    t[f >= 0.56] = inner[f >= 0.56]
    t[(f >= 0.50) & (f < 0.56)] = SNOW[1] if south else SNOW[4]
    t[(f >= 0.46) & (f < 0.50)] = SHADOW if south else SNOW[0]
    t[(f >= 0.40) & (f < 0.46) & ((xx + yy) % 2 == 0)] = GLINT
    return t


def road_tile(variant):
    """A plowed track across the shelf: packed snow, tread ruts, banks."""
    t = snow_tile(variant)
    n = _torus_noise(T, 4, 400 + variant)
    t[2:14, :] = np.where(n[2:14, :] > 0.5, SNOW[1], SNOW[2])
    for y in (5, 10):
        t[y, :] = SNOW[0]
        t[y, ::3] = SHADOW
    t[1, :] = SNOW[4]
    t[14, :] = SNOW[0]
    return t


def bunker_tiles():
    big = np.concatenate([np.concatenate([snow_tile(y * 2 + x) for x in range(2)], axis=1) for y in range(2)], axis=0)
    yy, xx = np.mgrid[0:32, 0:32]
    sq = np.maximum(np.abs(xx - 15.5), np.abs(yy - 15.5))
    big[sq < 14] = ROCK1
    big[(sq < 14) & (sq >= 12.5) & (xx < yy)] = ROCK0
    big[(sq < 14) & (sq >= 12.5) & (xx >= yy)] = SNOW[4]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 10] = ROCK0
    big[d < 8] = SHADOW
    big[(d < 10) & (d > 8.5) & ((xx + yy) % 4 == 0)] = SNOW[3]
    big[d < 2.5] = LAMP_R
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def beacon_tile():
    t = snow_tile(1)
    yy, xx = np.mgrid[0:T, 0:T]
    d = np.sqrt((xx - 7.5) ** 2 + (yy - 7.5) ** 2)
    t[d < 4] = ROCK0
    t[d < 2.5] = LAMP_G
    t[(d >= 4) & (d < 5)] = SHADOW
    return t


def ground_tileset():
    tiles, ids = [], {}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"water{k}", water_tile(k))
    for k in range(4):
        add(f"snow{k}", snow_tile(k))
    for cfg in range(1, 15):
        c = ((cfg >> 3) & 1, (cfg >> 2) & 1, (cfg >> 1) & 1, cfg & 1)
        add(f"edge{cfg}", edge_tile(c, cfg))
    for k in range(2):
        add(f"road{k}", road_tile(k))
    for k, t in enumerate(bunker_tiles()):
        add(f"bunker{k}", t)
    add("beacon", beacon_tile())
    return tiles, ids


# Stretches of the map, in body rows from the start: shelf (s) or floes (f).
SECTIONS = [("f", 14), ("s", 22), ("f", 26), ("s", 24), ("f", 22), ("s", 26), ("f", 24)]


def ground_map(rows, ids, seed=5):
    """Stage order. Returns the map, bunkers (row, col) and road rows."""
    rng = np.random.default_rng(seed)
    n = value_noise(COLS + 1, rows + 1, 3, seed) * 0.6 + value_noise(COLS + 1, rows + 1, 2, seed + 1) * 0.4
    kind = np.empty(rows + 1, dtype="<U1")
    r = 0
    for k, length in SECTIONS:
        kind[r:r + length] = k
        r += length
    kind[r:] = "s"  # the rest, up to the loop, is shelf
    corners = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    for r in range(rows + 1):
        for c in range(COLS + 1):
            if kind[r] == "s":
                corners[r, c] = n[r, c] > 0.18  # a few holes in the shelf
            else:
                corners[r, c] = n[r, c] > 0.62  # floes
    corners[0:3, :] = 0  # open water to begin with
    # Roads: rows of solid ice right across a shelf, eight rows apart.
    roads = []
    for r in range(rows):
        if kind[r] == "s" and kind[max(0, r - 4)] == "s" and kind[min(rows, r + 5)] == "s" and r % 8 == 4:
            corners[r - 1:r + 3, :] = 1
            roads.append(r)
    m = np.zeros((rows, COLS), dtype=np.uint8)
    for r in range(rows):
        for c in range(COLS):
            tl, tr = corners[r + 1, c], corners[r + 1, c + 1]
            bl, br = corners[r, c], corners[r, c + 1]
            cfg = (tl << 3) | (tr << 2) | (br << 1) | bl
            if cfg == 0:
                m[r, c] = ids[f"water{int(rng.integers(0, 4))}"]
            elif cfg == 15:
                m[r, c] = ids[f"snow{int(rng.choice(4, p=[0.34, 0.3, 0.3, 0.06]))}"]
                if rng.random() < 0.01:
                    m[r, c] = ids["beacon"]
            else:
                m[r, c] = ids[f"edge{cfg}"]
    for r in roads:
        m[r, :] = [ids[f"road{(c + r) % 2}"] for c in range(COLS)]
    snow = {ids[f"snow{k}"] for k in range(4)}
    bunkers = []
    used = np.zeros((rows, COLS), dtype=bool)
    for r in roads:
        used[r - 1:r + 2, :] = True
    for r in range(1, rows - 1):
        for c in range(COLS - 1):
            if all(m[r + dy, c + dx] in snow for dy in (0, 1) for dx in (0, 1)) and not used[r:r + 2, c:c + 2].any() \
                    and rng.random() < 0.11:
                m[r + 1, c], m[r + 1, c + 1] = ids["bunker0"], ids["bunker1"]
                m[r, c], m[r, c + 1] = ids["bunker2"], ids["bunker3"]
                used[max(0, r - 3):r + 5, max(0, c - 3):c + 5] = True
                bunkers.append((r, c))
    # Open water wide enough for an icebreaker: three clear columns, four rows.
    water_ids = {ids[f"water{k}"] for k in range(4)}
    water = []
    r = 0
    while r < rows - 4:
        spots = [c for c in range(1, COLS - 2) if all(m[r + dy, c + dx] in water_ids
                                                       for dy in range(4) for dx in range(-1, 2))]
        if spots:
            water.append((r + 2, spots[int(rng.integers(0, len(spots)))]))
            r += 7
        else:
            r += 1
    return m, bunkers, roads, water


def stage5_ground(total_rows=208):
    tiles, ids = ground_tileset()
    body_rows = total_rows - 2 * LOOP_ROWS
    body, bunkers, roads, water = ground_map(body_rows, ids)
    rng = np.random.default_rng(55)
    loop = np.array([[ids[f"snow{int(rng.choice(4, p=[0.34, 0.3, 0.3, 0.06]))}"] for _ in range(COLS)]
                     for _ in range(LOOP_ROWS)], dtype=np.uint8)
    stage = np.concatenate([body, loop, loop], axis=0)
    return tiles, stage[::-1].copy(), bunkers, roads, water


# ---- sky -------------------------------------------------------------------

def _field(c, u, v):
    tl, tr, br, bl = c
    return tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v


def berg_tile(top, face, shadow, variant):
    """One tile of the berg layer, from three sets of corners (tl, tr, br,
    bl): the berg's snowy top, its cliff face (the top's corners one row
    further south) and a dithered shadow (two rows south)."""
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T
    n = value_noise(T, T, 4, 500 + variant)
    ft = _field(top, u, v) + (n - 0.5) * 0.12
    ff = _field(face, u, v) + (n - 0.5) * 0.12
    fs = _field(shadow, u, v)
    t = np.zeros((T, T), dtype=np.uint8)
    t[(fs >= 0.5) & ((xx + yy) % 2 == 0)] = SH
    # The cliff: dark ice in vertical streaks, darkest at its foot.
    cliff = ff >= 0.5
    t[cliff] = FACE
    t[cliff & ((xx * 7 + variant) % 5 == 0)] = BERG[0]
    t[cliff & ((xx * 3 + variant) % 7 == 0)] = BERG[1]
    t[cliff & (ff < 0.56)] = OUT
    body = ft >= 0.5
    t[body] = BERG[2]
    t[body & (ft > 0.62) & (n > 0.45)] = BERG[3]
    t[body & (ft > 0.75)] = BERG[3]
    t[body & (ft > 0.85) & (n > 0.6)] = BERG[4]
    t[body & (ft < 0.6)] = BERG[4]  # the lit rim
    t[body & (ft < 0.54)] = OUT
    return t


def berg_inner(variant):
    """A tile wholly inside a berg's top: a snowfield, one in four with a
    glinting crevasse."""
    n = _torus_noise(T, 8, 520 + variant) * 0.6 + _torus_noise(T, 4, 540 + variant) * 0.4
    t = np.full((T, T), BERG[3], dtype=np.uint8)
    t[n > 0.64] = BERG[4]
    t[n < 0.3] = BERG[2]
    if variant == 1:
        for x in range(3, 13):
            y = int(8 + 2 * np.sin(x * 0.7))
            t[y, x] = BERG[0]
            t[y - 1, x] = CREV[(x // 2) % 3]
    return t


def snow_streak(variant):
    """Blowing snow: a few streaks, slanting down and to the right."""
    rng = np.random.default_rng(600 + variant)
    t = np.zeros((T, T), dtype=np.uint8)
    for _ in range(3):
        x, y = int(rng.integers(0, T)), int(rng.integers(0, T))
        length = int(rng.integers(3, 6))
        for k in range(length):
            xx, yy = (x + k) % T, (y + k // 2) % T
            t[yy, xx] = FLAKE if k >= length - 2 else SNOW_D
    for _ in range(3):
        t[int(rng.integers(0, T)), int(rng.integers(0, T))] = FLAKE
    return t


def _place_berg(corners, r, c, w, h, rng):
    """An irregular blob of ice corners, w x h, its south-west corner at r, c."""
    cy, cx = r + (h - 1) / 2, c + (w - 1) / 2
    for y in range(r, r + h):
        for x in range(c, c + w):
            d = ((y - cy) / (h / 2)) ** 2 + ((x - cx) / (w / 2)) ** 2
            if d < 1.05 - rng.random() * 0.3:
                corners[y, x] = 1


def _cfg(g, y, x):
    """A tile's corners (tl, tr, br, bl) in stage order, where row y + 1 is
    the one above."""
    return (int(g[y + 1, x]), int(g[y + 1, x + 1]), int(g[y, x + 1]), int(g[y, x]))


def stage5_sky(rows, intro_rows=18, tail_rows=17, seed=9):
    """Bergs come in lanes with room to dodge between them; snow blows
    through the gaps. Tiles are made for the corner sets the map uses.
    Returns tiles, the map (top row first) and the solid tile ids."""
    rng = np.random.default_rng(seed)
    top = np.zeros((rows + 3, COLS + 1), dtype=np.uint8)
    end = rows - tail_rows
    r = intro_rows
    side = 0
    while r < end - 10:
        w, h = int(rng.integers(4, 7)), int(rng.integers(4, 7))
        lane = (side + int(rng.integers(1, 3))) % 3
        side = lane
        right = COLS + 1 - w
        lo, hi = [(0, 1), (right // 2 - 1, right // 2 + 1), (right - 1, right)][lane]
        _place_berg(top, r + 3, int(rng.integers(lo, hi + 1)), w, h, rng)
        r += h + 4 + int(rng.integers(1, 5))
    face = np.zeros_like(top)
    face[:-1] = top[1:]
    shadow = np.zeros_like(top)
    shadow[:-2] = top[2:]
    shadow[:, 1:] |= shadow[:, :-1].copy()  # the light is from the upper left
    tiles, ids, solid = [np.zeros((T, T), dtype=np.uint8)], {}, set()
    sky = np.zeros((rows, COLS), dtype=np.uint8)
    for k in range(4):
        ids[("inner", k)] = len(tiles)
        tiles.append(berg_inner(k))
        solid.add(ids[("inner", k)])
    for k in range(4):
        ids[("streak", k)] = len(tiles)
        tiles.append(snow_streak(k))
    for y in range(rows):
        for x in range(COLS):
            key = (_cfg(top, y, x), _cfg(face, y, x), _cfg(shadow, y, x))
            if key[0] == (1, 1, 1, 1):
                sky[y, x] = ids[("inner", int(rng.choice(4, p=[0.3, 0.25, 0.3, 0.15])))]
            elif any(key[0]) or any(key[1]) or any(key[2]):
                if key not in ids:
                    ids[key] = len(tiles)
                    tiles.append(berg_tile(*key, len(tiles)))
                    # Solid where most of the tile is berg, top or cliff.
                    if sum(key[0]) >= 3 or sum(key[1]) >= 3:
                        solid.add(ids[key])
                sky[y, x] = ids[key]
            elif intro_rows - 6 < y < end and rng.random() < 0.16:
                sky[y, x] = ids[("streak", int(rng.integers(0, 4)))]
    sky[end:, :] = 0
    assert len(tiles) <= 256
    return tiles, sky[::-1].copy(), solid
