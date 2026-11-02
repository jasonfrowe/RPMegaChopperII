"""Stage 5 boss, GLACIER CRAWLER: a tracked fortress grinding across the ice.

Like stage 3's battleship, the hull is a tile map (10 x 9 tiles, 160 x 144
pixels) on plane 1's layer, palette HULL5, so it costs no sprite time. Its
treads are drawn in the rotating entries 2-4, so they run on their own.
Guns, the drill and the reactor are sprites on top (palette BOSS5); the
launch hatches are hull tiles. Destroyed parts leave craters.

The drill points down the screen, at the player; row 0 is the rear.
"""

import math

import numpy as np

from boss import MATS
from kit import Sprite, value_noise

T = 16
W, H = 10, 9

HULL5 = [
    None,                                                               # 0 clear
    (6, 10, 18),                                                        # 1 outline
    (40, 44, 56), (78, 84, 100), (130, 138, 156),                       # 2-4 tread cleats (rotate)
    (40, 52, 70), (64, 80, 104), (96, 114, 140), (140, 158, 184), (196, 210, 228),  # 5-9 cold steel
    (12, 16, 26),                                                       # 10 shadow
    (230, 170, 30),                                                     # 11 hazard
    (40, 120, 170),                                                     # 12 paint
    (255, 50, 50), (80, 255, 160),                                      # 13-14 lamps (blink)
    (210, 236, 250),                                                    # 15 frost
]
OUT, SH, HAZ, PAINT, LAMP_R, LAMP_G, FROSTC = 1, 10, 11, 12, 13, 14, 15
STEEL = [5, 6, 7, 8, 9]
CLEAT = [2, 3, 4]

BOSS5 = [
    None, (6, 10, 18),
    (40, 52, 70), (64, 80, 104), (96, 114, 140), (140, 158, 184), (200, 214, 232),  # 2-6 armour
    (20, 90, 140), (40, 140, 200), (130, 210, 250),                                # 7-9 paint
    (90, 220, 255), (220, 250, 255),                                               # 10-11 cryo core
    (12, 16, 26), (32, 40, 56),                                                    # 12-13 vents
    (255, 200, 60), (255, 250, 220),                                               # 14-15 lights
]
BOSS5_WRECK = [
    None, (6, 6, 8),
    (24, 24, 28), (38, 38, 42), (56, 54, 58), (78, 74, 76), (102, 96, 96),
    (24, 36, 44), (40, 54, 62), (66, 80, 86),
    (40, 70, 80), (90, 110, 116),
    (10, 10, 12), (24, 22, 26),
    (70, 50, 30), (100, 80, 60),
]

# Where each part sits: tile column and row of its top left, size in tiles.
PARTS = {
    "REACTOR": (4, 1, 2, 2),
    "GUN_L": (2, 4, 2, 2),
    "GUN_R": (6, 4, 2, 2),
    "HATCH_L": (4, 4, 1, 2),
    "HATCH_R": (5, 4, 1, 2),
    "TUR0": (2, 1, 1, 1),
    "TUR1": (7, 1, 1, 1),
    "TUR2": (2, 7, 1, 1),
    "TUR3": (7, 7, 1, 1),
    "DRILL": (4, 7, 2, 2),
}


def _deck(seed, seams=True):
    n = value_noise(T, T, 8, 2200 + seed)
    t = np.full((T, T), STEEL[2], dtype=np.uint8)
    t[n > 0.7] = STEEL[3]
    t[n < 0.26] = STEEL[1]
    t[(n > 0.82)] = FROSTC
    if seams:
        t[0, :] = STEEL[3]
        t[:, 0] = STEEL[3]
        t[T - 1, :] = STEEL[0]
        t[:, T - 1] = STEEL[0]
    return t


