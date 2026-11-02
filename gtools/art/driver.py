"""Stage 7 boss, MASS DRIVER: a hovering gun platform built round a rail
cannon that runs its whole length.

The hull is a tile map (10 x 9 tiles, 160 x 144 pixels) on plane 1's
layer, palette DRIVER, drawn with crawler.py's vocabulary of plates,
sockets, hatches and craters (the palette entries play the same roles).
The rail's coils are drawn in the rotating entries 2-4, so charge seems
to run down the barrel. Sprites (palette BOSS7): the breech, which is the
core, two capacitor pods, four turrets and the muzzle.
"""

import math

import numpy as np

import crawler
from boss import MATS
from crawler import OUT, SH, HAZ, PAINT, LAMP_G, STEEL
from kit import Sprite

T = 16
W, H = 10, 9

DRIVER = [
    None,                                                               # 0 clear
    (8, 8, 14),                                                         # 1 outline
    (110, 50, 230), (190, 130, 255), (250, 230, 255),                   # 2-4 coils (rotate)
    (44, 46, 50), (72, 74, 78), (108, 108, 110), (150, 148, 146), (204, 200, 194),  # 5-9 gunmetal
    (14, 14, 18),                                                       # 10 shadow
    (230, 170, 30),                                                     # 11 hazard
    (130, 36, 40),                                                      # 12 paint
    (255, 50, 50), (80, 255, 160),                                      # 13-14 lamps (blink)
    (226, 222, 214),                                                    # 15 markings
]
COIL = [2, 3, 4]

BOSS7 = [
    None, (8, 8, 14),
    (44, 46, 50), (72, 74, 78), (108, 108, 110), (150, 148, 146), (204, 200, 194),  # 2-6 armour
    (110, 50, 20), (190, 100, 40), (250, 170, 90),                                 # 7-9 copper
    (170, 90, 255), (240, 210, 255),                                               # 10-11 charge
    (14, 14, 18), (40, 36, 46),                                                    # 12-13 vents
    (255, 200, 60), (255, 250, 220),                                               # 14-15 lights
]
BOSS7_WRECK = [
    None, (6, 6, 8),
    (24, 24, 26), (36, 36, 38), (52, 52, 54), (72, 70, 70), (96, 92, 90),
    (50, 30, 20), (76, 50, 30), (100, 76, 50),
    (70, 50, 100), (120, 100, 140),
    (10, 10, 12), (24, 22, 26),
    (70, 50, 30), (100, 80, 60),
]

PARTS = {
    "BREECH": (4, 0, 2, 2),
    "CAP_L": (1, 2, 2, 2),
    "CAP_R": (7, 2, 2, 2),
    "HATCH_L": (3, 4, 1, 2),
    "HATCH_R": (6, 4, 1, 2),
    "TUR0": (1, 0, 1, 1),
    "TUR1": (8, 0, 1, 1),
    "TUR2": (1, 6, 1, 1),
    "TUR3": (8, 6, 1, 1),
    "MUZZLE": (4, 7, 2, 2),
}


