"""Every sprite sheet. Each returns a list of frames (h x w index arrays).

Sprites that face a way are drawn facing left; the game flips them with
MODE5_HFLIP to face right.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from art.kit import Material, Sprite  # noqa: E402


def grid(text, key):
    rows = [r for r in text.strip("\n").split("\n")]
    w = max(len(r) for r in rows)
    out = np.zeros((len(rows), w), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            out[y, x] = key.get(ch, 0)
    return out


def rot(pts, ang, cx, cy):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


# --- Chopper ---------------------------------------------------------------
CHOPPER_W, CHOPPER_H = 40, 20
CH_MATS = {
    "hull": Material([2, 3, 4, 5]),
    "red": Material([6, 7, 8]),
    "glass": Material([9, 10, 11], dither=0.2),
    "dark": Material([12, 13]),
    "skid": Material([12, 13], shaded=False),
}


def _chopper_side(pitch, blade, squash=1.0):
    """Side view, nose left. pitch > 0 tips the nose down."""
    s = Sprite(CHOPPER_W, CHOPPER_H)
    cx, cy = 18.0, 11.0

    def T(pts):
        pts = [(cx + (x - cx) * squash, y) for x, y in pts]
        return rot(pts, -pitch, cx, cy)

    # Tail boom and fin first, so the body sits over them.
    s.poly(T([(20, 9), (35, 10), (35, 12), (20, 14)]), "hull", amp=1.0, bevel=1.0)
    s.poly(T([(32, 10), (34, 4), (37, 4), (37, 12), (34, 12)]), "red", amp=1.0, bevel=1.0)
    s.poly(T([(4, 12), (8, 7), (14, 5), (22, 6), (25, 9), (25, 15), (20, 17), (8, 17), (5, 15)]),
           "hull", amp=3.0, bevel=3.0)
    s.poly(T([(5, 13), (24, 13), (24, 15), (20, 16.5), (8, 16.5), (5, 15)]), "red", amp=2.0, bevel=1.5)
    s.poly(T([(4.5, 12), (8, 7), (13, 6), (14, 12)]), "glass", amp=2.5, bevel=2.0)
    s.poly(T([(14, 4), (19, 4), (20, 6), (13, 6)]), "dark", amp=1.0, bevel=1.0)       # engine
    s.poly(T([(15.5, 2), (17.5, 2), (17.5, 4.5), (15.5, 4.5)]), "dark", amp=0.5)       # mast
    # Skids.
    s.line(*T([(8, 17), (8, 18.5)]), "skid")
    s.line(*T([(19, 17), (19, 18.5)]), "skid")
    s.line(*T([(5, 19), (23, 19)]), "skid")
    s.line(*T([(4, 18), (5, 19)]), "skid")
    out = s.render(CH_MATS, gloss=0.4)
    # Main rotor: a long blade, or a short one seen end on, with blur.
    rx = [(0, 39), (9, 27)][blade]
    p0, p1 = T([(rx[0], 1.5)])[0], T([(rx[1], 1.5)])[0]
    n = int(abs(p1[0] - p0[0])) + 1
    for k in range(n):
        t = k / max(1, n - 1)
        x = int(round(p0[0] + (p1[0] - p0[0]) * t))
        y = int(round(p0[1] + (p1[1] - p0[1]) * t))
        if 0 <= x < CHOPPER_W and 0 <= y < CHOPPER_H:
            out[y, x] = 12 if (k % 6) < 4 or blade else 14
            if blade == 0 and 0 <= y - 1 and k % 3 == 0:
                out[y - 1, x] = 14 if out[y - 1, x] == 0 else out[y - 1, x]
    # Tail rotor: a small blurred disc.
    tx, ty = T([(37, 6)])[0]
    for dy in (-2, -1, 0, 1, 2):
        x, y = int(round(tx)), int(round(ty + dy))
        if 0 <= x < CHOPPER_W and 0 <= y < CHOPPER_H:
            out[y, x] = 14 if (dy + blade) % 2 else 13
    nx, ny = T([(24, 10)])[0]
    out[int(round(ny)), int(round(nx))] = 15
    return out


def _chopper_front(bank, blade):
    """Facing the screen. bank > 0 tilts it to the left."""
    s = Sprite(CHOPPER_W, CHOPPER_H)
    cx, cy = 20.0, 12.0

    def T(pts):
        return rot(pts, bank, cx, cy)

    s.poly(T([(17, 9), (23, 9), (23, 4), (17, 4)]), "dark", amp=1.0)                   # engine
    s.poly(T([(19, 2), (21, 2), (21, 5), (19, 5)]), "dark", amp=0.5)
    s.ellipse((12, 5, 28, 18), "hull", amp=3.0)
    s.poly(T([(12, 13), (28, 13), (27, 16), (24, 18), (16, 18), (13, 16)]), "red", amp=1.5)
    s.ellipse((14, 6, 26, 14), "glass", amp=3.0)
    s.line(*T([(15, 17), (12, 19)]), "skid")
    s.line(*T([(25, 17), (28, 19)]), "skid")
    s.line(*T([(8, 19.5), (15, 19.5)]), "skid")
    s.line(*T([(25, 19.5), (32, 19.5)]), "skid")
    if bank:
        # Ellipses are not rotated by T; nudge the whole frame instead.
        pass
    out = s.render(CH_MATS, gloss=0.5)
    if bank:
        sh = int(round(math.copysign(1, bank)))
        out = np.roll(out, -sh, axis=1)
    rx = [(0, 39), (6, 33)][blade]
    for x in range(rx[0], rx[1] + 1):
        y = int(round(1.5 + (x - cx) * math.tan(bank)))
        if 0 <= y < CHOPPER_H:
            out[y, x] = 12 if (x // 5 + blade) % 3 else 14
    return out


def chopper():
    """Frames, in pairs (two rotor phases):
    0 side, 2 side nose down, 4 side nose up, 6 three-quarter, 8 front,
    10 front banking."""
    frames = []
    for kind in ("side", "down", "up", "quarter", "front", "bank"):
        for blade in (0, 1):
            if kind == "side":
                f = _chopper_side(0.0, blade)
            elif kind == "down":
                f = _chopper_side(0.14, blade)
            elif kind == "up":
                f = _chopper_side(-0.12, blade)
            elif kind == "quarter":
                f = _chopper_side(0.0, blade, squash=0.62)
            elif kind == "front":
                f = _chopper_front(0.0, blade)
            else:
                f = _chopper_front(0.12, blade)
            frames.append(f)
    return frames


# --- Hostages --------------------------------------------------------------
HK = {"o": 1, "a": 2, "b": 3, "c": 4, "p": 5, "q": 6, "s": 7, "t": 8, "h": 9, "w": 10}
HOSTAGE_FRAMES = [
    # 0-3: running (facing left)
    """
