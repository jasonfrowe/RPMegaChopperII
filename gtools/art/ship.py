"""Stage 3 boss, LEVIATHAN: a battleship too big for sprites.

The hull is a 10 x 26 tile map (160 x 416 pixels) drawn on plane 1's tile
layer with palette HULL, so it costs no sprite time at all. The game moves
the layer to move the ship. Guns, the bridge and the reactor are sprites
on top of it (palette BOSS3); the missile bays are hull tiles the game
swaps to open them. When a part is destroyed the game writes crater tiles
over its socket.

The bow points down the screen, at the player; row 0 is the stern.
"""

import math

import numpy as np

from boss import MATS
from kit import Sprite, value_noise

T = 16
W, H = 10, 26

HULL = [
    None,                                                               # 0 clear
    (8, 10, 16),                                                        # 1 outline
    (255, 110, 30), (255, 190, 70), (255, 250, 190),                    # 2-4 engine glow (rotate)
    (34, 38, 48), (56, 62, 76), (86, 94, 110), (126, 134, 150), (176, 184, 198),  # 5-9 steel
    (14, 16, 22),                                                       # 10 shadow
    (226, 176, 40),                                                     # 11 hazard
    (150, 36, 36),                                                      # 12 deck red
    (255, 50, 50), (80, 255, 140),                                      # 13-14 lamps (blink)
    (228, 234, 240),                                                    # 15 markings
]
OUT, SH, HAZ, RED, LAMP_R, LAMP_G, MARK = 1, 10, 11, 12, 13, 14, 15
STEEL = [5, 6, 7, 8, 9]
GLOW = [2, 3, 4]

BOSS3 = [
    None, (8, 10, 16),
    (34, 40, 52), (58, 66, 82), (90, 100, 118), (134, 144, 162), (190, 198, 212),  # 2-6 armour
    (110, 26, 26), (180, 50, 40), (240, 120, 80),                                  # 7-9 naval red
    (40, 230, 190), (200, 255, 240),                                               # 10-11 reactor
    (14, 16, 22), (36, 40, 52),                                                    # 12-13 vents
    (255, 210, 60), (255, 250, 220),                                               # 14-15 lights
]
BOSS3_WRECK = [
    None, (8, 6, 8),
    (26, 22, 22), (42, 36, 34), (62, 52, 48), (86, 72, 64), (112, 94, 82),
    (60, 24, 20), (90, 40, 30), (120, 70, 50),
    (40, 60, 50), (90, 110, 100),
    (12, 10, 10), (28, 22, 22),
    (70, 50, 30), (100, 80, 60),
]

# Where each part sits on the hull: tile column and row of its top left, and size in tiles.
PARTS = {
    "REACTOR": (4, 3, 2, 2),
    "BRIDGE": (3, 6, 4, 4),
    "GUN_A": (4, 11, 2, 2),
    "GUN_B": (4, 15, 2, 2),
    "TUR0": (1, 4, 1, 1),
    "TUR1": (8, 4, 1, 1),
    "TUR2": (1, 10, 1, 1),
    "TUR3": (8, 10, 1, 1),
    "TUR4": (1, 18, 1, 1),
    "TUR5": (8, 18, 1, 1),
    "BAY_L": (2, 13, 1, 2),
    "BAY_R": (7, 13, 1, 2),
}


def _deck(seed, seams=True):
    n = value_noise(T, T, 8, 1200 + seed)
    t = np.full((T, T), STEEL[2], dtype=np.uint8)
    t[n > 0.72] = STEEL[3]
    t[n < 0.25] = STEEL[1]
    if seams:
        t[0, :] = STEEL[3]
        t[:, 0] = STEEL[3]
        t[T - 1, :] = STEEL[0]
        t[:, T - 1] = STEEL[0]
    return t


def _socket(size):
    """A gun ring, size tiles across."""
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
    noise = value_noise(n, n, 3, 1300 + seed)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / (n / 2) + (noise - 0.5) * 0.5
    big[d < 0.95] = STEEL[0]
    big[d < 0.75] = SH
    big[d < 0.5] = OUT
    big[(d < 0.6) & (noise > 0.62)] = GLOW[0]   # embers
    big[(d < 0.4) & (noise > 0.7)] = GLOW[1]
    return [big[y * T:(y + 1) * T, x * T:(x + 1) * T] for y in range(size) for x in range(size)]


def _bay(open_):
    """A missile bay, 1 x 2 tiles: hatch doors, or open with missiles inside."""
    big = np.concatenate([_deck(60), _deck(61)], axis=0)
    big[2:30, 2:14] = OUT
    big[3:29, 3:13] = STEEL[0] if open_ else STEEL[3]
    if open_:
        for y in (6, 17):
            big[y:y + 8, 5:11] = STEEL[1]
            big[y:y + 2, 6:10] = RED
            big[y + 6:y + 8, 6:10] = GLOW[1]
    else:
        big[15:17, 3:13] = OUT
        for y in range(4, 28, 4):
            big[y, 4:12] = STEEL[2]
        big[3:29, 3] = HAZ
        big[3:29, 12] = HAZ
    return [big[0:16], big[16:32]]


