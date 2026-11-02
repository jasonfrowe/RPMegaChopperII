"""Stage 3, IRON TIDE: open ocean with jungle islands, and clouds above.

Ground (plane 0, palette OCEAN): the sea of stage 1 in a deeper blue, with
islands cut by marching squares (surf, sand, rock, jungle) and concrete
bunkers for turrets. Gunboats sail the open water. The map's top loops
over open sea for the battleship fight.

Sky (plane 1, palette SKY): drifting clouds only; nothing to crash into.
"""

import math

import numpy as np

import city
from kit import value_noise
from tiles import COLS, LOOP_ROWS, T, _torus_noise

OCEAN = [
    (4, 12, 30),                                                        # 0 backdrop (opaque)
    (10, 36, 80), (14, 46, 96), (18, 54, 110), (24, 64, 124),          # 1-4 sea (2-4 rotate, kept close to prevent flashing)
    (44, 36, 30), (74, 60, 46), (116, 96, 68), (170, 148, 100), (220, 204, 156),  # 5-9 rock and sand
    (6, 10, 20),                                                        # 10 shadow
    (28, 86, 44), (72, 150, 62),                                        # 11-12 jungle
    (255, 60, 60), (120, 255, 200),                                     # 13-14 lamps (blink)
    (226, 244, 255),                                                    # 15 surf
]
SEA = [1, 2, 3, 4]
ROCK = [5, 6, 7, 8, 9]
SHADOW, JUNGLE, JUNGLE2, LAMP_R, LAMP_G, FOAM = 10, 11, 12, 13, 14, 15

# Clouds only: the cloud tiles draw with entries 12 and 15 (see city.py).
SKY = [None] * 16
SKY[12] = (150, 162, 190)
SKY[15] = (232, 238, 250)


def sea_tile(variant):
    """Calm, serene deep-sea tiles with gentle rolling swells and subtle crests."""
    n1 = _torus_noise(T, 8, 42 + variant * 19)
    n2 = _torus_noise(T, 4, 88 + variant * 31)
    yy, xx = np.mgrid[0:T, 0:T]
    swell = (np.sin((2 * np.pi * (xx + yy)) / T + variant * 1.57) + 1.0) * 0.5
    v = n1 * 0.50 + n2 * 0.35 + swell * 0.15
    v = (v - v.min()) / (v.max() - v.min() + 1e-6)
    t = np.full((T, T), SEA[0], dtype=np.uint8)  # 1: base deep sea (~75%)
    t[v > 0.68] = SEA[1]                         # 2: gentle swell slope (~16%)
    t[v > 0.82] = SEA[2]                         # 3: soft ripple (~6%)
    t[v > 0.92] = SEA[3]                         # 4: rare sparkling crest tip (~3%)
    return t


def land(seed):
    """Island interior: jungle over rock."""
    n = value_noise(T, T, 4, 900 + seed) * 0.6 + value_noise(T, T, 2, 950 + seed) * 0.4
    t = np.full((T, T), JUNGLE, dtype=np.uint8)
    t[n > 0.55] = JUNGLE2
    t[n < 0.28] = ROCK[1]
    t[(n < 0.22)] = SHADOW
    return t


def edge_tile(c, variant=0):
    tl, tr, br, bl = c
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T
    f = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v
    f = f + (value_noise(T, T, 4, 970 + variant) - 0.5) * 0.12
    t = sea_tile(variant % 4)
    inner = land(variant)
    t[f >= 0.62] = inner[f >= 0.62]
    t[(f >= 0.50) & (f < 0.62)] = ROCK[4]  # sand
    t[(f >= 0.56) & (f < 0.62) & ((xx + yy) % 3 == 0)] = ROCK[3]
    t[(f < 0.50) & (f >= 0.44)] = FOAM
    t[(f < 0.44) & (f >= 0.40)] = SEA[3]
    return t


def bunker_tiles():
    big = np.zeros((32, 32), dtype=np.uint8)
    for ty in range(2):
        for tx in range(2):
            big[ty * T:(ty + 1) * T, tx * T:(tx + 1) * T] = land(20 + ty * 2 + tx)
    yy, xx = np.mgrid[0:32, 0:32]
    sq = np.maximum(np.abs(xx - 15.5), np.abs(yy - 15.5))
    big[sq < 14] = ROCK[2]
    big[(sq < 14) & (sq >= 12.5) & ((xx < yy))] = ROCK[0]
    big[(sq < 14) & (sq >= 12.5) & ((xx >= yy))] = ROCK[3]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 10] = ROCK[1]
    big[d < 8] = SHADOW
    big[(d < 10) & (d > 8.5) & ((xx + yy) % 4 == 0)] = ROCK[4]
    big[d < 2.5] = LAMP_R
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def ground_tileset():
    tiles, ids = [], {}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"sea{k}", sea_tile(k))
    for cfg in range(1, 16):
        c = ((cfg >> 3) & 1, (cfg >> 2) & 1, (cfg >> 1) & 1, cfg & 1)
        add(f"edge{cfg}", edge_tile(c, cfg))
    add("land1", edge_tile((1, 1, 1, 1), 33))
    add("land2", edge_tile((1, 1, 1, 1), 34))
    for k, t in enumerate(bunker_tiles()):
        add(f"bunker{k}", t)
    return tiles, ids