................
......ooo.......
.....ohhho......
.....othho......
.....ostto......
......oso.......
.....obcco......
....obccccoo....
...otbbccbtto...
....oobbbbo.....
.....oqppo......
....oqpoopo.....
...oqpo.oppo....
..ohho...ohho...
..ooo.....ooo...
................
""",
    """
................
................
......ooo.......
.....ohhho......
.....othho......
.....ostto......
......oso.......
.....obccoo.....
....obcccbto....
....otbbbbo.....
.....obbbo......
.....oqppo......
.....oqopo......
.....ohoqo......
....ohhoho......
.....oo.oo......
""",
    """
................
......ooo.......
.....ohhho......
.....othho......
.....ostto......
......oso.......
.....obcco......
....oobcccbo....
...otbbccbbto...
....oobbbbo.....
......oppo......
.....oppqpo.....
....oppo.oqpo...
...ohho...ohho..
...ooo.....ooo..
................
""",
    """
................
................
......ooo.......
.....ohhho......
.....othho......
.....ostto......
......oso.......
.....oobcco.....
....otbcccbo....
.....obbbbto....
......obbbo.....
......oppqo.....
......opoqo.....
......oqohho....
......ohoho.....
......oo.oo.....
""",
    # 4-5: waving, both arms up
    """
