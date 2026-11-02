"""Stage 6, ASCENT: climbing out of the atmosphere. The ocean and its cloud
systems fall away below and darken, the curve of the Earth's limb passes
underneath, glowing, and beyond it is black space.

Ground (plane 0, palette ORBIT): ocean and marching squares clouds, then
the limb (rendered pixel by pixel and cut into tiles), then stars. The
ocean and clouds use entries 5-11, which the game fades toward black as
the stage goes on (stage_def_t's fade); the limb's glow (12, 15) and the
stars do not fade. Stars twinkle in the rotating entries 2-4.

Sky (plane 1, palette ORBIT_SKY): thin cirrus low down, then satellites
with solar wings, solid: the ship crashes into them. Their panels
shimmer in entries 2-4 and their beacons blink.
"""

import math

import numpy as np

from kit import value_noise
from tiles import COLS, LOOP_ROWS, T, _torus_noise

ORBIT = [
    (0, 0, 8),                                                          # 0 space (opaque)
    (70, 80, 120),                                                      # 1 dim star
    (120, 130, 170), (190, 200, 230), (255, 255, 255),                  # 2-4 stars (rotate: twinkle)
    (12, 44, 112), (22, 66, 150), (40, 98, 184),                        # 5-7 ocean (fade)
    (70, 130, 200),                                                     # 8 shallows, cloud shadow (fade)
    (150, 172, 210), (200, 214, 236), (244, 248, 255),                  # 9-11 cloud (fade)
    (60, 130, 255),                                                     # 12 atmosphere
    None, None,                                                         # 13-14 (no lamps)
    (180, 230, 255),                                                    # 15 atmosphere, bright
]
STAR = [1, 2, 3, 4]
SEA = [5, 6, 7, 8]
CLOUD = [9, 10, 11]
AIR, AIR_HI = 12, 15
FADE_FIRST, FADE_N = 5, 7  # entries 5-11 fade

ORBIT_SKY = [
    None,                                                               # 0 clear
    (6, 8, 20),                                                         # 1 outline
    (26, 54, 130), (36, 74, 168), (54, 100, 206),                       # 2-4 solar cells (rotate)
    (36, 40, 54), (66, 72, 90), (106, 114, 134), (156, 164, 184), (214, 220, 232),  # 5-9 metal
    (10, 12, 22),                                                       # 10 dark
    (214, 164, 44),                                                     # 11 gold foil
    (150, 172, 214),                                                    # 12 cirrus, shaded
    (255, 50, 50), (80, 255, 140),                                      # 13-14 beacons (blink)
    (232, 240, 255),                                                    # 15 cirrus
]
OUT, DARK, FOIL, CIRRUS_D, BEACON_R, BEACON_G, CIRRUS = 1, 10, 11, 12, 13, 14, 15
CELL = [2, 3, 4]
METAL = [5, 6, 7, 8, 9]


# ---- ground --------------------------------------------------------------

def ocean_tile(variant):
    """Open ocean seen from very high up: an even deep blue, faintly mottled."""
    n = _torus_noise(T, 8, 700 + variant) * 0.5 + _torus_noise(T, 4, 720 + variant) * 0.5
    t = np.full((T, T), SEA[1], dtype=np.uint8)
    yy, xx = np.mgrid[0:T, 0:T]
    t[(n < 0.3) & ((xx + yy) % 2 == 0)] = SEA[0]
    t[(n > 0.72) & ((xx + yy) % 2 == 0)] = SEA[2]
    return t