def hull_tileset():
    tiles, ids = [np.zeros((T, T), dtype=np.uint8)], {"clear": 0}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"deck{k}", _deck(k))
    walk = _deck(9)
    walk[:, 5:11] = STEEL[1]
    walk[:, 7:9] = RED
    walk[::4, 5:11] = STEEL[0]
    add("walk", walk)
    vent = _deck(10)
    vent[3:13, 3:13] = SH
    vent[4:13:2, 4:12] = STEEL[1]
    add("vent", vent)
    lamp = _deck(11)
    lamp[6:10, 6:10] = OUT
    lamp[7:9, 7:9] = LAMP_G
    add("lamp", lamp)

    # Sides: lit from the left, so the port side is bright and starboard dark.
    yy, xx = np.mgrid[0:T, 0:T]
    port = _deck(12, seams=False)
    port[:, 0] = OUT
    port[:, 1] = STEEL[4]
    port[:, 2] = STEEL[3]
    port[:, 3] = STEEL[1]
    port[7:9, 5:7] = STEEL[4]  # bollard
    port[::8, 1:3] = STEEL[2]
    add("port", port)
    stbd = np.fliplr(_deck(13, seams=False)).copy()
    stbd[:, T - 1] = OUT
    stbd[:, T - 2] = STEEL[0]
    stbd[:, T - 3] = SH
    stbd[:, T - 4] = STEEL[1]
    stbd[7:9, 9:11] = STEEL[3]
    add("stbd", stbd)

    # Bow: a diagonal hull line on each side, narrowing to a point.
    for name, inside in (("bow_l", xx >= yy), ("bow_r", xx <= T - 1 - yy)):
        t = _deck(14)
        t[~inside] = 0
        edge = (xx == yy) if name == "bow_l" else (xx == T - 1 - yy)
        near = (xx == yy + 1) if name == "bow_l" else (xx == T - 2 - yy)
        t[edge] = OUT
        t[near & inside] = STEEL[4] if name == "bow_l" else STEEL[0]
        add(name, t)
    mark = _deck(15)
    mark[2:14, 6:10] = MARK
    mark[2:14, 7:9] = RED
    add("bow_mark", mark)

    # Stern: a rounded transom with the engines' exhaust glowing.
    for name, flip in (("stern_l", False), ("stern_r", True)):
        t = _deck(16)
        d = np.sqrt((xx - 15.5) ** 2 + (yy - 15.5) ** 2)
        t[d > 15.5] = 0
        t[(d <= 15.5) & (d > 14.2)] = OUT
        t[(d <= 14.2) & (d > 13)] = STEEL[4]
        if flip:
            t = np.fliplr(t).copy()
            t[(t == STEEL[4])] = STEEL[0]
        add(name, t)
    for name, glow in (("stern", False), ("engine", True)):
        t = _deck(17)
        t[0, :] = OUT
        t[1, :] = STEEL[4]
        if glow:
            t[2:9, 3:13] = OUT
            for y in range(3, 8):
                t[y, 4:12] = GLOW[(y - 3) % 3]
        add(name, t)

    for k, t in enumerate(_socket(2)):
        add(f"big{k}", t)
    add("small", _socket(1)[0])
    for k, t in enumerate(_bay(False)):
        add(f"bay{k}", t)
    for k, t in enumerate(_bay(True)):
        add(f"bayo{k}", t)
    for k, t in enumerate(_crater(2, 1)):
        add(f"crater_big{k}", t)
    add("crater", _crater(1, 2)[0])
    for k, t in enumerate(_crater(1, 3) + _crater(1, 4)):
        add(f"crater_bay{k}", t)
    return tiles, ids