....oo....oo....
...otto..otto...
....oto..oto....
....obooooobo...
.....obhhhbo....
.....ohhhho.....
.....othhto.....
.....ostts......
......osso......
.....obccbo.....
....obccccbo....
.....obbbbo.....
.....oqppqo.....
.....oqooqo.....
....ohho.ohho...
....ooo...ooo...
""",
    """
................
...oo......oo...
..otto....otto..
...otbo..obto...
.....obhhhbo....
.....ohhhho.....
.....othhto.....
.....ostts......
......osso......
.....obccbo.....
....obccccbo....
.....obbbbo.....
.....oqppqo.....
.....oqooqo.....
....ohho.ohho...
....ooo...ooo...
""",
    # 6: standing
    """
................
................
......ooo.......
.....ohhho......
.....othho......
.....ostto......
......oso.......
.....obcco......
....obccccbo....
....obcbbcbo....
....otbccbto....
.....obbbbo.....
.....oqppqo.....
.....oqooqo.....
.....ohooho.....
.....oo..oo.....
""",
]


def hostages():
    return [grid(t, HK) for t in HOSTAGE_FRAMES]


# --- Tank ------------------------------------------------------------------
TANK_W, TANK_H = 40, 20
TK_MATS = {
    "hull": Material([2, 3, 4, 5]),
    "camo": Material([5, 6, 7]),
    "tread": Material([8, 9, 10]),
    "barrel": Material([8, 9, 10]),
    "red": Material([11, 12]),
}


def _tank(aim, tread):
    """Facing left. aim 0: barrel raised toward the left, 1: straight up."""
    s = Sprite(TANK_W, TANK_H)
    if aim == 0:
        s.poly([(3, 6), (16, 9.5), (16, 11.5), (3, 8)], "barrel", amp=0.8, bevel=0.8)
    else:
        s.poly([(17, 0), (19, 0), (19, 9), (17, 9)], "barrel", amp=0.8, bevel=0.8)
    s.poly([(12, 13), (14, 8), (19, 6), (28, 6), (31, 9), (31, 13)], "hull", amp=2.5, bevel=2.0)   # turret
    s.poly([(17, 7), (22, 7), (21, 10), (16, 10)], "camo", amp=1.0)
    s.poly([(2, 15), (6, 12), (36, 12), (39, 15), (36, 17), (4, 17)], "hull", amp=2.0, bevel=2.0)   # hull
    s.poly([(8, 13), (14, 13), (12, 15), (7, 15)], "camo", amp=0.8)
    s.poly([(24, 13), (31, 13), (32, 15), (26, 15)], "camo", amp=0.8)
    s.poly([(3, 16), (37, 16), (35, 19.5), (5, 19.5)], "tread", amp=1.5, bevel=1.5)
    s.rect((25, 9, 28, 11), "red", amp=0.5)
    out = s.render(TK_MATS)
    # Road wheels, turning.
    for k, x in enumerate(range(7, 35, 5)):
        out[17, x] = 10 if (k + tread) % 2 else 8
        out[18, x] = 8 if (k + tread) % 2 else 10
    for x in range(5, 36):
        if (x + tread * 2) % 4 == 0:
            out[19, x] = 1
    return out


def tank():
    """0-1: barrel raised left (two tread phases), 2-3: barrel up."""
    return [_tank(a, t) for a in (0, 1) for t in (0, 1)]


# --- Jet -------------------------------------------------------------------
JET_W, JET_H = 40, 16
JT_MATS = {
    "hull": Material([2, 3, 4, 5]),
    "red": Material([6, 7]),
    "canopy": Material([8, 9], dither=0.2),
    "dark": Material([2, 3]),
}


def jet():
    """Facing left; frames differ in the afterburner flame."""
    frames = []
    for flame in (0, 1):
        s = Sprite(JET_W, JET_H)
        s.poly([(18, 8), (24, 1), (29, 1), (27, 8)], "hull", amp=1.0)                     # tail fin
        s.poly([(1, 9), (8, 6.5), (30, 6.5), (35, 8), (35, 11), (8, 11.5)], "hull", amp=2.5, bevel=2.5)
        s.poly([(14, 10), (26, 10), (30, 14.5), (22, 14.5)], "dark", amp=1.0)            # wing
        s.poly([(6, 7.5), (10, 5), (15, 5), (17, 7.5)], "canopy", amp=1.5)
        s.poly([(22, 1.5), (28, 1.5), (27, 4), (23, 4)], "red", amp=0.8)
        s.poly([(1, 9), (4, 8), (4, 10)], "red", amp=0.5)
        out = s.render(JT_MATS, gloss=0.4)
        n = 3 + flame * 2
        for k in range(n):
            x = 35 + k
            if x < JET_W:
                out[8, x] = 12 if k < 2 else 11
                out[9, x] = 11 if k < n - 1 else 10
                out[10, x] = 10 if k < n - 2 else 0
        frames.append(out)
    return frames


# --- Balloon ---------------------------------------------------------------
BALLOON_W, BALLOON_H = 32, 32
BL_MATS = {
    "env": Material([2, 3, 4, 5], dither=0.15),
    "red": Material([6, 7]),
    "fin": Material([2, 3, 4]),
    "gond": Material([8, 9]),
    "mine": Material([13, 9]),
}


def balloon():
    """A motorised barrage blimp, nose left: a silver teardrop envelope with
    red bands and three tail fins, a slim gondola with a pusher propeller,
    and a spiked mine hanging below. Frames: the propeller turning, and the
    warning light on the mine blinking."""
    frames = []
    for k in range(3):
        s = Sprite(BALLOON_W, BALLOON_H)
        s.poly([(21, 8), (26, 1), (30, 1), (29, 8)], "fin", amp=1.0)           # top fin
        s.poly([(21, 12), (26, 18), (30, 18), (29, 12)], "fin", amp=1.0)       # bottom fin
        s.poly([(12, 5), (29, 9), (29, 11), (12, 16)], "env", amp=3.0, bevel=3.0)  # tail cone
        s.ellipse((1, 3, 21, 18), "env", amp=5.0)                              # body
        s.rect((8, 4, 9, 17), "red", amp=0.4)
        s.rect((14, 4.5, 15, 16.5), "red", amp=0.4)
        s.poly([(10, 18), (17, 18), (16, 21), (11, 21)], "gond", amp=0.8)
        s.ellipse((9, 22, 19, 32), "mine", amp=3.0)
        out = s.render(BL_MATS, gloss=0.4)
        # Cables: envelope to gondola, gondola to mine.
        out[17, 11] = out[17, 16] = 9
        out[21, 14] = 9
        # Hazard band round the mine, and spikes.
        for x in range(10, 19):
            if out[27, x] not in (0, 1):
                out[27, x] = 12 if (x // 2) % 2 else 1
        for x, y in ((8, 27), (19, 27), (14, 31), (10, 23), (18, 23)):
            out[y, x] = 1
        out[6, 5] = out[6, 6] = 15                                              # glint
        # Pusher propeller: a blurred disc behind the gondola, turning.
        out[19, 18] = 8
        for y in (17, 18, 19, 20, 21):
            out[y, 19] = 14 if (y + k) % 3 else 9
        # The warning light on the mine: on, dim, on.
        out[25, 13] = 10 if k != 1 else 6
        out[24, 13] = 11 if k != 1 else out[24, 13]
        frames.append(out)
    return frames


# --- Small things ----------------------------------------------------------
FXK = {"o": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "A": 10, "B": 11,
       "c": 12, "d": 13, "y": 14, "u": 15}


def bomb():
    return [np.flipud(f) for f in _bomb()]


def _bomb():
    return [grid("""