def ground_map(rows, ids, seed=7):
    """Stage order. Islands come and go; open water between them for boats."""
    rng = np.random.default_rng(seed)
    n = value_noise(COLS + 1, rows + 1, 4, seed) * 0.65 + value_noise(COLS + 1, rows + 1, 2, seed + 1) * 0.35
    corners = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    for r in range(rows + 1):
        t = r / rows
        cov = 0.0 if t < 0.06 or t > 0.9 else 0.30 + 0.12 * math.sin(t * 17)
        for c in range(COLS + 1):
            # Islands keep to the sides more than the middle.
            side = abs(c - COLS / 2) / (COLS / 2)
            corners[r, c] = 1 if n[r, c] * 0.8 + side * 0.25 > 1.0 - cov else 0
    m = np.zeros((rows, COLS), dtype=np.uint8)
    for r in range(rows):
        for c in range(COLS):
            tl, tr = corners[r + 1, c], corners[r + 1, c + 1]
            bl, br = corners[r, c], corners[r, c + 1]
            cfg = (tl << 3) | (tr << 2) | (br << 1) | bl
            if cfg == 0:
                m[r, c] = ids[f"sea{int(rng.integers(0, 4))}"]
            elif cfg == 15:
                m[r, c] = ids["land1" if rng.random() < 0.5 else "land2"]
            else:
                m[r, c] = ids[f"edge{cfg}"]
    bunkers, water = [], []
    used = np.zeros((rows, COLS), dtype=bool)
    full = (ids["land1"], ids["land2"])
    for r in range(1, rows - 1):
        for c in range(COLS - 1):
            if all(m[r + dy, c + dx] in full for dy in (0, 1) for dx in (0, 1)) and not used[r:r + 2, c:c + 2].any() \
                    and rng.random() < 0.25:
                m[r + 1, c], m[r + 1, c + 1] = ids["bunker0"], ids["bunker1"]
                m[r, c], m[r, c + 1] = ids["bunker2"], ids["bunker3"]
                used[r - 2:r + 4, c - 2:c + 4] = True
                bunkers.append((r, c))
    # Open water wide enough for a gunboat: three clear columns, four rows.
    sea_ids = {ids[f"sea{k}"] for k in range(4)}
    r = 0
    while r < rows - 4:
        spots = [c for c in range(1, COLS - 2) if all(m[r + dy, c + dx] in sea_ids
                                                       for dy in range(4) for dx in range(-1, 2))]
        if spots:
            water.append((r + 2, spots[int(rng.integers(0, len(spots)))]))
            r += 6
        else:
            r += 1
    return m, bunkers, water


def stage3_ground(total_rows=208):
    tiles, ids = ground_tileset()
    body_rows = total_rows - 2 * LOOP_ROWS
    body, bunkers, water = ground_map(body_rows, ids)
    rng = np.random.default_rng(77)
    loop = np.array([[ids[f"sea{int(rng.integers(0, 4))}"] for _ in range(COLS)] for _ in range(LOOP_ROWS)],
                    dtype=np.uint8)
    stage = np.concatenate([body, loop, loop], axis=0)
    return tiles, stage[::-1].copy(), bunkers, water


def stage3_sky(rows, seed=21):
    """Clouds only, thicker than stage 2's, empty for the last screen."""
    tiles = [np.zeros((T, T), dtype=np.uint8)]
    ids = {"clear": 0}
    for cfg in range(1, 16):
        c = ((cfg >> 3) & 1, (cfg >> 2) & 1, (cfg >> 1) & 1, cfg & 1)
        ids[f"cloud{cfg}"] = len(tiles)
        tiles.append(city.cloud_tile(c, cfg + 40))
    ids["cloud15b"] = len(tiles)
    tiles.append(city.cloud_tile((1, 1, 1, 1), 77))
    rng = np.random.default_rng(seed)
    corners = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    end = rows - 17
    r = 10
    while r < end - 5:
        cw, ch = int(rng.integers(3, 7)), int(rng.integers(2, 4))
        cc = int(rng.integers(-1, COLS - cw + 1))
        city._place_cloud(corners, r, max(0, cc), cw, ch, rng)
        r += ch + int(rng.integers(3, 8))
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
    return tiles, sky[::-1].copy()