def hull_map(ids):
    m = np.zeros((H, W), dtype=np.uint8)
    rng = np.random.default_rng(3)
    for r in range(H):
        for c in range(W):
            m[r, c] = ids[f"deck{int(rng.integers(0, 4))}"]
    # Walkway down the middle, vents and lamps along the deck.
    for r in range(1, 21):
        m[r, 4] = m[r, 5] = ids["walk"]
    for r in (2, 8, 14, 20):
        m[r, 2] = m[r, 7] = ids["vent"]
    for r in (6, 12, 17):
        m[r, 1] = m[r, 8] = ids["lamp"]
    # Sides.
    for r in range(1, 21):
        m[r, 0] = ids["port"]
        m[r, 9] = ids["stbd"]
    # Stern.
    m[0, 0], m[0, 9] = ids["stern_l"], ids["stern_r"]
    for c in range(1, 9):
        m[0, c] = ids["engine" if 3 <= c <= 6 else "stern"]
    # Bow: narrowing a column on each side per row.
    for k, r in enumerate(range(21, 26)):
        for c in range(W):
            if c < k or c > W - 1 - k:
                m[r, c] = 0
        m[r, k] = ids["bow_l"]
        m[r, W - 1 - k] = ids["bow_r"]
    m[21, 4] = m[21, 5] = m[22, 4] = m[22, 5] = ids["bow_mark"]
    # Sockets under the guns, the bridge's footing, the bays.
    for name, (c, r, w, h) in PARTS.items():
        if name.startswith("GUN") or name == "REACTOR":
            for k in range(4):
                m[r + k // 2, c + k % 2] = ids[f"big{k}"]
        elif name.startswith("TUR"):
            m[r, c] = ids["small"]
        elif name.startswith("BAY"):
            m[r, c], m[r + 1, c] = ids["bay0"], ids["bay1"]
        elif name == "BRIDGE":
            for y in range(h):
                for x in range(w):
                    m[r + y, c + x] = ids["deck0"]
    return m


def bridge():
    """64x64 superstructure: stepped decks, a radar dish, masts, lit windows."""
    s = Sprite(64, 64)
    s.poly([(8, 61), (8, 19), (16, 7), (48, 7), (56, 19), (56, 61)], "armor", amp=3, bevel=5)
    s.rect((14, 23, 50, 57), "plate", z=2.5, amp=1.6, bevel=3)
    s.rect((20, 29, 44, 51), "armor", z=4.5, amp=1.4, bevel=2.5)
    for x in range(22, 43, 4):
        s.rect((x, 45, x + 2, 48), "light", z=6, amp=0.2, profile="flat")
    s.rect((22, 25, 42, 28), "vent", z=3.5, amp=0.3, profile="flat")
    # Radar dish and masts.
    s.ellipse((24, 9, 40, 23), "gold", z=5, amp=1.6)
    s.ellipse((28, 12, 36, 20), "vent", z=6, amp=0.4, profile="flat")
    s.line((32, 16), (32, 3), "plate", width=2, z=7)
    s.line((14, 31), (6, 31), "plate", width=1, z=5, sym=True)
    s.dot(32, 3, "lightb", z=8)
    s.dot(6, 31, "light", z=6, sym=True)
    s.rect((10, 57, 54, 61), "gold", z=2, amp=0.6, bevel=1)
    return [s.render(MATS, gloss=0.35)]


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
    ".......f",  # 1: radar mast tip beacon (15)
    "......14",  # 2: mast needle
    ".....187",  # 3: naval red radar dish
    "....1887",  # 4:
    "...16554",  # 5: upper superstructure armor
    "..165444",  # 6:
    ".1654eee",  # 7: bridge window strip (14 = e amber)
    ".1654eee",  # 8:
    ".1544433",  # 9: lower deck terrace
    ".1544998",  # 10: naval red pinstripe
    ".1544333",  # 11:
    "..154433",  # 12: stepped hull
    "..154331",  # 13:
    "...1111.",  # 14: bottom margin
    "........",  # 15: margin
]


def portrait():
    """16x16 HUD portrait of Leviathan battleship."""
    return _parse_frames([[r + "".join(reversed(r)) for r in _HALF_PORTRAIT]], 16, 16)


def reactor():
    """32x32 reactor under an armoured iris. Frames: pulse dim/bright."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        s.ellipse((2, 2, 30, 30), "armor", amp=2.4)
        for a in range(0, 360, 60):
            x, y = 16 + math.cos(math.radians(a)) * 10, 16 + math.sin(math.radians(a)) * 10
            s.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), "vent", z=2.5, amp=0.4, profile="flat")
        s.ellipse((7, 7, 25, 25), "gold", z=2.5, amp=1.2)
        s.ellipse((9.5, 9.5, 22.5, 22.5), "corehot" if hot else "core", z=4)
        s.ellipse((13, 13, 19, 19), "lightb" if hot else "corehot", z=5)
        out.append(s.render(MATS, gloss=0.4))
    return out


def main_gun():
    """32x32 twin-barrel turret aimed in 8 directions, starting straight down, clockwise."""
    out = []
    for k in range(8):
        a = math.pi / 2 + k * (2 * math.pi / 8)
        s = Sprite(32, 32)
        c, sn = math.cos(a), math.sin(a)
        for side in (-3.5, 3.5):
            ox, oy = -sn * side, c * side
            s.line((16 + ox, 16 + oy), (16 + ox + c * 13.5, 16 + oy + sn * 13.5), "vent", width=4, z=3.6)
            s.line((16 + ox, 16 + oy), (16 + ox + c * 13.5, 16 + oy + sn * 13.5), "plate", width=2, z=4)
        s.ellipse((7, 7, 25, 25), "armor", z=1, amp=2.4)
        s.ellipse((10.5, 10.5, 21.5, 21.5), "gold", z=2.8, amp=1.2)
        s.ellipse((13, 13, 19, 19), "plate", z=3.5, amp=1.0)
        s.dot(15, 15, "light", z=4.5)
        out.append(s.render(MATS, gloss=0.3))
    return out