..oooo..
.oddcco.
.ocddco.
.occcco.
..occo..
..odco..
.oo..oo.
........
""", FXK), grid("""
..oooo..
.oddcco.
.ocddco.
.occcco.
..occo..
..odco..
..o..o..
.oo..oo.
""", FXK)]


def bullet():
    """0: the chopper's tracer (8x4), 1: flak shell glow (8x4)."""
    return [grid("""
........
.5yyyy7.
.4555yy.
........
""", FXK), grid("""
..3443..
.346643.
.346643.
..3443..
""", FXK)]


def explosion():
    """A 32x32 fireball that billows into smoke."""
    frames = []
    rng = np.random.default_rng(3)
    n = 7
    for f in range(n):
        out = np.zeros((32, 32), np.uint8)
        t = f / (n - 1)
        R = 5 + 11 * min(1, t * 1.6)
        yy, xx = np.mgrid[0:32, 0:32]
        blobs = [(16, 18, R)] + [(16 + rng.uniform(-1, 1) * R * 0.6, 18 + rng.uniform(-1, 0.4) * R * 0.6,
                                  R * rng.uniform(0.45, 0.7)) for _ in range(5)]
        heat = np.zeros((32, 32))
        for bx, by, br in blobs:
            d = np.sqrt((xx - bx) ** 2 + ((yy - by) * 1.1) ** 2) / br
            heat = np.maximum(heat, 1 - d)
        rise = int(t * 6)
        if rise:
            heat = np.vstack([heat[rise:], np.zeros((rise, 32))])
        core = heat * (1.0 - t * 0.9)
        dith = np.tile(np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0, (8, 8))
        fire = [2, 3, 4, 5, 6, 7]
        smoke = [8, 9, 10, 11]
        inside = heat > 0.05
        v = core * 1.6 + (dith - 0.5) * 0.25
        idx = np.where(v > 0.25, np.array(fire)[np.clip((v * 4).astype(int), 0, 5)],
                       np.array(smoke)[np.clip(((heat + (dith - 0.5) * 0.3) * 4).astype(int), 0, 3)])
        if t > 0.7:  # thinning smoke, in ragged holes
            inside &= rng.random((32, 32)) < (1.25 - t) * 1.4
        out[inside] = idx[inside]
        edge = inside & ~(np.roll(inside, 1, 0) & np.roll(inside, -1, 0) & np.roll(inside, 1, 1) & np.roll(inside, -1, 1))
        out[edge & (t < 0.7)] = 1
        frames.append(out)
    return frames