def cloud_tile(c, variant):
    """Marching squares cloud over the ocean: dithered rim, a shadow cast
    to the south-east, a lit top."""
    tl, tr, br, bl = c
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T

    def field(du, dv):
        uu, vv = u - du, v - dv
        return tl * (1 - uu) * (1 - vv) + tr * uu * (1 - vv) + br * uu * vv + bl * (1 - uu) * vv

    n = value_noise(T, T, 4, 740 + variant) * 0.3
    f = field(0, 0) + n
    t = ocean_tile(variant % 4)
    sh = field(0.15, 0.2) + n
    t[(sh > 0.62) & ((xx + yy) % 2 == 0)] = SEA[0]
    # Billows: seamless noise inside, so whole-cloud tiles join up.
    b = _torus_noise(T, 8, 780 + variant % 3) * 0.6 + _torus_noise(T, 4, 790 + variant % 3) * 0.4
    body = f > 0.5
    t[body & ((xx + yy) % 2 == 0)] = CLOUD[0]
    t[body & ((xx + yy) % 2 == 1)] = SEA[2]
    inner = body & (f > 0.62)
    t[inner] = CLOUD[1]
    t[inner & (b < 0.35)] = CLOUD[0]
    t[inner & (b > 0.55) & ((xx + yy) % 2 == 0)] = CLOUD[2]
    t[inner & (b > 0.68)] = CLOUD[2]
    return t