def _rail(side):
    """Half the barrel (side 0 left, 1 right): a steel rail and coil rings
    in bands of the rotating entries."""
    t = np.full((T, T), SH, dtype=np.uint8)
    for y in range(T):
        t[y, :] = COIL[(y // 3) % 3] if y % 3 != 2 else OUT
    if side == 0:
        t[:, 0] = OUT
        t[:, 1:4] = STEEL[4]
        t[:, 4] = STEEL[2]
        t[:, 12:] = SH  # the bore
    else:
        t[:, T - 1] = OUT
        t[:, T - 4:T - 1] = STEEL[1]
        t[:, T - 5] = STEEL[0]
        t[:, :4] = SH
    return t


def _nacelle(end, side):
    """A hover engine down each side: armoured, with a row of vents."""
    t = crawler._deck(70 + side, seams=False)
    t[:, 0 if side == 0 else T - 1] = OUT
    t[:, 1 if side == 0 else T - 2] = STEEL[4] if side == 0 else STEEL[0]
    for y in range(3, T, 5):
        t[y:y + 2, 4:12] = SH
        t[y, 5:11] = PAINT
    yy, xx = np.mgrid[0:T, 0:T]
    if end:
        cx = T - 0.5 if side == 0 else -0.5
        cy = T - 0.5 if end == "top" else -0.5
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        t[r > T - 0.5] = 0
        t[(r <= T - 0.5) & (r > T - 1.8)] = OUT
    return t


def hull():
    tiles, ids = [np.zeros((T, T), dtype=np.uint8)], {"clear": 0}

    def add(name, t):
        ids[name] = len(tiles)
        tiles.append(t)

    for k in range(4):
        add(f"deck{k}", crawler._deck(k))
    for side in (0, 1):
        add(f"rail{side}", _rail(side))
        for end in (None, "top", "bottom"):
            add(f"nac{side}{end or ''}", _nacelle(end, side))
    stripe = crawler._deck(12)
    yy, xx = np.mgrid[0:T, 0:T]
    stripe[((xx + yy) // 4) % 2 == 0] = HAZ
    add("stripe", stripe)
    lamp = crawler._deck(11)
    lamp[6:10, 6:10] = OUT
    lamp[7:9, 7:9] = LAMP_G
    add("lamp", lamp)
    for k, t in enumerate(crawler._socket(2)):
        add(f"big{k}", t)
    add("small", crawler._socket(1)[0])
    for k, t in enumerate(crawler._hatch()):
        add(f"hatch{k}", t)
    for k, t in enumerate(crawler._crater(2, 3)):
        add(f"crater_big{k}", t)
    add("crater", crawler._crater(1, 4)[0])

    m = np.zeros((H, W), dtype=np.uint8)
    rng = np.random.default_rng(7)
    for r in range(H):
        for c in range(1, 9):
            m[r, c] = ids[f"deck{int(rng.integers(0, 4))}"]
        end = "top" if r == 0 else "bottom" if r == H - 1 else ""
        m[r, 0], m[r, 9] = ids[f"nac0{end}"], ids[f"nac1{end}"]
        m[r, 4], m[r, 5] = ids["rail0"], ids["rail1"]
    for c in (1, 2, 3, 6, 7, 8):
        m[H - 1, c] = ids["stripe"]
    m[4, 1], m[4, 8] = ids["lamp"], ids["lamp"]
    for name, (c, r, w, h) in PARTS.items():
        if w == 2:
            for k in range(4):
                m[r + k // 2, c + k % 2] = ids[f"big{k}"]
        elif name.startswith("TUR"):
            m[r, c] = ids["small"]
        elif name.startswith("HATCH"):
            m[r, c], m[r + 1, c] = ids["hatch0"], ids["hatch1"]
    return tiles, ids, m


def breech():
    """32x32 breech: the capacitor core feeding the rail. Frames: pulse."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        s.rect((2.5, 2.5, 29.5, 29.5), "armor", amp=2.4, bevel=4)
        s.rect((6, 6, 26, 26), "gold", z=2, amp=1.2, bevel=2)
        for y in (9, 15, 21):
            s.rect((7, y, 25, y + 2), "vent", z=2.6, amp=0.3, profile="flat")
        s.ellipse((10, 10, 22, 22), "corehot" if hot else "core", z=4)
        s.ellipse((13.5, 13.5, 18.5, 18.5), "lightb" if hot else "corehot", z=5)
        out.append(s.render(MATS, gloss=0.4))
    return out


def capacitor():
    """32x32 capacitor pod: a drum wound with copper coils. Frames: charge."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        s.ellipse((2, 2, 30, 30), "armor", amp=2.4)
        for r in (12, 9, 6):
            s.ellipse((16 - r, 16 - r, 16 + r, 16 + r), "gold" if r != 9 else "plate", z=13 - r, amp=1)
        s.ellipse((12, 12, 20, 20), "corehot" if hot else "core", z=8)
        for a in range(0, 360, 90):
            x, y = 16 + math.cos(math.radians(a + 45)) * 13, 16 + math.sin(math.radians(a + 45)) * 13
            s.dot(x, y, "light", z=3)
        out.append(s.render(MATS, gloss=0.35))
    return out


def muzzle():
    """32x32 muzzle, pointing down. Frames: idle, charged."""
    out = []
    for hot in (False, True):
        s = Sprite(32, 32)
        s.rect((4, 2.5, 28, 22), "armor", amp=2.2, bevel=3)
        s.poly([(4, 20), (28, 20), (24, 29.5), (8, 29.5)], "plate", z=1, amp=1.6, bevel=2)
        for y in (5, 10, 16):
            s.rect((5, y, 27, y + 3), "gold", z=2.5, amp=0.8, bevel=1)
        s.ellipse((11, 19, 21, 29.5), "vent", z=3, amp=0.3, profile="flat")
        s.ellipse((13, 22, 19, 28), "corehot" if hot else "core", z=4)
        if hot:
            s.ellipse((14.5, 24, 17.5, 27), "lightb", z=5)
        out.append(s.render(MATS, gloss=0.35))
    return out


_HALF_PORTRAIT = [
    "........",  # 0: margin
    "..111111",  # 1: top breech armor
    ".1655881",  # 2: breech plates + center copper coil
    ".16544a1",  # 3: outer nacelle start + charged rail
    ".165e4b1",  # 4: capacitor pod (indicator e) + core charge
    ".15444b1",  # 5: pod armor + glowing rail
    ".16584a1",  # 6: pod copper coil ring
    ".15444b1",  # 7: pod armor + glowing rail
    ".11444b1",  # 8: nacelle taper + rail
    "..1549b1",  # 9: lower rail funnel
    "..1658a1",  # 10: muzzle emitter shroud
    "..164bb1",  # 11: muzzle bore focus
    "...15bb1",  # 12: emitter aperture
    "....15b1",  # 13: muzzle bottom
    ".....111",  # 14: bottom outline rim
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
    """16x16 HUD portrait of Mass Driver."""
    return _parse_frames([[r + "".join(reversed(r)) for r in _HALF_PORTRAIT]], 16, 16)