def smallexplosion():
    return [grid(t, FXK) for t in ("""
................
................
................
................
.......o........
......o7o.......
.....o767o......
....o76667o.....
.....o767o......
......o7o.......
.......o........
................
................
................
................
................
""", """
................
................
.......o........
.....oo6oo......
....o566665o....
...o56677665o...
...o56777765o...
..o5677777665o..
...o56777765o...
...o45666654o...
....o445544o....
.....oo44oo.....
.......o........
................
................
................
""", """
................
.....oo..oo.....
....o54oo45o....
...o5445544o....
..o544333445o...
..o4433A3344o...
.o443AAAA3344o..
.o43AABBAA34o...
..o43AAAA34o....
..o443AA3344o...
...o4433344o....
....oo4444oo....
......oooo......
................
................
................
""", """
................
.....o....o.....
....oAo..oAo....
...oA9AooA9Ao...
..o9A99AA99A9o..
..o99A9999A99o..
..o9999BB9999o..
...o99A99A99o...
..o999999999o...
...o99A99A9o....
....oo9999oo....
......oooo......
................
................
................
................
""")]


def flags():
    """A 24x16 maple-leaf flag on the pole, rippling; the pole is at its left."""
    frames = []
    leaf = grid("""
....r....
..r.rr.r.
.rrrrrrr.
rrrrrrrrr
.rrrrrrr.
..rrrrr..
....r....
....r....
""", {"r": 3})
    for f in range(4):
        out = np.zeros((16, 24), np.uint8)
        for x in range(23):
            off = int(round(1.4 * math.sin(x / 3.2 - f * math.pi / 2) * min(1, x / 6)))
            for y in range(1, 15):
                yy = y + off
                if not 0 <= yy < 16:
                    continue
                if y in (1, 14) or x == 22:
                    c = 1
                elif x < 6 or x > 16:
                    c = 3
                else:
                    c = 6
                out[yy, x] = c
        # The leaf, drawn into the white field and shaded by the ripple.
        for ly in range(8):
            for lx in range(9):
                if leaf[ly, lx]:
                    x = 7 + lx
                    off = int(round(1.4 * math.sin(x / 3.2 - f * math.pi / 2) * min(1, x / 6)))
                    out[4 + ly + off, x] = 3
        # Ripple shading.
        for x in range(23):
            sh = math.cos(x / 3.2 - f * math.pi / 2)
            col = out[:, x]
            if sh < -0.4:
                col[col == 3] = 2
                col[col == 6] = 5
            elif sh > 0.6:
                col[col == 3] = 4
        frames.append(out)
    return frames


