"""Stage 8, DEEP FIELD: open space beyond the Moon, through a belt of
asteroids.

Two starfields at two depths. The ground (plane 0, palette DEEP) is the
far one: faint stars twinkling in the rotating entries 2-4, a nebula in
marching squares tiles, and a distant galaxy or two. The sky (plane 1,
palette DEEP_SKY) is the near one, scrolling half again as fast: bright
stars, and asteroids, solid, which the ship crashes into and which stop
shots and bullets alike. They come in drifts with a wide gap somewhere in
each, and lulls between.

Asteroids are lit lumpy spheres, cratered, rendered pixel by pixel from a
dozen templates (so the tiles stay few) and set down on the tile grid.
"""

import math

import numpy as np

from kit import BAYER4, value_noise
from orbit import TileSet, star_tile
from tiles import COLS, LOOP_ROWS, T, _torus_noise

DEEP = [
    (0, 0, 10),                                                         # 0 space (opaque)
    (60, 60, 100),                                                      # 1 dim star
    (110, 110, 160), (180, 180, 230), (255, 255, 255),                  # 2-4 stars (rotate: twinkle)
    (16, 6, 30), (34, 12, 56), (64, 22, 90), (112, 46, 132),            # 5-8 nebula
    (184, 100, 196),                                                    # 9 nebula core
    (20, 80, 110), (90, 200, 210),                                      # 10-11 galaxy arms
    (255, 230, 170),                                                    # 12 galaxy core
    None, None,                                                         # 13-14 (no lamps)
    (255, 250, 236),                                                    # 15 core, bright
]
NEB = [5, 6, 7, 8, 9]
ARM, ARM_HI, GCORE, GCORE_HI = 10, 11, 12, 15

DEEP_SKY = [
    None,                                                               # 0 clear
    (12, 8, 12),                                                        # 1 outline
    (140, 150, 200), (210, 220, 255), (255, 255, 255),                  # 2-4 near stars (rotate)
    (34, 28, 30), (58, 48, 46), (88, 74, 66), (122, 104, 90), (160, 140, 118), (204, 186, 158),  # 5-10 rock
    (18, 12, 14),                                                       # 11 crater shadow
    (160, 210, 255),                                                    # 12 ice glint
    None, None,                                                         # 13-14 (no lamps)
    (255, 236, 190),                                                    # 15 star, warm
]
OUT, ROCK, PIT, ICE, WARM = 1, [5, 6, 7, 8, 9, 10], 11, 12, 15
NEAR = [2, 3, 4]


# ---- ground: the far starfield ---------------------------------------------

def _cfg(g, y, x):
    """A tile's corners (tl, tr, br, bl) in stage order, row y + 1 above."""
    return (int(g[y + 1, x]), int(g[y + 1, x + 1]), int(g[y, x + 1]), int(g[y, x]))


def nebula_tile(c, inner, variant):
    """Marching squares nebula: a thin dithered veil at the rim, thickening
    inward, with a bright core where the inner field is set too. Stars
    shine through the veil."""
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T

    def field(k):
        tl, tr, br, bl = k
        return tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v

    b = _torus_noise(T, 8, 900 + variant) * 0.6 + _torus_noise(T, 4, 910 + variant) * 0.4
    f = field(c) + (b - 0.5) * 0.3
    g = field(inner) + (b - 0.5) * 0.35
    bay = BAYER4[yy % 4, xx % 4] + 0.5
    t = star_tile(variant % 8)
    # The veil thickens inward by dithering: space, then NEB 0, then 1.
    veil = f > 0.4
    t[veil & (bay < (f - 0.4) * 3.5)] = NEB[0]
    t[f > 0.68] = NEB[0]
    t[(f > 0.68) & (bay < (f - 0.68) * 3.5)] = NEB[1]
    t[f > 0.95] = NEB[1]
    # The core glows through it.
    core = g > 0.48
    t[core & (bay < (g - 0.48) * 4)] = NEB[2]
    t[g > 0.72] = NEB[2]
    t[(g > 0.72) & (bay < (g - 0.72) * 3)] = NEB[3]
    t[(g > 0.95) & (b > 0.62) & (bay < 0.5)] = NEB[4]
    return t


def galaxy():
    """A spiral galaxy seen at a slant, 2 x 2 tiles."""
    n = 2 * T
    yy, xx = np.mgrid[0:n, 0:n]
    x, y = (xx - n / 2 + 0.5), (yy - n / 2 + 0.5) * 1.8
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    arm = np.cos(2 * a - r * 0.42)
    img = np.zeros((n, n), dtype=np.uint8)
    bay = BAYER4[yy % 4, xx % 4] + 0.5
    disc = r < 15
    img[disc & (arm > 0.4) & (bay < (1 - r / 15) * 1.6)] = ARM
    img[disc & (arm > 0.7) & (r < 11)] = ARM
    img[disc & (arm > 0.85) & (r < 9) & (bay < 0.6)] = ARM_HI
    img[r < 5] = GCORE
    img[r < 2.5] = GCORE_HI
    return [img[:T, :T], img[:T, T:], img[T:, :T], img[T:, T:]]


