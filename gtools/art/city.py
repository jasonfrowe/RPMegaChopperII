"""Stage 2, NEON SPIRES: a city at night, and a parallax sky over it.

Ground (plane 0, palette CITY): blocks of rooftops between roads. Horizontal
roads run every BLOCK rows, so the map is periodic and its top loops
without a seam. Lane lights on the roads use the rotating entries 2-4,
so traffic seems to stream along them. Tanks drive on the horizontal roads,
turrets sit on rooftop pads.

Sky (plane 1, palette SKY): tall towers and clouds, scrolling faster than
the ground because they are nearer. A tower is its roof, its lit south
face and a dithered shadow; the roof and face are solid, and the ship
crashes into them. Clouds are only scenery. The sky's last rows are
empty, so once it stops scrolling the boss has a clear sky.
"""

import math

import numpy as np

from kit import BAYER4, value_noise

T = 16
COLS = 12
BLOCK = 8          # rows from one horizontal road to the next
LOOP_ROWS = 16     # two blocks

CITY = [
    (4, 6, 16),                                                         # 0 backdrop (opaque)
    (22, 24, 38),                                                       # 1 asphalt
    (40, 120, 220), (120, 220, 255), (240, 250, 255),                   # 2-4 traffic lights (rotate)
    (30, 28, 48), (50, 46, 74), (78, 72, 106), (112, 104, 144), (160, 152, 196),  # 5-9 roofs
    (10, 8, 20),                                                        # 10 shadow
    (210, 50, 170), (255, 170, 40),                                     # 11-12 neon magenta, amber
    (255, 60, 60), (90, 255, 160),                                      # 13-14 lamps (blink)
    (255, 226, 150),                                                    # 15 lit windows
]
ASPHALT, SHADOW, NEON, AMBER, LAMP_R, LAMP_G, WIN = 1, 10, 11, 12, 13, 14, 15
LANE = [2, 3, 4]
ROOF = [5, 6, 7, 8, 9]

SKY = [
    None,                                                               # 0 clear
    (8, 6, 18),                                                         # 1 outline
    (40, 170, 255), (150, 230, 255), (255, 255, 255),                   # 2-4 window bands (rotate)
    (36, 36, 60), (60, 62, 92), (92, 96, 132), (136, 142, 178), (196, 202, 228),  # 5-9 tower metal
    (4, 2, 12),                                                         # 10 shadow (dithered)
    (240, 190, 40),                                                     # 11 hazard
    (128, 136, 168),                                                    # 12 cloud shade
    (255, 50, 50), (255, 150, 40),                                      # 13-14 beacons (blink)
    (226, 232, 248),                                                    # 15 cloud
]
OUT, SH, HAZ, CLOUD_D, BEACON, BEACON2, CLOUD = 1, 10, 11, 12, 13, 14, 15
METAL = [5, 6, 7, 8, 9]
BAND = [2, 3, 4]


# ---- ground tiles ---------------------------------------------------------

def _noise(seed, cell=4):
    return value_noise(T, T, cell, seed)


