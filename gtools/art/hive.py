"""Stage 8 boss, HIVE MOTHERSHIP: an alien mothership grown, not built.

The hull is a tile map (10 x 9 tiles, 160 x 144 pixels) on plane 1's
layer, palette HIVE: a carapace of honeycomb cells inside a lit shell,
its outline in marching squares, so the tiles are few. Some cells hold
amber, some glow; veins carry a pulse (the rotating entries 2-4) out from
the eye. Two mandibles reach forward. Sprites (palette BOSS8): the great
eye, which is the core, two spore pods that launch saucers, the mandibles'
pincers, and four turrets.
"""

import math

import numpy as np

from boss import MATS
from kit import BAYER4, Sprite, value_noise

T = 16
W, H = 10, 9

HIVE = [
    None,                                                               # 0 clear
    (10, 4, 14),                                                        # 1 outline
    (30, 120, 60), (100, 220, 90), (210, 255, 160),                     # 2-4 veins (rotate: pulse)
    (34, 18, 42), (58, 32, 70), (90, 54, 100), (130, 86, 136), (178, 134, 172),  # 5-9 chitin
    (14, 6, 18),                                                        # 10 shadow
    (210, 140, 40),                                                     # 11 amber
    (130, 24, 50),                                                      # 12 flesh
    (255, 70, 70), (120, 255, 140),                                     # 13-14 eyelets (blink)
    (226, 214, 190),                                                    # 15 bone
]
OUT, SH, AMBER, FLESH, EYE_R, EYE_G, BONE = 1, 10, 11, 12, 13, 14, 15
CHITIN = [5, 6, 7, 8, 9]
VEIN = [2, 3, 4]

BOSS8 = [
    None, (8, 4, 12),
    (40, 22, 50), (66, 38, 80), (100, 60, 112), (146, 96, 150), (196, 150, 190),  # 2-6 chitin
    (30, 100, 40), (80, 180, 70), (170, 245, 130),                               # 7-9 bio green
    (230, 40, 40), (255, 170, 60),                                               # 10-11 iris
    (14, 6, 16), (44, 20, 40),                                                   # 12-13 dark
    (140, 255, 200), (240, 236, 220),                                            # 14-15 glow, sclera
]
BOSS8_WRECK = [
    None, (6, 4, 8),
    (24, 18, 28), (36, 28, 40), (52, 42, 56), (72, 60, 74), (94, 82, 94),
    (24, 40, 26), (40, 60, 40), (60, 80, 56),
    (80, 30, 30), (100, 70, 40),
    (10, 6, 10), (24, 16, 24),
    (50, 80, 70), (100, 96, 90),
]

PARTS = {
    "EYE": (4, 3, 2, 2),
    "POD_L": (1, 2, 2, 2),
    "POD_R": (7, 2, 2, 2),
    "CLAW_L": (2, 6, 2, 2),
    "CLAW_R": (6, 6, 2, 2),
    "TUR0": (3, 1, 1, 1),
    "TUR1": (6, 1, 1, 1),
    "TUR2": (1, 5, 1, 1),
    "TUR3": (8, 5, 1, 1),
}


# ---- hull tiles -------------------------------------------------------------