STAR_P = [0.3, 0.2, 0.15, 0.1, 0.04, 0.08, 0.08, 0.05]


def ground_map(rows, seed=8):
    """Stage order, bottom row first: stars, then nebulae from row 14 on."""
    rng = np.random.default_rng(seed)
    ts = TileSet()
    for k in range(8):
        ts.add(("star", k), lambda k=k: star_tile(k))
    n = value_noise(COLS + 1, rows + 1, 5, seed) * 0.65 + value_noise(COLS + 1, rows + 1, 2, seed + 1) * 0.35
    neb = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    inner = np.zeros_like(neb)
    for r in range(14, rows - 4):
        # Nebulae swell and thin in long waves.
        cov = 0.34 + 0.14 * math.sin(r / 23.0)
        neb[r] = n[r] > 1.0 - cov
        inner[r] = n[r] > 1.0 - cov * 0.45
    m = np.zeros((rows, COLS), dtype=np.uint8)
    for r in range(rows):
        for c in range(COLS):
            cfg, icfg = _cfg(neb, r, c), _cfg(inner, r, c)
            if any(cfg):
                v = int(rng.integers(0, 2)) if cfg == (1, 1, 1, 1) and not any(icfg) else 0
                key = ("neb", cfg, icfg, v)
                m[r, c] = ts.add(key, lambda cfg=cfg, icfg=icfg, v=v: nebula_tile(cfg, icfg, v * 4 + sum(cfg)))
            else:
                m[r, c] = ts.ids[("star", int(rng.choice(8, p=STAR_P)))]
    # Galaxies, far off in the clear patches.
    g = galaxy()
    gid = [ts.add(("galaxy", k), lambda k=k: g[k]) for k in range(4)]
    placed = 0
    for r in range(30, rows - 8, 41):
        for c in rng.permutation(COLS - 1):
            if not neb[r - 1:r + 3, c:c + 3].any():
                m[r + 1, c], m[r + 1, c + 1], m[r, c], m[r, c + 1] = gid
                placed += 1
                break
    assert placed >= 2
    return ts, m


def stage8_ground(total_rows=208):
    body_rows = total_rows - 2 * LOOP_ROWS
    ts, body = ground_map(body_rows)
    rng = np.random.default_rng(88)
    loop = np.array([[ts.ids[("star", int(rng.choice(8, p=STAR_P)))] for _ in range(COLS)]
                     for _ in range(LOOP_ROWS)], dtype=np.uint8)
    stage = np.concatenate([body, loop, loop], axis=0)
    assert len(ts.tiles) <= 256
    return ts.tiles, stage[::-1].copy()


# ---- sky: the near starfield and the asteroids ----------------------------

