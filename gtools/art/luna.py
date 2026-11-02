"""Stage 7, SEA OF TRANQUILITY: the Moon's surface, cratered gray
regolith, and the enemy's lunar bases.

Ground (plane 0, palette LUNA): regolith tiles with craters stamped over
them in three sizes, lit from the upper left like everything else; and
bases: plazas of metal floor with glass domes, landing pads whose lights
run (entries 2-4 rotate), turret bunkers and a road across each one for
rovers. No sky layer: there is no air to hold clouds, and the boss needs
plane 1 for its hull.
"""

import numpy as np

from kit import value_noise
from tiles import COLS, LOOP_ROWS, T, _torus_noise

LUNA = [
    (0, 0, 0),                                                          # 0 backdrop (opaque)
    (22, 22, 28),                                                       # 1 shadow
    (255, 160, 40), (255, 214, 110), (255, 248, 210),                   # 2-4 runway lights (rotate)
    (52, 52, 60), (82, 82, 92), (118, 118, 128), (158, 158, 168), (204, 204, 212),  # 5-9 regolith
    (8, 8, 12),                                                         # 10 deep shadow
    (70, 140, 210),                                                     # 11 dome glass
    (58, 66, 84),                                                       # 12 base metal
    (255, 60, 60), (120, 255, 200),                                     # 13-14 lamps (blink)
    (232, 238, 248),                                                    # 15 markings, glints
]
RUN = [2, 3, 4]
REG = [5, 6, 7, 8, 9]
SH, DEEP, GLASS, METAL, LAMP_R, LAMP_G, MARK = 1, 10, 11, 12, 13, 14, 15

# Crater stamps: (size in tiles, variants).
CRATERS = ((1, 2), (2, 2), (3, 1))


def regolith(variant):
    """Gray dust, seamless, faintly speckled with pebbles."""
    n = _torus_noise(T, 8, 900 + variant) * 0.6 + _torus_noise(T, 4, 920 + variant) * 0.4
    yy, xx = np.mgrid[0:T, 0:T]
    t = np.full((T, T), REG[2], dtype=np.uint8)
    t[(n < 0.38) & ((xx + yy) % 2 == 0)] = REG[1]
    t[(n > 0.64) & ((xx + yy) % 2 == 0)] = REG[3]
    rng = np.random.default_rng(940 + variant)
    for _ in range(3):
        y, x = int(rng.integers(0, T - 1)), int(rng.integers(0, T - 1))
        t[y, x] = REG[4]
        t[y + 1, x + 1] = SH
    return t


def _ground(w, h, variant=0):
    """w x h tiles of regolith, as one image."""
    return np.tile(regolith(variant), (h, w))


