"""Stage 9 boss, GAMMA PRIME: the Gamma Core's true form, a sunburst
fortress feeding on the Sun.

The hull is a tile map (10 x 9 tiles, 160 x 144 pixels) on plane 1's
layer, palette GAMMA: gold plating (crawler.py's decks, sockets and
craters) inside a lit rim in marching squares, a disc with eight rays.
Light runs down the spine in the rotating entries 2-4. Sprites (palette
BOSS9): the core, two ring cannons, a beam emitter, four turrets, and four
prisms orbiting outside the hull.
"""

import math

import numpy as np

import crawler
from boss import MATS
from crawler import OUT, SH, STEEL
from hive import _field
from kit import BAYER4, Sprite

T = 16
W, H = 10, 9

GAMMA = [
    None,                                                               # 0 clear
    (20, 10, 0),                                                        # 1 outline
    (255, 120, 40), (255, 200, 80), (255, 255, 200),                    # 2-4 spine lights (rotate)
    (90, 60, 20), (140, 100, 40), (196, 150, 60), (232, 198, 110), (255, 240, 190),  # 5-9 gold plate
    (30, 16, 4),                                                        # 10 shadow
    (180, 30, 40),                                                      # 11 crimson trim
    (30, 40, 110),                                                      # 12 enamel
    (255, 60, 60), (120, 255, 255),                                     # 13-14 lamps (blink)
    (255, 255, 255),                                                    # 15 white
]
SPINE = [2, 3, 4]

BOSS9 = [
    None, (20, 8, 0),
    (120, 90, 40), (170, 130, 60), (214, 176, 96), (240, 214, 150), (255, 248, 220),  # 2-6 armour
    (150, 20, 40), (210, 40, 60), (255, 110, 120),                                   # 7-9 crimson
    (80, 255, 140), (230, 255, 230),                                                 # 10-11 gamma glow
    (20, 10, 0), (60, 36, 10),                                                       # 12-13 vents
    (120, 220, 255), (255, 255, 255),                                                # 14-15 lights
]
BOSS9_WRECK = [
    None, (8, 4, 0),
    (40, 30, 16), (56, 42, 22), (72, 56, 32), (90, 72, 44), (110, 92, 60),
    (50, 16, 20), (70, 24, 30), (90, 50, 54),
    (40, 80, 50), (80, 100, 80),
    (10, 6, 0), (24, 16, 6),
    (50, 80, 90), (100, 100, 100),
]

PARTS = {
    "CORE": (4, 3, 2, 2),
    "CANNON_L": (1, 3, 2, 2),
    "CANNON_R": (7, 3, 2, 2),
    "EMITTER": (4, 6, 2, 2),
    "TUR0": (2, 1, 1, 1),
    "TUR1": (7, 1, 1, 1),
    "TUR2": (2, 6, 1, 1),
    "TUR3": (7, 6, 1, 1),
}


def shape():
    """The hull's corners, (H + 1) x (W + 1), screen order: a disc and
    eight rays."""
    g = np.zeros((H + 1, W + 1), dtype=np.uint8)
    for y in range(H + 1):
        for x in range(W + 1):
            dx, dy = (x - 5) / 1.0, (y - 4.5) / 0.92
            r = math.hypot(dx, dy)
            a = math.degrees(math.atan2(dy, dx)) % 45
            ray = min(a, 45 - a)  # degrees from the nearest ray
            if r < 3.9 or (r < 5.7 and ray < 15 - r * 1.5):
                g[y, x] = 1
    return g


def edge(c):
    """A rim tile over gold plate: the shell lit toward the upper left."""
    f, fx, fy = _field(c)
    yy, xx = np.mgrid[0:T, 0:T]
    bay = BAYER4[yy % 4, xx % 4]
    t = crawler._deck(0)
    norm = np.hypot(fx, fy) + 1e-6
    lit = (fx * 0.6 + fy * 0.8) / norm * 0.5 + 0.5
    shell = f < 0.7
    lvl = np.clip(np.round(lit * 4 + bay * 0.8), 0, 4).astype(int)
    t[shell] = np.array(STEEL)[lvl[shell]]
    t[(f >= 0.68) & (f < 0.74)] = crawler.HAZ
    t[f < 0.5] = 0
    t[(f < 0.5) & (f > 0.42)] = OUT
    return t