def star_tile(variant):
    rng = np.random.default_rng(760 + variant)
    t = np.zeros((T, T), dtype=np.uint8)
    for _ in range(int(rng.integers(0, 4))):
        t[int(rng.integers(0, T)), int(rng.integers(0, T))] = STAR[0]
    if variant % 2 == 0:
        t[int(rng.integers(1, T - 1)), int(rng.integers(1, T - 1))] = STAR[1 + variant // 2 % 3]
    if variant == 4:
        y, x = 8, 7
        t[y, x] = STAR[3]
        t[y - 1, x] = t[y + 1, x] = t[y, x - 1] = t[y, x + 1] = STAR[1]
    return t


def _cfg(g, y, x):
    return (int(g[y + 1, x]), int(g[y + 1, x + 1]), int(g[y, x + 1]), int(g[y, x]))


class TileSet:
    """Tiles made on demand and shared by key; images deduplicated."""

    def __init__(self):
        self.tiles, self.ids, self.by_bytes = [], {}, {}

    def add(self, key, make):
        if key in self.ids:
            return self.ids[key]
        img = make()
        b = img.tobytes()
        if b not in self.by_bytes:
            self.by_bytes[b] = len(self.tiles)
            self.tiles.append(img)
        self.ids[key] = self.by_bytes[b]
        return self.ids[key]


LIMB_ROW = 112      # body row (from the bottom) where the limb is highest
LIMB_R = 240.0      # the Earth's radius in pixels: the limb's curve


def ground_map(rows, seed=6):
    """Stage order, bottom row first. Returns tiles and the map."""
    rng = np.random.default_rng(seed)
    ts = TileSet()
    for k in range(8):
        ts.add(("star", k), lambda k=k: star_tile(k))
    n = value_noise(COLS + 1, rows + 1, 4, seed) * 0.7 + value_noise(COLS + 1, rows + 1, 2, seed + 1) * 0.3
    clouds = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    for r in range(rows + 1):
        # Cloud systems thin out toward the limb.
        cov = 0.42 if r < 40 else 0.42 - (r - 40) * 0.005
        clouds[r] = n[r] > 1.0 - cov
    clouds[LIMB_ROW - 18:] = 0
    m = np.zeros((rows, COLS), dtype=np.uint16)
    # The limb: a curve highest at x = 96, its height y_limb(x) a circle of
    # radius LIMB_R (near enough a parabola). d is how far above it.
    top = LIMB_ROW * T + T // 2
    yy, xx = np.mgrid[0:T, 0:T]
    for r in range(rows):
        for c in range(COLS):
            # Pixel centers in stage order: y up from the bottom of the map.
            py = r * T + (T - 1 - yy) + 0.5
            px = c * T + xx + 0.5
            d = py - (top - (px - 96) ** 2 / (2 * LIMB_R))
            if d.max() < -16:
                cfg = _cfg(clouds, r, c)
                if any(cfg):
                    v = int(rng.integers(0, 3)) if cfg == (1, 1, 1, 1) else 0
                    m[r, c] = ts.add(("cloud", cfg, v), lambda cfg=cfg, v=v: cloud_tile(cfg, v * 16 + sum(cfg)))
                else:
                    v = int(rng.integers(0, 4))
                    m[r, c] = ts.add(("ocean", v), lambda v=v: ocean_tile(v))
            elif d.min() > 8:
                v = int(rng.choice(8, p=[0.3, 0.2, 0.15, 0.1, 0.04, 0.08, 0.08, 0.05]))
                m[r, c] = ts.add(("star", v), None)
            else:
                v = int(rng.integers(0, 4))
                base = ocean_tile(v)
                star = star_tile(int(rng.integers(0, 4)))
                t = base.copy()
                t[d > -16] = SEA[0]
                t[(d > -12) & ((xx + yy) % 2 == 0)] = SEA[1]
                t[d > -8] = SEA[1]
                t[(d > -5) & ((xx + yy) % 2 == 0)] = AIR
                t[d > -3] = AIR
                t[d > -1.5] = AIR_HI
                t[d > 0] = AIR
                t[(d > 1.5) & ((xx + yy) % 2 == 0)] = 0
                t[(d > 1.5) & ((xx + yy) % 2 == 1)] = AIR
                t[d > 3.5] = star[d > 3.5]
                t[(d > 3.5) & (d < 6) & ((xx + yy) % 4 == 0)] = AIR
                key = ("limb", r, c)
                m[r, c] = ts.add(key, lambda t=t: t)
    return ts, m


def stage6_ground(total_rows=208):
    body_rows = total_rows - 2 * LOOP_ROWS
    ts, body = ground_map(body_rows)
    rng = np.random.default_rng(66)
    loop = np.array([[ts.ids[("star", int(rng.choice(8, p=[0.3, 0.2, 0.15, 0.1, 0.04, 0.08, 0.08, 0.05])))]
                      for _ in range(COLS)] for _ in range(LOOP_ROWS)], dtype=np.uint8)
    stage = np.concatenate([body.astype(np.uint8), loop, loop], axis=0)
    assert len(ts.tiles) <= 256
    return ts.tiles, stage[::-1].copy()


# ---- sky -------------------------------------------------------------------

def cirrus_tile(variant):
    """Thin, streaky high cloud: transparent, mostly."""
    n = value_noise(T, T, 4, 800 + variant)
    yy, xx = np.mgrid[0:T, 0:T]
    band = np.sin((yy * 1.1 - xx * 0.25 + n * 5 + variant) * 0.9)
    t = np.zeros((T, T), dtype=np.uint8)
    t[(band > 0.6) & ((xx + yy) % 2 == 0)] = CIRRUS_D
    t[(band > 0.85) & ((xx + yy) % 2 == 0)] = CIRRUS
    return t


def _panel(edge_l, edge_r, half):
    """Solar wing, half 0 the top row of two, 1 the bottom: cells in a grid."""
    t = np.full((T, T), DARK, dtype=np.uint8)
    yy, xx = np.mgrid[0:T, 0:T]
    cell = ((xx % 4) != 3) & ((yy % 4) != 3)
    t[cell] = CELL[0]
    t[cell & ((xx // 4 + yy // 4 + half) % 3 == 1)] = CELL[1]
    t[cell & ((xx // 4 + yy // 4 + half) % 5 == 3)] = CELL[2]
    if half == 0:
        t[0, :] = OUT
        t[1, :] = METAL[3]
    else:
        t[T - 1, :] = OUT
        t[T - 2, :] = METAL[0]
    if edge_l:
        t[:, 0] = OUT
        t[:, 1] = METAL[3]
    if edge_r:
        t[:, T - 1] = OUT
        t[:, T - 2] = METAL[0]
    return t


def _truss(half):
    t = np.zeros((T, T), dtype=np.uint8)
    y0 = 12 if half == 0 else 0
    t[y0:y0 + 4, :] = METAL[2]
    t[y0 if half == 0 else 3, :] = OUT if half == 0 else METAL[0]
    t[(y0 + 1) if half == 0 else 0, :] = METAL[4] if half == 0 else METAL[2]
    t[y0:y0 + 4, ::4] = METAL[0]
    return t


def _body(k):
    """The satellite's 2 x 2 body: gold foil, a dish, a beacon. k 0-3, tl tr bl br."""
    big = np.full((32, 32), FOIL, dtype=np.uint8)
    yy, xx = np.mgrid[0:32, 0:32]
    n = value_noise(32, 32, 3, 820)
    big[n > 0.6] = METAL[4]
    big[n < 0.3] = METAL[2]
    big[(xx < 2) | (yy < 2) | (xx > 29) | (yy > 29)] = OUT
    big[(xx == 2) | (yy == 2)] = METAL[4]
    big[(xx == 29) | (yy == 29)] = METAL[0]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 9] = METAL[3]
    big[(d < 9) & (xx + yy > 31)] = METAL[2]
    big[(d < 9) & (d > 7.8)] = OUT
    big[d < 2.5] = METAL[4]
    big[5:7, 5:7] = BEACON_R
    big[25:27, 25:27] = BEACON_G
    y, x = divmod(k, 2)
    return big[y * T:(y + 1) * T, x * T:(x + 1) * T]


def sky_tileset():
    tiles, ids, solid = [np.zeros((T, T), dtype=np.uint8)], {"clear": 0}, set()

    def add(name, t, is_solid=False):
        ids[name] = len(tiles)
        tiles.append(t)
        if is_solid:
            solid.add(ids[name])

    for k in range(4):
        add(f"cirrus{k}", cirrus_tile(k))
    for half in range(2):
        for name, el, er in (("l", True, False), ("m", False, False), ("r", False, True)):
            add(f"panel_{name}{half}", _panel(el, er, half), True)
        add(f"truss{half}", _truss(half), True)
    for k in range(4):
        add(f"body{k}", _body(k), True)
    return tiles, ids, solid


def _place_sat(sky, ids, r, c, wing_l, wing_r):
    """A satellite in stage order: rows r (bottom) and r + 1, its body at
    columns c..c+1, with a truss and wing_l / wing_r panels on each side."""
    def put(col, name):
        if 0 <= col < COLS:
            sky[r + 1, col] = ids[name + "0"]
            sky[r, col] = ids[name + "1"]

    sky[r + 1, c], sky[r + 1, c + 1] = ids["body0"], ids["body1"]
    sky[r, c], sky[r, c + 1] = ids["body2"], ids["body3"]
    for side, wing, step in ((-1, wing_l, c - 1), (1, wing_r, c + 2)):
        if not wing:
            continue
        put(step, "truss")
        for k in range(wing):
            col = step + side * (k + 1)
            last = k == wing - 1
            put(col, "panel_" + ("l" if side < 0 and last else "r" if side > 0 and last else "m"))


def stage6_sky(rows, sat_from, intro_rows=18, tail_rows=17, seed=6):
    """Cirrus low down; satellites from sky row sat_from, swinging from one
    side to the other with a wide gap to fly through."""
    tiles, ids, solid = sky_tileset()
    rng = np.random.default_rng(seed)
    sky = np.zeros((rows, COLS), dtype=np.uint8)
    end = rows - tail_rows
    n = value_noise(COLS, rows, 3, seed)
    for y in range(intro_rows - 6, min(sat_from - 8, end)):
        for x in range(COLS):
            if n[y, x] > 0.55 and rng.random() < 0.7:
                sky[y, x] = ids[f"cirrus{int(rng.integers(0, 4))}"]
    r = sat_from
    left = True
    while r < end - 4:
        wing = int(rng.integers(1, 3))
        span = 2 + 2 * (1 + wing)  # body, two trusses, two wings
        if left:
            c = int(rng.integers(1 + wing, 3 + wing))
        else:
            c = COLS - 2 - 1 - wing - int(rng.integers(0, 2))
        _place_sat(sky, ids, r, c, wing, wing)
        assert span <= COLS - 4
        left = not left if rng.random() < 0.8 else left
        r += 2 + 5 + int(rng.integers(0, 4))
    sky[end:, :] = 0
    return tiles, sky[::-1].copy(), solid