def crater(size, seed):
    """A crater size tiles across over regolith: lit rim on the upper left,
    the bowl's upper-left wall in shadow, its lower-right wall lit."""
    n = size * T
    img = _ground(size, size)
    yy, xx = np.mgrid[0:n, 0:n]
    c = n / 2 - 0.5
    noise = value_noise(n, n, 3, 960 + seed)
    r = n / 2 - 1.5 - size * 0.5
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / r + (noise - 0.5) * 0.12
    # Light comes from the upper left: + toward it, - away.
    lit = ((c - xx) + (c - yy)) / (np.sqrt(2) * np.maximum(1.0, np.sqrt((xx - c) ** 2 + (yy - c) ** 2)))
    rim = (d > 0.82) & (d < 1.08)
    img[rim & (lit > 0.2)] = REG[4]
    img[rim & (lit > -0.3) & (lit <= 0.2)] = REG[3]
    img[rim & (lit <= -0.3)] = REG[1]
    bowl = d <= 0.82
    img[bowl] = REG[2]
    img[bowl & (lit > 0.1)] = SH       # the near wall, in its own shadow
    img[bowl & (lit > 0.45)] = DEEP
    img[bowl & (lit < -0.35)] = REG[3]  # the far wall, catching the light
    img[bowl & (d < 0.35)] = REG[1]
    img[bowl & (d < 0.35) & (lit < -0.2)] = REG[2]
    # Ejecta: bright flecks scattered round the rim.
    ej = (d > 1.08) & (d < 1.5) & (noise > 0.62) & ((xx + yy) % 3 == 0)
    img[ej] = REG[4]
    return [img[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(size) for x in range(size)]


def floor_tile(edges, variant):
    """Base floor plates, a 9-slice: edges (n, e, s, w) get a raised curb."""
    v = value_noise(T, T, 8, 980 + variant)
    t = np.full((T, T), METAL, dtype=np.uint8)
    t[v > 0.7] = REG[1]
    t[0, :] = REG[1]
    t[:, 0] = REG[1]
    t[8, :] = REG[0]
    t[:, 8] = REG[0]
    n_, e_, s_, w_ = edges
    if n_:
        t[0, :] = SH
        t[1, :] = REG[4]
    if w_:
        t[:, 0] = SH
        t[:, 1] = REG[4]
    if s_:
        t[T - 1, :] = SH
        t[T - 2, :] = REG[0]
    if e_:
        t[:, T - 1] = SH
        t[:, T - 2] = REG[0]
    return t


def dome():
    big = np.tile(floor_tile((0, 0, 0, 0), 0), (2, 2))
    yy, xx = np.mgrid[0:32, 0:32]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 14] = SH
    big[d < 13] = GLASS
    big[(d < 13) & ((xx + yy) % 2 == 0) & (xx + yy > 34)] = METAL
    big[(d < 13) & (xx + yy > 40)] = METAL
    for a in range(0, 32, 6):
        big[(np.abs(xx - a) < 0.6) & (d < 13)] = METAL
    big[(np.abs(d - 9) < 0.6) & (xx + yy < 30)] = MARK
    big[(d < 4) & (xx < 14) & (yy < 14)] = MARK
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def pad():
    """A landing pad: a ring of running lights round a marked circle."""
    big = np.tile(floor_tile((0, 0, 0, 0), 1), (2, 2))
    yy, xx = np.mgrid[0:32, 0:32]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 14] = REG[1]
    big[d < 12] = METAL
    big[np.abs(d - 10) < 0.7] = MARK
    ang = (np.degrees(np.arctan2(yy - 15.5, xx - 15.5)) + 360) % 360
    on = (np.abs(d - 13) < 0.8) & ((ang // 20).astype(int) % 2 == 0)
    big[on] = np.array(RUN)[((ang[on] // 40).astype(int)) % 3]
    # A big "H" marking.
    big[10:22, 11:13] = MARK
    big[10:22, 19:21] = MARK
    big[15:17, 11:21] = MARK
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def bunker():
    big = np.tile(floor_tile((0, 0, 0, 0), 2), (2, 2))
    yy, xx = np.mgrid[0:32, 0:32]
    sq = np.maximum(np.abs(xx - 15.5), np.abs(yy - 15.5))
    big[sq < 14] = REG[2]
    big[(sq < 14) & (sq >= 12.5) & (xx < yy)] = REG[0]
    big[(sq < 14) & (sq >= 12.5) & (xx >= yy)] = REG[4]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 10] = REG[1]
    big[d < 8] = DEEP
    big[d < 2.5] = LAMP_R
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def road(variant, plaza):
    """A rover road: packed dust between two rows of guide lights, or a
    metal roadway where it crosses a plaza."""
    t = floor_tile((0, 0, 0, 0), 3) if plaza else regolith(variant)
    t[2:14, :] = REG[1] if not plaza else REG[0]
    t[4:12, :] = REG[1]
    t[6, ::3] = REG[0]
    t[9, 1::3] = REG[0]
    t[1, :] = REG[3]
    t[14, :] = REG[0]
    t[1, (variant * 8):(variant * 8) + 2] = RUN[variant % 3]
    t[14, (variant * 8 + 4):(variant * 8) + 6] = RUN[(variant + 1) % 3]
    return t


def ground_tileset():
    tiles, ids = [], {}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"reg{k}", regolith(k))
    for size, variants in CRATERS:
        for v in range(variants):
            for k, t in enumerate(crater(size, size * 10 + v)):
                add(f"crater{size}_{v}_{k}", t)
    for e in range(16):
        add(f"floor{e}", floor_tile(((e >> 3) & 1, (e >> 2) & 1, (e >> 1) & 1, e & 1), e))
    for k, t in enumerate(dome()):
        add(f"dome{k}", t)
    for k, t in enumerate(pad()):
        add(f"pad{k}", t)
    for k, t in enumerate(bunker()):
        add(f"bunker{k}", t)
    for v in range(2):
        add(f"road{v}", road(v, False))
        add(f"roadp{v}", road(v, True))
    return tiles, ids


def ground_map(rows, ids, seed=7):
    """Stage order. Returns the map, bunkers (row, col) and road rows."""
    rng = np.random.default_rng(seed)
    m = np.array([[ids[f"reg{int(rng.integers(0, 4))}"] for _ in range(COLS)] for _ in range(rows)], dtype=np.uint8)
    used = np.zeros((rows, COLS), dtype=bool)
    bunkers, roads = [], []
    # Bases: plazas in three stretches of the stage.
    for r0 in (24, 74, 124):
        h = int(rng.integers(9, 13))
        c0 = int(rng.integers(0, 3))
        c1 = COLS - int(rng.integers(0, 3))
        for r in range(r0, r0 + h):
            for c in range(c0, c1):
                e = ((r == r0 + h - 1) << 3) | ((c == c1 - 1) << 2) | ((r == r0) << 1) | (c == c0)
                m[r, c] = ids[f"floor{e}"]
        used[r0 - 1:r0 + h + 1, max(0, c0 - 1):min(COLS, c1 + 1)] = True
        mid = r0 + h // 2
        for c in range(COLS):
            m[mid, c] = ids[f"roadp{c % 2}" if c0 <= c < c1 else f"road{c % 2}"]
        used[mid, :] = True
        roads.append(mid)
        # Fill the plaza with domes, pads and bunkers, two by two.
        spots = [(r, c) for r in range(r0 + 1, r0 + h - 2, 3) for c in range(c0 + 1, c1 - 2, 3)
                 if not (r <= mid <= r + 1)]
        rng.shuffle(spots)
        for k, (r, c) in enumerate(spots):
            kind = ["bunker", "dome", "bunker", "pad"][k % 4]
            # Stage order: the stamp's top row is r + 1.
            m[r + 1, c], m[r + 1, c + 1] = ids[f"{kind}0"], ids[f"{kind}1"]
            m[r, c], m[r, c + 1] = ids[f"{kind}2"], ids[f"{kind}3"]
            if kind == "bunker":
                bunkers.append((r, c))
    # Roads through the open ground between bases, for more rovers.
    for r in (42, 56, 94, 108, 146, 160):
        if r < rows and not used[r].any():
            for c in range(COLS):
                m[r, c] = ids[f"road{c % 2}"]
            used[r, :] = True
            roads.append(r)
    # Craters wherever there is room, the big ones first.
    for size, variants in reversed(CRATERS):
        tries = {3: 40, 2: 120, 1: 260}[size]
        for _ in range(tries):
            r, c = int(rng.integers(0, rows - size)), int(rng.integers(0, COLS - size + 1))
            if used[max(0, r - 1):r + size + 1, max(0, c - 1):c + size + 1].any():
                continue
            v = int(rng.integers(0, variants))
            for k in range(size * size):
                y, x = divmod(k, size)
                m[r + size - 1 - y, c + x] = ids[f"crater{size}_{v}_{k}"]
            used[r:r + size, c:c + size] = True
    # A few lone bunkers out on the plain, in crater-free spots.
    for _ in range(140):
        r, c = int(rng.integers(4, rows - 4)), int(rng.integers(0, COLS - 1))
        if not used[r - 1:r + 3, max(0, c - 1):c + 3].any() and rng.random() < 0.5:
            m[r + 1, c], m[r + 1, c + 1] = ids["bunker0"], ids["bunker1"]
            m[r, c], m[r, c + 1] = ids["bunker2"], ids["bunker3"]
            used[max(0, r - 3):r + 5, max(0, c - 2):c + 4] = True
            bunkers.append((r, c))
    return m, bunkers, roads


def stage7_ground(total_rows=208):
    tiles, ids = ground_tileset()
    body_rows = total_rows - 2 * LOOP_ROWS
    body, bunkers, roads = ground_map(body_rows, ids)
    # The loop: open regolith with a few small craters, seamless.
    rng = np.random.default_rng(77)
    loop = np.array([[ids[f"reg{int(rng.integers(0, 4))}"] for _ in range(COLS)] for _ in range(LOOP_ROWS)],
                    dtype=np.uint8)
    for _ in range(8):
        r, c = int(rng.integers(0, LOOP_ROWS)), int(rng.integers(0, COLS))
        loop[r, c] = ids[f"crater1_{int(rng.integers(0, 2))}_0"]
    stage = np.concatenate([body, loop, loop], axis=0)
    return tiles, stage[::-1].copy(), bunkers, roads