def target():
    TK = {"o": 1, "a": 2, "b": 3, "c": 4}
    return [grid("""
.ooooo....ooooo.
.obbbo....obbbo.
.obooo....ooobo.
.obo........obo.
.ooo...oo...ooo.
......obbo......
.....obccbo.....
....obc..cbo....
....obc..cbo....
.....obccbo.....
......obbo......
.ooo...oo...ooo.
.obo........obo.
.obooo....ooobo.
.obbbo....obbbo.
.ooooo....ooooo.
""", TK), grid("""
................
..oooo....oooo..
..oaao....oaao..
..oaoo....ooao..
..oo...oo...oo..
......oaao......
.....oabbao.....
....oab..bao....
....oab..bao....
.....oabbao.....
......oaao......
..oo...oo...oo..
..oaoo....ooao..
..oaao....oaao..
..oooo....oooo..
................
""", TK)]


def snow():
    """Snowflakes, 4x4: a big soft one, a small bright one, a dim one, and a
    streak blown by the wind (flipped for the other way)."""
    return [grid("""
.1..
121.
.21.
....
""", {"1": 1, "2": 2, "3": 3}), grid("""
....
.3..
....
....
""", {"3": 3}), grid("""
....
.2..
.1..
....
""", {"1": 1, "2": 2}), grid("""
....
..13
123.
3...
""", {"1": 1, "2": 2, "3": 3})]


def gust():
    """16x8 clusters of snow driven sideways by a blizzard (blowing west to
    east; flipped for the other way). Several streaks to a sprite, so a
    few sprites fill the air."""
    key = {"1": 1, "2": 2, "3": 3}
    return [grid("""
.........123....
.123............
.......12.......
............123.
...123..........
..........12....
.....123........
123.............
""", key), grid("""
..12............
..........123...
....123.........
.............12.
.12.............
........123.....
..123...........
...........123..
""", key)]


# name, frame w, frame h, frames(), palette
SHEETS = [
    ("chopper", CHOPPER_W, CHOPPER_H, chopper, "CHOPPER"),
    ("hostages", 16, 16, hostages, "HOSTAGE"),
    ("tank", TANK_W, TANK_H, tank, "TANK"),
    ("jet", JET_W, JET_H, jet, "JET"),
    ("balloon", BALLOON_W, BALLOON_H, balloon, "BALLOON"),
    ("bomb", 8, 8, bomb, "FX"),
    ("bullet", 8, 4, bullet, "FX"),
    ("explosion", 32, 32, explosion, "FX"),
    ("smallexplosion", 16, 16, smallexplosion, "FX"),
    ("flags", 24, 16, flags, "FLAG"),
    ("target", 16, 16, target, "TARGET"),
    ("snow", 4, 4, snow, "SNOW"),
    ("gust", 16, 8, gust, "SNOW"),
]