def _comb():
    """Honeycomb across a tile, seamless: cell ids, and how far each pixel
    is from its cell's center (0 middle, 1 at the wall)."""
    pts = []
    for r in range(-1, 4):
        for c in range(-1, 4):
            pts.append((c * 8 + (4 if r % 2 else 0), r * 8))
    yy, xx = np.mgrid[0:T, 0:T]
    best = np.full((T, T), 1e9)
    second = np.full((T, T), 1e9)
    cell = np.zeros((T, T), dtype=int)
    for i, (px, py) in enumerate(pts):
        d = np.hypot(xx + 0.5 - px, (yy + 0.5 - py) * 1.1)
        closer = d < best
        second = np.where(closer, best, np.minimum(second, d))
        cell = np.where(closer, ((px // 8) % 2) * 2 + (py // 8) % 2 + 4 * ((px % 16) // 4), cell)
        best = np.minimum(best, d)
    wall = 1 - (second - best) / 3.0
    return cell, best, np.clip(wall, 0, 1)


CELL, CDIST, WALL = _comb()


def carapace(variant):
    """Full-interior hull: chitin cells, lit from the upper left, dark
    walls. Variants fill a cell with amber, open one dark, light one."""
    yy, xx = np.mgrid[0:T, 0:T]
    bay = BAYER4[yy % 4, xx % 4]
    n = value_noise(T, T, 4, 3000 + variant)
    # Each cell a low dome: brighter up and to the left of its middle.
    lit = 0.55 - (WALL * 0.5) + n * 0.25
    lvl = np.clip(np.round(lit * 4 + bay * 0.8), 0, 4).astype(int)
    t = np.array(CHITIN)[lvl]
    t[WALL > 0.72] = CHITIN[0]
    t[WALL > 0.9] = SH
    ids = sorted(set(CELL[CDIST < 2].tolist()))
    pick = ids[(variant * 3) % len(ids)]
    inner = (CELL == pick) & (WALL < 0.6)
    if variant == 1:
        t[inner] = AMBER
        t[inner & (WALL < 0.25) & (bay < 0)] = BONE
    elif variant == 2:
        t[inner] = SH
        t[inner & (WALL > 0.45)] = CHITIN[0]
    elif variant == 3:
        t[inner] = VEIN[1]
        t[inner & (WALL < 0.3)] = VEIN[2]
    return t


def _field(c):
    tl, tr, br, bl = c
    yy, xx = np.mgrid[0:T, 0:T]
    u, v = (xx + 0.5) / T, (yy + 0.5) / T
    f = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v
    # Its slope: the shell faces down it.
    fx = (tr - tl) * (1 - v) + (br - bl) * v
    fy = (bl - tl) * (1 - u) + (br - tr) * u
    return f, fx, fy


def edge(c):
    """A marching squares tile of the hull's rim (corners tl, tr, br, bl,
    screen order): the shell, a band lit on the side toward the upper left,
    over the honeycomb."""
    f, fx, fy = _field(c)
    yy, xx = np.mgrid[0:T, 0:T]
    bay = BAYER4[yy % 4, xx % 4]
    t = carapace(0)
    norm = np.hypot(fx, fy) + 1e-6
    # The outward normal is down the slope; light comes from the upper left.
    lit = (fx * 0.6 + fy * 0.8) / norm * 0.5 + 0.5
    shell = f < 0.68
    lvl = np.clip(np.round(lit * 4 + bay * 0.8), 0, 4).astype(int)
    t[shell] = np.array(CHITIN)[lvl[shell]]
    t[(f >= 0.66) & (f < 0.72)] = SH
    t[f < 0.5] = 0
    out = (f < 0.5) & (f > 0.42)
    t[out] = OUT
    return t


def _vein(t, horizontal):
    """A vein across a tile, its pulse running along it."""
    t = t.copy()
    yy, xx = np.mgrid[0:T, 0:T]
    a = (yy if horizontal else xx) + 0.5 - T / 2
    along = xx if horizontal else yy
    wob = np.sin(along / 16 * 2 * math.pi) * 1.5
    d = np.abs(a - wob)
    t[d < 3] = SH
    t[d < 2] = np.array(VEIN)[(along // 3) % 3][d < 2]
    t[(d < 2) & (d >= 1.2)] = VEIN[0]
    return t


def _socket(size, base):
    """A fleshy ring the part grows from, over size x size tiles of base."""
    n = size * T
    big = base.copy()
    yy, xx = np.mgrid[0:n, 0:n]
    c = n / 2 - 0.5
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    r = n / 2 - 1
    big[d < r] = BONE
    big[(d < r) & (xx + yy >= 2 * c)] = CHITIN[2]
    big[d < r - 1.5] = FLESH
    big[d < r - 3.5] = SH
    big[d >= r] = np.where(d[d >= r] < r + 1, OUT, big[d >= r])
    return big


def _crater(size, seed):
    n = size * T
    big = np.concatenate([np.concatenate([carapace(2 if (x + y) % 2 else 0) for x in range(size)], axis=1)
                          for y in range(size)], axis=0)
    yy, xx = np.mgrid[0:n, 0:n]
    c = n / 2 - 0.5
    noise = value_noise(n, n, 3, 3100 + seed)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / (n / 2) + (noise - 0.5) * 0.5
    big[d < 0.95] = CHITIN[0]
    big[d < 0.75] = SH
    big[d < 0.5] = OUT
    big[(d < 0.6) & (noise > 0.6)] = FLESH
    big[(d < 0.4) & (noise > 0.66)] = AMBER
    return [big[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(size) for x in range(size)]


def _maw():
    """The launch maw between the mandibles, 2 x 1 tiles: a dark throat
    ringed with bone teeth."""
    n = 2 * T
    big = np.concatenate([carapace(0), carapace(2)], axis=1)
    yy, xx = np.mgrid[0:T, 0:n]
    d = np.sqrt(((xx - n / 2 + 0.5) / 13) ** 2 + ((yy - 6) / 8) ** 2)
    big[d < 1] = FLESH
    big[d < 0.75] = SH
    big[d < 0.5] = OUT
    teeth = (d >= 0.72) & (d < 0.98) & ((xx // 3) % 2 == 0) & (yy > 4)
    big[teeth] = BONE
    return [big[:, :T], big[:, T:]]


def shape():
    """The hull's corners, (H + 1) x (W + 1), screen order: an oval, and the
    mandibles reaching down past it."""
    g = np.zeros((H + 1, W + 1), dtype=np.uint8)
    for y in range(H + 1):
        for x in range(W + 1):
            if ((x - 5) / 5.3) ** 2 + ((y - 4.0) / 4.4) ** 2 < 1:
                g[y, x] = 1
    for x0 in (2, 6):
        g[5:9, x0:x0 + 3] = 1
    g[9, 3], g[9, 7] = 1, 1
    return g


def hull():
    """The tiles, their ids and the 10 x 9 map."""
    tiles, ids, seen = [np.zeros((T, T), dtype=np.uint8)], {}, {bytes(T * T): 0}

    def add(t):
        b = t.tobytes()
        if b not in seen:
            seen[b] = len(tiles)
            tiles.append(t)
        return seen[b]

    g = shape()
    rng = np.random.default_rng(8)
    m = np.zeros((H, W), dtype=np.uint8)
    for r in range(H):
        for c in range(W):
            cfg = (int(g[r, c]), int(g[r, c + 1]), int(g[r + 1, c + 1]), int(g[r + 1, c]))
            if cfg == (1, 1, 1, 1):
                m[r, c] = add(carapace(int(rng.choice(4, p=[0.55, 0.17, 0.14, 0.14]))))
            elif any(cfg):
                m[r, c] = add(edge(cfg))
    # Veins out from the eye: along row 4 to the pods' sides, up its column.
    for c in (1, 2, 3, 6, 7, 8):
        if g[4, c] and g[5, c] and g[4, c + 1] and g[5, c + 1]:
            m[4, c] = add(_vein(carapace(0), True))
    for r in (0, 1, 2):
        for c in (4, 5):
            cfg = (int(g[r, c]), int(g[r, c + 1]), int(g[r + 1, c + 1]), int(g[r + 1, c]))
            if cfg == (1, 1, 1, 1):
                m[r, c] = add(_vein(carapace(0), False))
    maw = _maw()
    m[7, 4], m[7, 5] = add(maw[0]), add(maw[1])
    # Sockets, all on plain carapace so each size is one set of tiles.
    base1 = carapace(0)
    base2 = np.concatenate([np.concatenate([base1, base1], axis=1)] * 2, axis=0)
    big = _socket(2, base2)
    big_ids = [add(big[y * T:(y + 1) * T, x * T:(x + 1) * T].copy()) for y in range(2) for x in range(2)]
    small = add(_socket(1, base1))
    for name, (c, r, w, h) in PARTS.items():
        if w == 2:
            for k in range(4):
                m[r + k // 2, c + k % 2] = big_ids[k]
        else:
            m[r, c] = small
    ids["crater_big0"] = len(tiles)
    tiles += _crater(2, 1)
    ids["crater"] = len(tiles)
    tiles += _crater(1, 2)
    return tiles, ids, m


# ---- sprites (palette BOSS8) -------------------------------------------------

def eye():
    """32x32 great eye, the core: chitin lids round a red iris and a slit
    pupil. Frames: watching, and glaring as it fires."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        s.ellipse((2.0, 3.5, 30.0, 28.5), "armor", amp=2.4)
        s.ellipse((5, 8, 27, 24), "vent", z=1.5, amp=0.4, profile="flat")
        img = s.render(MATS, gloss=0.3)
        yy, xx = np.mgrid[0:32, 0:32]
        x, y = xx - 15.5, yy - 15.5
        ball = (x / 10.0) ** 2 + (y / 7.2) ** 2 < 1
        img[ball] = 15
        img[ball & (x + y > 7)] = 6
        iris = x ** 2 + y ** 2 < (6.5 if hot else 5.5) ** 2
        img[iris & ball] = 11 if hot else 10
        img[iris & ball & (x ** 2 + y ** 2 < 3 ** 2) & hot] = 15
        slit = (np.abs(x) < (1.0 if hot else 1.6)) & (np.abs(y) < 5) & ball
        img[slit] = 12
        img[(x + 3.5) ** 2 + (y + 3) ** 2 < 1.5] = 15
        out.append(img)
    return out


def pod():
    """32x32 spore pod: a ribbed sac with a glow inside. Frames: pulse."""
    out = []
    for big in (False, True):
        s = Sprite(32, 32)
        s.ellipse((3, 2, 29, 30), "armor", amp=2.2)
        g = 3 if big else 5
        s.ellipse((3 + g, 2 + g, 29 - g, 30 - g), "gold", z=1.6, amp=2)
        for a in range(0, 180, 45):
            r = math.radians(a)
            s.line((16 - math.cos(r) * 12, 16 - math.sin(r) * 13), (16 + math.cos(r) * 12, 16 + math.sin(r) * 13),
                   "armor", width=1.6, z=3, amp=0.6)
        s.ellipse((12, 12, 20, 20), "light" if big else "gold", z=4)
        out.append(s.render(MATS, gloss=0.35))
    return out


def claw():
    """32x32 mandible pair, reaching down and curving in. Frames: open,
    closing."""
    out = []
    for k in range(2):
        s = Sprite(32, 32)
        for side in (-1, 1):
            left, right = [], []
            for i in range(9):
                t = i / 8
                x = 16 + side * (9.5 + 2 * t - (7 + k * 2) * t * t)
                y = 4.5 + 25 * t
                w = 2.8 * (1 - t) + 0.7
                left.append((x - w, y))
                right.append((x + w, y))
            s.poly(left + right[::-1], "armor", z=1, amp=1.8, bevel=2)
        s.ellipse((7.5, 2.5, 24.5, 14.5), "armor", z=2, amp=2.2)
        s.ellipse((12, 5.0, 20, 12.0), "core" if k else "corehot", z=3.5)
        img = s.render(MATS, gloss=0.35)
        out.append(img)
    return out


_HALF_PORTRAIT = [
    "........",  # 0: margin
    "....1111",  # 1: top brow arch
    "..116554",  # 2: chitin brow ridge
    ".1654311",  # 3: upper eyelid fold
    ".163ffba",  # 4: sclera + upper iris
    ".15ffbba",  # 5: sclera + iris
    ".15ffbac",  # 6: sclera + iris + slit pupil
    ".15ffbac",  # 7: eye center
    ".15ffbac",  # 8: lower eye center
    ".163ffba",  # 9: lower iris
    ".1654311",  # 10: lower eyelid fold
    "..165431",  # 11: lower carapace rim
    "..116541",  # 12: mandible mount
    "...11541",  # 13: mandible tip
    "....1111",  # 14: bottom outline closure
    "........",  # 15: margin
]


def _parse_frames(art_list, fw, fh):
    frames = []
    for rows in art_list:
        f = np.zeros((fh, fw), dtype=np.uint8)
        assert len(rows) == fh, f"bad h: {len(rows)} != {fh}"
        for y, row in enumerate(rows):
            assert len(row) == fw, f"bad w at row {y}: {len(row)} != {fw}"
            for x, ch in enumerate(row):
                if ch != ".":
                    f[y, x] = int(ch, 16)
        frames.append(f)
    return frames


def portrait():
    """16x16 HUD portrait of Hive Mothership."""
    return _parse_frames([[r + "".join(reversed(r)) for r in _HALF_PORTRAIT]], 16, 16)