def _spine():
    """The spine: a channel of running light down the middle of a tile."""
    t = crawler._deck(5, seams=False)
    yy, xx = np.mgrid[0:T, 0:T]
    t[:, 4:12] = SH
    t[:, 5:11] = OUT
    light = (xx >= 6) & (xx < 10)
    t[light] = np.array(SPINE)[(yy // 3) % 3][light]
    t[(yy % 3 == 2) & light] = OUT
    return t


def hull():
    tiles, ids, seen = [np.zeros((T, T), dtype=np.uint8)], {}, {bytes(T * T): 0}

    def add(t):
        b = t.tobytes()
        if b not in seen:
            seen[b] = len(tiles)
            tiles.append(t)
        return seen[b]

    g = shape()
    rng = np.random.default_rng(9)
    m = np.zeros((H, W), dtype=np.uint8)
    for r in range(H):
        for c in range(W):
            cfg = (int(g[r, c]), int(g[r, c + 1]), int(g[r + 1, c + 1]), int(g[r + 1, c]))
            if cfg == (1, 1, 1, 1):
                m[r, c] = add(crawler._deck(int(rng.integers(0, 4))))
            elif any(cfg):
                m[r, c] = add(edge(cfg))
    spine = add(_spine())
    for r in (0, 1, 2, 5, 8):
        for c in (4, 5):
            if all(g[r + dy, c + dx] for dy in (0, 1) for dx in (0, 1)):
                m[r, c] = spine
    lamp = crawler._deck(11)
    lamp[6:10, 6:10] = OUT
    lamp[7:9, 7:9] = crawler.LAMP_G
    lid = add(lamp)
    m[5, 1], m[5, 8] = lid, lid
    big = [add(t) for t in crawler._socket(2)]
    small = add(crawler._socket(1)[0])
    for name, (c, r, w, h) in PARTS.items():
        if w == 2:
            for k in range(4):
                m[r + k // 2, c + k % 2] = big[k]
        else:
            m[r, c] = small
    ids["crater_big0"] = len(tiles)
    tiles += crawler._crater(2, 9)
    ids["crater"] = len(tiles)
    tiles.append(crawler._crater(1, 10)[0])
    return tiles, ids, m


# ---- sprites (palette BOSS9) -------------------------------------------------

def core():
    """32x32 Gamma Core: a green star of gamma light in an armoured collar
    with eight fins. Frames: pulse."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        for a in range(0, 360, 45):
            r = math.radians(a + 22.5)
            p = [(16 + math.cos(r) * 14.5, 16 + math.sin(r) * 14.5),
                 (16 + math.cos(r + 0.3) * 9, 16 + math.sin(r + 0.3) * 9),
                 (16 + math.cos(r - 0.3) * 9, 16 + math.sin(r - 0.3) * 9)]
            s.poly(p, "gold", z=0.5, amp=1.2, bevel=1)
        s.ellipse((4, 4, 28, 28), "armor", z=1, amp=2.2)
        s.ellipse((8, 8, 24, 24), "vent", z=2, amp=0.3, profile="flat")
        s.ellipse((9.5, 9.5, 22.5, 22.5) if hot else (10.5, 10.5, 21.5, 21.5), "core", z=3)
        s.ellipse((13, 13, 19, 19), "lightb" if hot else "corehot", z=4)
        out.append(s.render(MATS, gloss=0.4))
    return out


def prism():
    """32x32 orbiting prism: a crystal in a gold frame. Frames: two turns."""
    out = []
    for k in range(2):
        s = Sprite(32, 32)
        a = k * math.pi / 4
        pts = [(16 + math.cos(a + i * math.pi / 2) * 13.5, 16 + math.sin(a + i * math.pi / 2) * 13.5) for i in range(4)]
        s.poly(pts, "armor", amp=2, bevel=2)
        inner = [(16 + math.cos(a + i * math.pi / 2) * 9, 16 + math.sin(a + i * math.pi / 2) * 9) for i in range(4)]
        s.poly(inner, "light", z=2, amp=1, bevel=1)
        s.ellipse((13, 13, 19, 19), "lightb", z=3)
        out.append(s.render(MATS, gloss=0.5))
    return out


_HALF_PORTRAIT = [
    "........",  # 0: margin
    "......11",  # 1: top vertical ray tip
    ".....165",  # 2: top ray fin
    '..116541',  # 3: diagonal ray + top collar
    '.16584c1',  # 4: collar crimson trim + vent ring
    '.168acca',  # 5: vent ring + outer gamma glow
    '.154abba',  # 6: core bright gamma pulse
    '.165bbff',  # 7: horizontal ray + white focal core
    '.165bbff',  # 8: horizontal ray + white focal core
    '.154abba',  # 9: core bright gamma pulse
    '.168acca',  # 10: vent ring + outer gamma glow
    '.16584c1',  # 11: lower collar crimson trim
    '..116541',  # 12: lower diagonal ray + collar
    ".....165",  # 13: bottom ray fin
    "......11",  # 14: bottom vertical ray tip
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
    """16x16 HUD portrait of Gamma Prime."""
    return _parse_frames([[r + "".join(reversed(r)) for r in _HALF_PORTRAIT]], 16, 16)