def _tread(side, end=None):
    """A tread, half its width per tile: cleats in bands of the rotating
    entries, so it runs. side 0 outer, 1 inner; mirrored on the right."""
    t = np.full((T, T), SH, dtype=np.uint8)
    for y in range(T):
        t[y, 1:T - 1] = CLEAT[(y // 2) % 3]
        if y % 2 == 1:
            t[y, 1:T - 1] = SH
    if side == 0:
        t[:, 0] = OUT
        t[:, 1] = STEEL[0]
    else:
        t[:, T - 1] = OUT
        t[:, T - 2] = STEEL[0]
        t[::4, T - 4:T - 2] = STEEL[3]  # road wheels showing through
    yy, xx = np.mgrid[0:T, 0:T]
    if end == "top":
        r = np.sqrt((xx - (T - 0.5 if side == 0 else -0.5)) ** 2 + (yy - (T - 0.5)) ** 2)
        t[r > T - 0.5] = 0
        t[(r <= T - 0.5) & (r > T - 1.8)] = OUT
    elif end == "bottom":
        r = np.sqrt((xx - (T - 0.5 if side == 0 else -0.5)) ** 2 + (yy + 0.5) ** 2)
        t[r > T - 0.5] = 0
        t[(r <= T - 0.5) & (r > T - 1.8)] = OUT
    return t


def _socket(size):
    n = size * T
    big = np.concatenate([np.concatenate([_deck(3 + y * size + x) for x in range(size)], axis=1)
                          for y in range(size)], axis=0)
    yy, xx = np.mgrid[0:n, 0:n]
    c = n / 2 - 0.5
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    r = n / 2 - 1.5
    big[d < r] = STEEL[1]
    big[(d < r) & (d > r - 1.5) & (xx + yy < 2 * c)] = STEEL[4]
    big[(d < r) & (d > r - 1.5) & (xx + yy >= 2 * c)] = OUT
    big[(d < r - 2) & (((xx + yy) // 3) % 2 == 0) & (d > r - 3.5)] = HAZ
    big[d < r - 4] = SH
    return [big[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(size) for x in range(size)]


def _crater(size, seed):
    n = size * T
    big = np.concatenate([np.concatenate([_deck(40 + y * size + x) for x in range(size)], axis=1)
                          for y in range(size)], axis=0)
    yy, xx = np.mgrid[0:n, 0:n]
    c = n / 2 - 0.5
    noise = value_noise(n, n, 3, 2300 + seed)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / (n / 2) + (noise - 0.5) * 0.5
    big[d < 0.95] = STEEL[0]
    big[d < 0.75] = SH
    big[d < 0.5] = OUT
    big[(d < 0.6) & (noise > 0.62)] = LAMP_R
    return [big[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(size) for x in range(size)]


def _hatch():
    """A launch hatch, 1 x 2 tiles: hazard-striped doors."""
    big = np.concatenate([_deck(60), _deck(61)], axis=0)
    big[2:30, 2:14] = OUT
    big[3:29, 3:13] = STEEL[1]
    yy, xx = np.mgrid[0:32, 0:16]
    stripe = (((xx + yy) // 3) % 2 == 0) & ((yy < 7) | (yy > 24)) & (xx > 2) & (xx < 13)
    big[stripe] = HAZ
    big[15:17, 3:13] = OUT
    big[9:23:4, 5:11] = STEEL[3]
    return [big[0:16], big[16:32]]


def hull_tileset():
    tiles, ids = [np.zeros((T, T), dtype=np.uint8)], {"clear": 0}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"deck{k}", _deck(k))
    for side in (0, 1):
        for end in (None, "top", "bottom"):
            t = _tread(side, end)
            add(f"tread{side}{end or ''}", t)
            add(f"treadr{side}{end or ''}", np.fliplr(t).copy())
    vent = _deck(10)
    vent[3:13, 3:13] = SH
    vent[4:13:2, 4:12] = STEEL[1]
    add("vent", vent)
    lamp = _deck(11)
    lamp[6:10, 6:10] = OUT
    lamp[7:9, 7:9] = LAMP_G
    add("lamp", lamp)
    stripe = _deck(12)
    yy, xx = np.mgrid[0:T, 0:T]
    stripe[((xx + yy) // 4) % 2 == 0] = HAZ
    stripe[0, :] = OUT
    add("stripe", stripe)
    paint = _deck(13)
    paint[4:12, :] = PAINT
    paint[4, :] = STEEL[4]
    paint[11, :] = OUT
    add("paint", paint)
    # Rear: exhaust stacks; front: a plow blade angled back on each side.
    rear = _deck(14)
    rear[0, :] = OUT
    rear[1, :] = STEEL[4]
    rear[3:9, 3:7] = OUT
    rear[4:8, 4:6] = LAMP_R
    rear[3:9, 9:13] = OUT
    rear[4:8, 10:12] = LAMP_R
    add("rear", rear)
    for name, inside in (("plow_l", xx >= yy - 1), ("plow_r", xx <= T - yy)):
        t = _deck(15)
        t[~inside] = 0
        edge = (xx == yy - 1) | (xx == yy) if name == "plow_l" else (xx == T - yy) | (xx == T - 1 - yy)
        t[edge & inside] = OUT
        t[(xx == yy + 1) if name == "plow_l" else (xx == T - 2 - yy)] = FROSTC
        add(name, t)
    for k, t in enumerate(_socket(2)):
        add(f"big{k}", t)
    add("small", _socket(1)[0])
    for k, t in enumerate(_hatch()):
        add(f"hatch{k}", t)
    for k, t in enumerate(_crater(2, 1)):
        add(f"crater_big{k}", t)
    add("crater", _crater(1, 2)[0])
    return tiles, ids


def hull_map(ids):
    m = np.zeros((H, W), dtype=np.uint8)
    rng = np.random.default_rng(5)
    for r in range(H):
        for c in range(2, 8):
            m[r, c] = ids[f"deck{int(rng.integers(0, 4))}"]
    # Treads down both sides, rounded at the ends.
    for r in range(H):
        end = "top" if r == 0 else "bottom" if r == H - 1 else ""
        m[r, 0], m[r, 1] = ids[f"tread0{end}"], ids[f"tread1{end}"]
        m[r, 9], m[r, 8] = ids[f"treadr0{end}"], ids[f"treadr1{end}"]
    for c in range(2, 8):
        m[0, c] = ids["rear"]
        m[3, c] = ids["paint"]
        m[6, c] = ids["stripe"]
    m[3, 2], m[3, 7] = ids["vent"], ids["vent"]
    m[6, 2], m[6, 7] = ids["lamp"], ids["lamp"]
    m[8, 2], m[8, 3] = ids["plow_l"], ids["deck0"]
    m[8, 7], m[8, 6] = ids["plow_r"], ids["deck1"]
    for name, (c, r, w, h) in PARTS.items():
        if w == 2:
            for k in range(4):
                m[r + k // 2, c + k % 2] = ids[f"big{k}"]
        elif name.startswith("TUR"):
            m[r, c] = ids["small"]
        elif name.startswith("HATCH"):
            m[r, c], m[r + 1, c] = ids["hatch0"], ids["hatch1"]
    return m


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


_HALF_PORTRAIT = [
    "........",  # 0: margin
    "....111.",  # 1: top mount collar
    "...16651",  # 2: armored prow cowl
    "..165541",  # 3:
    ".1655411",  # 4:
    ".1658881",  # 5: cyan hull paint band (8)
    ".1558771",  # 6:
    ".154111.",  # 7: drill chuck casing
    "..15441.",  # 8: spiral flute start
    "..15481.",  # 9: rotating cutting blade (8)
    "..15481.",  # 10:
    "...1541.",  # 11: tapered cone
    "...1481.",  # 12: drill point
    "....181.",  # 13:
    "....11..",  # 14: tip (margin row 14)
    "........",  # 15: margin
]


def portrait():
    """16x16 HUD portrait of Glacier Crawler."""
    return _parse_frames([[r + "".join(reversed(r)) for r in _HALF_PORTRAIT]], 16, 16)


def reactor():
    """32x32 cryo reactor: a frosted dome over a glowing core. Frames: pulse."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        s.ellipse((2, 2, 30, 30), "armor", amp=2.4)
        for a in range(0, 360, 45):
            x, y = 16 + math.cos(math.radians(a)) * 10.5, 16 + math.sin(math.radians(a)) * 10.5
            s.ellipse((x - 2, y - 2, x + 2, y + 2), "vent", z=2.5, amp=0.4, profile="flat")
        s.ellipse((7, 7, 25, 25), "gold", z=2.5, amp=1.2)
        s.ellipse((9.5, 9.5, 22.5, 22.5), "corehot" if hot else "core", z=4)
        for a in (0, 60, 120):
            r = math.radians(a)
            s.line((16 - math.cos(r) * 5.5, 16 - math.sin(r) * 5.5), (16 + math.cos(r) * 5.5, 16 + math.sin(r) * 5.5),
                   "lightb" if hot else "corehot", width=1, z=5)
        out.append(s.render(MATS, gloss=0.45))
    return out


def drill():
    """32x32 ice drill, point down. Frames: two turns of its spiral."""
    out = []
    for k in range(2):
        s = Sprite(32, 32)
        s.rect((6, 3, 26, 9), "armor", amp=1.6, bevel=2)
        s.poly([(5, 8), (27, 8), (16, 29)], "plate", z=1, amp=2.2, bevel=3)
        for j in range(4):
            y = 11 + j * 4.4 + k * 2.2
            half = 10.0 * (29 - y) / 21
            s.line((16 - half, y), (16 + half, y + 2.0), "gold", width=1.5, z=2.5)
        s.dot(16, 5, "light", z=3)
        out.append(s.render(MATS, gloss=0.4))
    return out