def road_h(variant):
    t = np.full((T, T), ASPHALT, dtype=np.uint8)
    n = _noise(300 + variant)
    t[n > 0.75] = SHADOW
    t[0, :] = ROOF[0]
    t[T - 1, :] = SHADOW
    # Lane lights: a dashed band whose colours rotate, so they stream.
    for x in range(T):
        t[7, x] = LANE[(x // 2 + variant) % 3]
        t[8, x] = LANE[(x // 2 + variant + 1) % 3] if x % 4 < 2 else ASPHALT
    return t


def road_v(variant):
    t = np.full((T, T), ASPHALT, dtype=np.uint8)
    n = _noise(320 + variant)
    t[n > 0.75] = SHADOW
    t[:, 0] = ROOF[0]
    t[:, T - 1] = SHADOW
    for y in range(T):
        t[y, 7] = LANE[(y // 2 + variant) % 3]
    return t


def crossing():
    t = np.full((T, T), ASPHALT, dtype=np.uint8)
    yy, xx = np.mgrid[0:T, 0:T]
    t[((xx + yy) % 6 == 0)] = SHADOW
    for k in range(2, T - 2, 3):
        t[1, k:k + 2] = ROOF[3]
        t[T - 2, k:k + 2] = ROOF[3]
        t[k:k + 2, 1] = ROOF[3]
        t[k:k + 2, T - 2] = ROOF[3]
    t[6:10, 6:10] = AMBER
    t[7:9, 7:9] = LAMP_R
    return t


def roof_tile(edges, style, variant):
    """A rooftop tile. edges: which sides are the building's edge (n, e, s, w)."""
    n_, e_, s_, w_ = edges
    n = _noise(400 + variant * 7 + style * 31, 8)
    t = np.full((T, T), ROOF[2], dtype=np.uint8)
    t[n > 0.72] = ROOF[3]
    t[n < 0.22] = ROOF[1]
    t[7, :] = ROOF[1]  # roof panel seams
    t[:, 7] = ROOF[1]
    if style == 1:  # glass roof: a grid of panes, some lit
        t[:] = ROOF[1]
        rng = np.random.default_rng(500 + variant)
        for y in range(1, T, 4):
            for x in range(1, T, 4):
                t[y:y + 3, x:x + 3] = WIN if rng.random() < 0.35 else ROOF[0]
    elif style == 2:  # machinery: AC units and vents
        rng = np.random.default_rng(600 + variant)
        for _ in range(2):
            x, y = int(rng.integers(2, 9)), int(rng.integers(2, 9))
            t[y:y + 5, x:x + 5] = ROOF[3]
            t[y + 1:y + 4, x + 1:x + 4] = ROOF[1]
            t[y + 2, x + 1:x + 4] = SHADOW
            t[y + 5, x + 1:x + 6] = SHADOW
            t[y + 1:y + 6, x + 5] = SHADOW
    # Parapet: lit on the north and west, dark on the south and east, with
    # a neon trim on the street side.
    if n_:
        t[0, :] = ROOF[4]
        t[1, :] = NEON if variant % 2 else ROOF[3]
    if w_:
        t[:, 0] = ROOF[4]
        t[:, 1] = ROOF[3]
    if s_:
        t[T - 1, :] = SHADOW
        t[T - 2, :] = ROOF[0]
        t[T - 3, 2:T - 2:3] = AMBER  # street-facing signs
    if e_:
        t[:, T - 1] = SHADOW
        t[:, T - 2] = ROOF[0]
    if n_ and w_:
        t[2:4, 2:4] = LAMP_R
    if n_ and e_:
        t[2:4, T - 4:T - 2] = LAMP_G
    return t


def pad_tiles():
    """A 2x2 rooftop gun pad for a turret, TL TR BL BR."""
    big = np.full((32, 32), ROOF[2], dtype=np.uint8)
    yy, xx = np.mgrid[0:32, 0:32]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[d < 14] = ROOF[1]
    big[(d < 14) & (d > 12)] = AMBER
    big[(d < 13) & (d > 12) & (((xx + yy) // 3) % 2 == 0)] = SHADOW
    big[d < 10] = ROOF[3]
    big[d < 7] = ROOF[0]
    big[(np.abs(xx - 15.5) < 1) | (np.abs(yy - 15.5) < 1)] = ROOF[4]
    big[d < 3] = LAMP_R
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def helipad_tiles():
    big = np.full((32, 32), ROOF[1], dtype=np.uint8)
    yy, xx = np.mgrid[0:32, 0:32]
    d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
    big[(d < 13) & (d > 11)] = ROOF[4]
    hx = (np.abs(xx - 15.5) < 6) & (np.abs(yy - 15.5) < 7)
    h = hx & ((np.abs(xx - 10.5) < 1.5) | (np.abs(xx - 20.5) < 1.5) | (np.abs(yy - 15.5) < 1.2))
    big[h] = AMBER
    for a in range(0, 360, 45):
        x, y = 15.5 + 14.5 * math.cos(math.radians(a)), 15.5 + 14.5 * math.sin(math.radians(a))
        big[int(y), int(x)] = LAMP_G
    big[0, :] = ROOF[4]
    big[:, 0] = ROOF[4]
    big[31, :] = SHADOW
    big[:, 31] = SHADOW
    return [big[0:16, 0:16], big[0:16, 16:32], big[16:32, 0:16], big[16:32, 16:32]]


def ground_tileset():
    tiles, ids = [], {}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for v in range(3):
        add(f"rh{v}", road_h(v))
    for v in range(2):
        add(f"rv{v}", road_v(v))
    add("cross", crossing())
    for style in range(3):
        for e in range(16):
            edges = ((e >> 3) & 1, (e >> 2) & 1, (e >> 1) & 1, e & 1)
            add(f"roof{style}_{e}", roof_tile(edges, style, e % 3))
    for k, t in enumerate(pad_tiles()):
        add(f"pad{k}", t)
    for k, t in enumerate(helipad_tiles()):
        add(f"heli{k}", t)
    return tiles, ids


def _band_columns(band):
    """Vertical road columns for a block band, varying the districts."""
    sets = [(0, 6), (3, 9), (5,), (2, 7), (0, 4, 8), (6,), (3, 8), (1, 7)]
    return sets[band % len(sets)]


def ground_map(rows, ids, seed=3):
    """Stage order (row 0 = first seen). Returns map, turret pads, tank roads."""
    rng = np.random.default_rng(seed)
    m = np.zeros((rows, COLS), dtype=np.uint8)
    pads, roads = [], []
    for band in range(rows // BLOCK):
        r0 = band * BLOCK
        vcols = _band_columns(band)
        # Road along the band's first row, then a block of buildings.
        for c in range(COLS):
            m[r0, c] = ids["cross"] if c in vcols else ids[f"rh{(c + band) % 3}"]
        roads.append(r0)
        edges = [-1] + list(vcols) + [COLS]
        for a, b in zip(edges, edges[1:]):
            x0, x1 = a + 1, b - 1
            if x1 < x0:
                continue
            # Split tall blocks into two buildings now and then.
            splits = [r0 + 1, r0 + BLOCK]
            if rng.random() < 0.4:
                splits = [r0 + 1, r0 + 1 + int(rng.integers(2, 6)), r0 + BLOCK]
            for y0, y1 in zip(splits, splits[1:]):
                style = int(rng.integers(0, 3))
                for r in range(y0, y1):
                    for c in range(x0, x1 + 1):
                        # Stage order runs bottom-up: the building's north edge is its last row.
                        e = ((r == y1 - 1) << 3) | ((c == x1) << 2) | ((r == y0) << 1) | (c == x0)
                        m[r, c] = ids[f"roof{style}_{e}"]
                # A gun pad or a helipad on a big enough roof.
                if x1 - x0 >= 2 and y1 - y0 >= 3:
                    roll = rng.random()
                    cx, cy = x0 + 1 + int(rng.integers(0, x1 - x0 - 1)), y0 + 1
                    if roll < 0.45:
                        m[cy + 1, cx], m[cy + 1, cx + 1] = ids["pad0"], ids["pad1"]
                        m[cy, cx], m[cy, cx + 1] = ids["pad2"], ids["pad3"]
                        pads.append((cy, cx))
                    elif roll < 0.6:
                        m[cy + 1, cx], m[cy + 1, cx + 1] = ids["heli0"], ids["heli1"]
                        m[cy, cx], m[cy, cx + 1] = ids["heli2"], ids["heli3"]
        for c in vcols:
            for r in range(r0 + 1, r0 + BLOCK):
                m[r, c] = ids[f"rv{(r + c) % 2}"]
    return m, pads, roads


def stage2_ground(total_rows=208):
    tiles, ids = ground_tileset()
    body_rows = total_rows - 2 * LOOP_ROWS
    body, pads, roads = ground_map(body_rows, ids)
    loop, _, _ = ground_map(LOOP_ROWS, ids, seed=11)
    stage = np.concatenate([body, loop, loop], axis=0)
    return tiles, stage[::-1].copy(), pads, roads, body_rows


# ---- sky tiles ------------------------------------------------------------

def _dither_mask(alpha, seed=0):
    """Ordered dither of a 0-1 coverage into a boolean mask."""
    yy, xx = np.mgrid[0:alpha.shape[0], 0:alpha.shape[1]]
    return alpha > (BAYER4[(yy + seed) % 4, (xx + seed) % 4] + 0.5)


def cloud_tile(c, variant=0):
    """Marching squares cloud tile, corners (tl, tr, br, bl), soft dithered rim."""
    tl, tr, br, bl = c
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T
    f = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v
    n = value_noise(T, T, 4, 700 + variant) * 0.35
    a = np.clip((f + n - 0.35) * 2.6, 0, 1)
    t = np.zeros((T, T), dtype=np.uint8)
    body = _dither_mask(a, variant)
    t[body] = CLOUD
    # Shade the underside (south) and the eastern edges a little.
    shade = body & ((f + n) < 0.75) & (((xx + yy) % 2) == 0)
    t[shade] = CLOUD_D
    return t


def tower_tiles():
    """Tower vocabulary: roof 9-slice, south face, shadow; plus roof details."""
    out = {}
    base = np.full((T, T), METAL[2], dtype=np.uint8)
    yy, xx = np.mgrid[0:T, 0:T]

    def roof(n_, e_, s_, w_, detail=None):
        t = base.copy()
        t[((xx // 4 + yy // 4) % 2 == 0) & (((xx + yy) % 4) == 0)] = METAL[1]
        if n_:
            t[0, :] = OUT
            t[1, :] = METAL[4]
            t[2, :] = HAZ
            t[2, ::4] = OUT
        if w_:
            t[:, 0] = OUT
            t[:, 1] = METAL[4]
        if s_:
            t[T - 1, :] = METAL[0]
            t[T - 2, :] = METAL[1]
        if e_:
            t[:, T - 1] = OUT
            t[:, T - 2] = METAL[0]
        if n_ and w_:
            t[3:5, 3:5] = BEACON
        if n_ and e_:
            t[3:5, T - 5:T - 3] = BEACON
        if detail == "antenna":
            t[4:12, 7:9] = METAL[4]
            t[4:12, 9] = METAL[0]
            t[3:5, 6:10] = BEACON2
        elif detail == "vent":
            t[4:12, 4:12] = METAL[0]
            t[5:11:2, 5:11] = METAL[3]
        elif detail == "core":
            d = np.sqrt((xx - 7.5) ** 2 + (yy - 7.5) ** 2)
            t[d < 6] = METAL[1]
            t[d < 4] = BAND[1]
            t[d < 2] = BAND[2]
        return t

    for e in range(16):
        n_, e_, s_, w_ = (e >> 3) & 1, (e >> 2) & 1, (e >> 1) & 1, e & 1
        out[f"roof{e}"] = roof(n_, e_, s_, w_)
    out["roof_antenna"] = roof(0, 0, 0, 0, "antenna")
    out["roof_vent"] = roof(0, 0, 0, 0, "vent")
    out["roof_core"] = roof(0, 0, 0, 0, "core")

    # South face, two tiles tall: lit window bands that rotate (upper), and
    # a darker base with a hazard band where it meets the street (lower).
    for k, side in enumerate(("_w", "", "_e")):
        up = np.full((T, T), METAL[1], dtype=np.uint8)
        up[0, :] = METAL[0]
        for y in range(2, T, 4):
            for x in range(1, T, 3):
                up[y:y + 2, x:x + 2] = BAND[(x // 3 + y // 4) % 3]
        lo = np.full((T, T), METAL[0], dtype=np.uint8)
        for y in range(1, 9, 4):
            for x in range(1, T, 3):
                lo[y:y + 2, x:x + 2] = BAND[(x // 3 + y // 4 + 1) % 3]
        lo[11:13, :] = HAZ
        lo[11:13, ::4] = OUT
        lo[T - 1, :] = OUT
        for t in (up, lo):
            if k == 0:
                t[:, 0] = OUT
                t[:, 1] = METAL[2]
            if k == 2:
                t[:, T - 1] = OUT
        out["face" + side] = up
        out["base" + side] = lo

    # Shadows: a dither of SH, cast to the east and south.
    sh = np.zeros((T, T), dtype=np.uint8)
    sh[((xx + yy) % 2) == 0] = SH
    out["shadow"] = sh
    corner = np.zeros((T, T), dtype=np.uint8)
    corner[(((xx + yy) % 2) == 0) & (xx < T - yy)] = SH
    out["shadow_corner"] = corner
    top = np.zeros((T, T), dtype=np.uint8)
    top[(((xx + yy) % 2) == 0) & (yy >= 6)] = SH
    out["shadow_top"] = top
    left = np.zeros((T, T), dtype=np.uint8)
    left[(((xx + yy) % 2) == 0) & (xx >= 6)] = SH
    out["shadow_left"] = left
    return out


def sky_tileset():
    tiles, ids, solid = [np.zeros((T, T), dtype=np.uint8)], {"clear": 0}, set()

    def add(name, t, is_solid=False):
        ids[name] = len(tiles)
        tiles.append(t)
        if is_solid:
            solid.add(ids[name])

    for cfg in range(1, 16):
        c = ((cfg >> 3) & 1, (cfg >> 2) & 1, (cfg >> 1) & 1, cfg & 1)
        add(f"cloud{cfg}", cloud_tile(c, cfg))
    add("cloud15b", cloud_tile((1, 1, 1, 1), 31))
    for name, t in tower_tiles().items():
        add(name, t, name.startswith(("roof", "face", "base")))
    return tiles, ids, solid


def _place_tower(sky, ids, r, c, w, h, rng):
    """A tower whose roof covers rows r..r+h-1 (stage order, r = south) and
    columns c..c+w-1, with its face below and its shadow to the east/south."""
    rows, cols = sky.shape
    for y in range(h):
        for x in range(w):
            rr, cc = r + y, c + x
            # Stage order is bottom-up: the roof's north edge is its top row.
            e = ((y == h - 1) << 3) | ((x == w - 1) << 2) | ((y == 0) << 1) | (x == 0)
            name = f"roof{e}"
            if e == 0 and rng.random() < 0.5:
                name = ["roof_antenna", "roof_vent", "roof_core"][int(rng.integers(0, 3))]
            sky[rr, cc] = ids[name]
    for x in range(w):
        side = "_w" if x == 0 else "_e" if x == w - 1 else ""
        sky[r - 1, c + x] = ids["face" + side]
        sky[r - 2, c + x] = ids["base" + side]
    # Shadow: one column east (beside the roof and face), one row south of the base.
    if c + w < cols:
        sky[r + h - 1, c + w] = ids["shadow_top"]
        for y in range(-2, h - 1):
            sky[r + y, c + w] = ids["shadow"]
        sky[r - 3, c + w] = ids["shadow_corner"]
    for x in range(w):
        sky[r - 3, c + x] = ids["shadow_left"] if x == 0 else ids["shadow"]


def _place_cloud(corners, r, c, w, h, rng):
    rows, cols = corners.shape
    cy, cx = r + h / 2, c + w / 2
    for y in range(max(0, r - 1), min(rows, r + h + 2)):
        for x in range(max(0, c - 1), min(cols, c + w + 2)):
            d = ((y - cy) / (h / 2 + 0.5)) ** 2 + ((x - cx) / (w / 2 + 0.5)) ** 2
            if d < 1.0 - rng.random() * 0.25:
                corners[y, x] = 1


def sky_map(rows, ids, intro_rows=18, tail_rows=17, seed=5):
    """Stage order. Towers come in lanes with room to dodge between them."""
    rng = np.random.default_rng(seed)
    sky = np.zeros((rows, COLS), dtype=np.uint8)
    corners = np.zeros((rows + 1, COLS + 1), dtype=np.uint8)
    end = rows - tail_rows
    r = intro_rows
    side = 0
    towers = []
    while r < end - 8:
        w = int(rng.integers(2, 5))
        h = int(rng.integers(2, 4))
        # Swing between the left, middle and right, with an occasional pair
        # that leaves only the middle open. There is always a way through.
        if rng.random() < 0.2 and r < end - 12:
            w = min(w, 3)
            spots = [0, COLS - w - 1]
        else:
            lane = (side + int(rng.integers(1, 3))) % 3
            side = lane
            right = COLS - w - 1
            mid = right // 2
            lo, hi = [(0, 1), (mid - 1, mid + 1), (right - 1, right)][lane]
            spots = [int(rng.integers(lo, hi + 1))]
        for c in spots:
            _place_tower(sky, ids, r + 3, c, w, h, rng)
            towers.append((r + 3, c, w, h))
        r += h + 4 + int(rng.integers(1, 5))
    # Clouds drift in the gaps, clear of the towers.
    used = sky != 0
    r = intro_rows
    while r < end - 6:
        cw, ch = int(rng.integers(3, 6)), int(rng.integers(2, 4))
        cc = int(rng.integers(0, COLS - cw))
        if not used[max(0, r - 2):r + ch + 3, max(0, cc - 2):cc + cw + 3].any():
            _place_cloud(corners, r, cc, cw, ch, rng)
            used[r:r + ch + 1, cc:cc + cw + 1] = True
            r += ch + int(rng.integers(4, 9))
        else:
            r += 1
    # Clouds become tiles where nothing else is.
    for y in range(rows):
        for x in range(COLS):
            if sky[y, x]:
                continue
            tl, tr = corners[y + 1, x], corners[y + 1, x + 1]
            bl, br = corners[y, x], corners[y, x + 1]
            cfg = (tl << 3) | (tr << 2) | (br << 1) | bl
            if cfg == 15 and (x + y) % 3 == 0:
                sky[y, x] = ids["cloud15b"]
            elif cfg:
                sky[y, x] = ids[f"cloud{cfg}"]
    sky[end:, :] = 0
    return sky, towers


def stage2_sky(rows):
    tiles, ids, solid = sky_tileset()
    sky, towers = sky_map(rows, ids)
    return tiles, sky[::-1].copy(), solid, towers