def asteroid(w, h, seed):
    """An asteroid filling w x h tiles: a lumpy sphere lit from the upper
    left, its craters bowls with a lit far rim. Returns the image."""
    rng = np.random.default_rng(1000 + seed)
    W, H = w * T, h * T
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = W / 2 - 0.5, H / 2 - 0.5
    rx, ry = (W / 2 - 1.5, H / 2 - 1.5) if w > 1 else (5.0, 4.0)
    a = np.arctan2((yy - cy) / ry, (xx - cx) / rx)
    lump = np.ones_like(a)
    for k in (2, 3, 5):
        lump += rng.uniform(0.05, 0.12) * np.cos(k * a + rng.uniform(0, 2 * math.pi)) * (3 / k)
    lump *= 0.86
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) / lump
    inside = d < 1
    hgt = np.sqrt(np.clip(1 - d * d, 0, 1)) * min(rx, ry) * 0.9
    hgt += value_noise(W, H, 4, 1100 + seed) * 1.6 + value_noise(W, H, 2, 1200 + seed) * 0.6
    pits = []
    for _ in range(0 if w == 1 else int(rng.integers(2, 2 + (w + h) // 2 + 1))):
        pr = rng.uniform(2.2, 2 + min(w, h) * 2.2)
        ang, rad = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.62)
        px, py = cx + math.cos(ang) * rad * rx, cy + math.sin(ang) * rad * ry
        dc = np.sqrt((xx - px) ** 2 + (yy - py) ** 2) / pr
        hgt -= np.where(dc < 1, (1 - dc * dc) * pr * 0.9, 0)
        hgt += np.where((dc >= 1) & (dc < 1.35), (1.35 - dc) * pr * 0.6, 0)
        pits.append(dc)
    gy, gx = np.gradient(hgt)
    light = np.array([-0.55, -0.75, 0.9])
    light /= np.linalg.norm(light)
    nl = np.sqrt(gx * gx + gy * gy + 1)
    lam = np.clip((-gx * light[0] - gy * light[1] + light[2]) / nl, 0, 1)
    inten = np.clip(0.1 + 0.9 * lam ** 1.3, 0, 1)
    bay = BAYER4[yy % 4, xx % 4]
    lvl = np.clip(np.round(inten * (len(ROCK) - 1) + bay * 0.9), 0, len(ROCK) - 1).astype(int)
    img = np.zeros((H, W), dtype=np.uint8)
    img[inside] = np.array(ROCK)[lvl[inside]]
    deep = np.zeros_like(inside)
    for dc in pits:
        deep |= dc < 0.55
    img[inside & deep & (inten < 0.35)] = PIT
    glint = inside & (inten > 0.95) & (value_noise(W, H, 2, 1300 + seed) > 0.8)
    img[glint] = ICE
    pad = np.pad(inside, 1)
    nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    img[~inside & nb] = OUT
    return img


# (w, h) in tiles; each drawn once and reused.
TEMPLATES = [(1, 1), (1, 1), (2, 2), (2, 2), (3, 2), (2, 3), (3, 3), (3, 3), (4, 3), (4, 4)]
WEIGHTS = [0, 0, 5, 5, 4, 4, 3, 3, 2.5, 2]  # the 1 x 1s are debris, scattered apart


def near_star(k):
    rng = np.random.default_rng(1400 + k)
    t = np.zeros((T, T), dtype=np.uint8)
    y, x = int(rng.integers(2, T - 2)), int(rng.integers(2, T - 2))
    if k < 2:
        t[y, x] = NEAR[k + 1]
    elif k == 2:
        t[y, x] = WARM
    else:
        t[y, x] = NEAR[2]
        t[y - 1, x] = t[y + 1, x] = t[y, x - 1] = t[y, x + 1] = NEAR[0]
    return t


def stage8_sky(rows, intro_rows=18, tail_rows=17, seed=8):
    """Returns tiles, the map (top row first), the solid tile ids (whole
    tiles: what stops bullets and what enemies steer round) and the tile
    ids with rock in them at all (what the ship crashes on, finely)."""
    rng = np.random.default_rng(seed)
    tiles, solid, rock = [np.zeros((T, T), dtype=np.uint8)], set(), set()
    stars = []
    for k in range(4):
        stars.append(len(tiles))
        tiles.append(near_star(k))
    # Each template cut into tiles; a tile mostly rock is solid.
    tmpl = []
    for i, (w, h) in enumerate(TEMPLATES):
        if i == 1:  # the debris shares one image: XRAM is tight
            tmpl.append(tmpl[0])
            continue
        img = asteroid(w, h, i)
        ids = np.zeros((h, w), dtype=int)
        for r in range(h):
            for c in range(w):
                t = img[r * T:(r + 1) * T, c * T:(c + 1) * T]
                if not t.any():
                    continue
                ids[r, c] = len(tiles)
                tiles.append(t.copy())
                if w > 1:
                    rock.add(ids[r, c])
                    if (t >= ROCK[0]).mean() >= 0.5:
                        solid.add(ids[r, c])
        tmpl.append(ids)
    sky = np.zeros((rows, COLS), dtype=np.uint8)
    used = np.zeros((rows, COLS), dtype=bool)
    end = rows - tail_rows

    def gap_ok(r0, h):
        """Every row keeps a run of four clear columns: room to pass."""
        for r in range(r0, r0 + h):
            run = best = 0
            for c in range(COLS):
                run = 0 if used[r, c] else run + 1
                best = max(best, run)
            if best < 4:
                return False
        return True

    p = np.array(WEIGHTS) / sum(WEIGHTS)
    r = intro_rows
    while r < end - 5:
        # Drifts of rocks, then a lull.
        drift = int(rng.integers(14, 26))
        stop = min(r + drift, end - 5)
        while r < stop:
            k = int(rng.choice(len(TEMPLATES), p=p))
            ids = tmpl[k]
            h, w = ids.shape
            for _ in range(6):
                c = int(rng.integers(-1, COLS - w + 2))
                c0, c1 = max(c, 0), min(c + w, COLS)
                area = used[max(r - 1, 0):r + h + 1, max(c0 - 1, 0):c1 + 1]
                if c1 - c0 < max(1, w - 1) or area.any():
                    continue
                used[r:r + h, c0:c1] = True
                if not gap_ok(r, h):
                    used[r:r + h, c0:c1] = False
                    continue
                for y in range(h):
                    for x in range(w):
                        if 0 <= c + x < COLS and ids[y, x]:
                            # Stage order: the template's top row is the highest.
                            sky[r + h - 1 - y, c + x] = ids[y, x]
                break
            r += int(rng.integers(1, 4))
        r += int(rng.integers(8, 14))
    # Debris and near stars in what is left.
    for y in range(rows):
        for x in range(COLS):
            if sky[y, x] or used[y, x]:
                continue
            if intro_rows - 6 < y < end and rng.random() < 0.035:
                sky[y, x] = tmpl[int(rng.integers(0, 2))][0, 0]
            elif rng.random() < 0.13:
                sky[y, x] = stars[int(rng.choice(4, p=[0.4, 0.3, 0.12, 0.18]))]
    sky[end:, :] = 0
    assert len(tiles) <= 256
    return tiles, sky[::-1].copy(), solid, rock
