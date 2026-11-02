"""Plane 2 (below the HUD): the ground the game is played on.

One image for the whole 4096-pixel world, cut into 16x16 tiles. Row 0 of
the image is screen row FG_Y; the snow's surface is at screen row
GROUND_LINE. Index 0 is transparent.
"""

from __future__ import annotations

import numpy as np

from .paint import bayer, fbm, wave

T = 16
W = 4096
FG_Y = 96
H = 144
GROUND_LINE = 208
SURF = GROUND_LINE - FG_Y           # image row of the snow's surface

# Compounds: the left column of each, west to east. Hostages come out of
# the door, DOOR_COL tiles in, DOOR_W tiles wide and DOOR_H tall, standing
# on the ground.
COMPOUND_COLS = [18, 75, 138, 196]
COMPOUND_W = 12
DOOR_COL = 5
DOOR_W = 2
DOOR_H = 2

# Home base, at the east end.
PAD_COL0, PAD_COL1 = 234, 244       # helipad, columns [PAD_COL0, PAD_COL1)
FLAG_COL = 245
HANGAR_COL = 247                    # 8 columns wide
HANGAR_DOOR_X = (HANGAR_COL + 3) * T + 8


class Canvas:
    def __init__(self, w, h):
        self.a = np.zeros((h, w), np.uint8)
        self.d = bayer(h, w, 4)

    def rect(self, x0, y0, x1, y1, c):
        """Fill [x0, x1) x [y0, y1), clipped."""
        h, w = self.a.shape
        x0, x1 = max(0, x0), min(w, x1)
        y0, y1 = max(0, y0), min(h, y1)
        if x0 < x1 and y0 < y1:
            self.a[y0:y1, x0:x1] = c

    def px(self, x, y, c):
        h, w = self.a.shape
        if 0 <= x < w and 0 <= y < h:
            self.a[y, x] = c

    def dith(self, x0, y0, x1, y1, ca, cb, amount):
        """Fill with cb showing through ca at `amount` (0..1), ordered."""
        h, w = self.a.shape
        x0, x1 = max(0, x0), min(w, x1)
        y0, y1 = max(0, y0), min(h, y1)
        if x0 < x1 and y0 < y1:
            m = self.d[y0:y1, x0:x1] < amount
            self.a[y0:y1, x0:x1] = np.where(m, cb, ca)

    def box(self, x0, y0, x1, y1, fill, light=None, dark=None, outline=1):
        """A lit block: fill, a light top-left edge, a dark bottom-right
        edge and an outline."""
        self.rect(x0, y0, x1, y1, outline)
        self.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill)
        if light is not None:
            self.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 2, light)
            self.rect(x0 + 1, y0 + 1, x0 + 2, y1 - 1, light)
        if dark is not None:
            self.rect(x0 + 1, y1 - 2, x1 - 1, y1 - 1, dark)
            self.rect(x1 - 2, y0 + 2, x1 - 1, y1 - 1, dark)

    def snowcap(self, x0, x1, y, thick=4, rng=None):
        """Snow lying on a ledge at row y, from x0 to x1, with a soft
        rounded top and a few icicles below."""
        for x in range(x0 - 1, x1 + 1):
            edge = min(x - x0 + 1, x1 - x) + 1
            t = min(thick, edge)
            self.rect(x, y - t, x + 1, y - t + 1, 1)
            self.rect(x, y - t + 1, x + 1, y, 6 if t > 2 else 5)
            if t > 2:
                self.px(x, y - 1, 5)
                self.px(x, y, 4)
        if rng is not None:
            for x in range(x0 + 2, x1 - 2, 3):
                if rng.random() < 0.45:
                    n = int(rng.integers(1, 4))
                    for k in range(n):
                        self.px(x, y + 1 + k, 5 if k < n - 1 else 6)


def ground(c: Canvas, seed):
    """The snow from the surface down: a lit crest, wind-carved drifts, and
    packed snow and ice below. Repeats every 128 pixels."""
    rng = np.random.default_rng(seed)
    P = 128
    g = Canvas(P, H - SURF)
    h = g.a.shape[0]
    yy, xx = np.mgrid[0:h, 0:P]
    d = bayer(h, P, 4)
    v = 0.95 - yy / 22.0 + (d - 0.5) * 0.35
    streak = wave(P, [(2, 1.5), (5, 1.0)], seed)
    for k, y0 in enumerate((5, 9, 13)):
        line = (np.abs(yy - (y0 + streak[None, :] * (k + 1) * 0.6)) < 0.6)
        v = np.where(line & (d < 0.7), v + 0.25, v)
    idx = np.clip(np.round(2 + v * 4), 2, 6).astype(np.uint8)
    idx[0] = 6
    idx[1] = np.where(d[1] < 0.5, 6, 5)
    # Below the crest the snow darkens smoothly with depth, with a few
    # glints of ice.
    deep = yy >= 14
    lv = 0.62 - (yy - 14) / 26.0 + (d - 0.5) * 0.45
    lower = np.clip(np.round(2 + lv * 3), 2, 4).astype(np.uint8)
    idx = np.where(deep, lower, idx)
    for _ in range(6):
        x, y = int(rng.integers(0, P - 3)), int(rng.integers(18, h - 2))
        idx[y, x:x + 3] = 5
        idx[y, x + 1] = 6
    for x0 in range(0, W, P):
        c.a[SURF:, x0:x0 + P] = idx


def drift(c: Canvas, x, w, h):
    """A rounded snow drift on the surface."""
    for dx in range(w):
        t = 1 - abs((dx - w / 2) / (w / 2)) ** 2
        top = int(round(SURF - t * h))
        for y in range(top, SURF + 1):
            c.px(x + dx, y, 6 if y - top < 1 else (5 if y - top < 3 + (dx < w // 2) * 2 else 4))
        c.px(x + dx, top - 1, 1 if t > 0.05 else c.a[top - 1, x + dx])


def rock(c: Canvas, x, w, h, rng):
    """A boulder half buried in snow, with snow on its top."""
    for dx in range(w):
        t = 1 - abs((dx - w / 2) / (w / 2)) ** 1.6
        top = int(round(SURF - t * h))
        for y in range(top, SURF + 2):
            col = 9 if dx < w * 0.45 else 8
            if y == top:
                col = 1
            c.px(x + dx, y, col)
        if t > 0.3:
            c.px(x + dx, top + 1, 6)
            c.px(x + dx, top + 2, 5 if dx < w * 0.6 else 4)
    c.rect(x - 1, SURF, x + w + 1, SURF + 2, 5)


def pine(c: Canvas, x, h, rng):
    """A tall snowy pine with its foot on the surface at column x."""
    base = SURF + 1
    tiers = max(3, h // 10)
    c.rect(x - 1, base - 6, x + 2, base, 1)
    c.rect(x, base - 6, x + 1, base, 8)
    for y in range(base - h, base - 4):
        t = (y - (base - h)) / h
        tier = (t * tiers) % 1.0
        half = (0.8 + t * h * 0.22) * (0.55 + tier * 0.6)
        hw = int(half)
        for dx in range(-hw - 1, hw + 2):
            if abs(dx) == hw + 1:
                if c.a[y, x + dx] == 0:
                    c.px(x + dx, y, 1)
                continue
            col = 12 if dx < -hw * 0.2 else 11
            if dx > hw * 0.5:
                col = 1 if (c.d[y, x + dx] < 0.5) else 11
            if tier < 0.25 and dx < hw * 0.6:
                col = 6 if dx < 0 else 5
            elif tier < 0.4 and dx < -hw * 0.3 and c.d[y, x + dx] < 0.5:
                col = 4
            c.px(x + dx, y, col)
    c.px(x, base - h - 1, 1)


def fence(c: Canvas, x0, x1, rng):
    """Posts and three strands of barbed wire, from x0 to x1."""
    for x in range(x0, x1 + 1, 16):
        c.box(x, SURF - 26, x + 3, SURF + 1, 8, light=9)
        c.snowcap(x, x + 3, SURF - 26, thick=2)
    for k, y in enumerate((SURF - 23, SURF - 15, SURF - 7)):
        for x in range(x0 + 3, x1):
            yy = y + (1 if ((x // 3) + k) % 4 == 0 else 0)
            if c.a[yy, x] in (0,) or c.a[yy, x] >= 2 and c.a[yy, x] <= 6:
                c.px(x, yy, 9 if x % 2 else 7)
            if x % 6 == 0:
                c.px(x, yy - 1, 9)
                c.px(x, yy + 1, 7)


def tower(c: Canvas, x, rng):
    """A guard tower 32 pixels wide on four legs, with a lit searchlight."""
    top = SURF - 76
    cab = top + 6
    # Legs and cross bracing.
    for lx in (x + 3, x + 27):
        c.rect(lx - 1, cab + 18, lx + 2, SURF + 1, 1)
        c.rect(lx, cab + 18, lx + 1, SURF + 1, 8)
    for k in range(3):
        y0 = cab + 18 + k * 18
        for t in range(18):
            c.px(x + 4 + int(t * 22 / 18), y0 + t, 7)
            c.px(x + 26 - int(t * 22 / 18), y0 + t, 7)
    # Cabin.
    c.box(x, cab, x + 31, cab + 20, 8, light=9, dark=7)
    c.rect(x + 4, cab + 5, x + 27, cab + 12, 1)
    c.rect(x + 5, cab + 6, x + 26, cab + 11, 7)
    c.rect(x + 6, cab + 7, x + 12, cab + 10, 15)            # the lamp, lit
    c.rect(x + 7, cab + 8, x + 11, cab + 9, 13)
    c.rect(x + 1, cab + 14, x + 30, cab + 15, 7)
    # Roof with snow.
    c.box(x - 3, top + 1, x + 34, cab + 1, 7, light=8)
    c.snowcap(x - 3, x + 34, top + 1, thick=4, rng=rng)
    c.rect(x + 14, top - 10, x + 15, top - 3, 9)            # aerial
    c.px(x + 14, top - 11, 14)


def bunker(c: Canvas, x0, rng, breached=False):
    """The prison block: concrete, snow on the roof, a reinforced blast
    door in hazard stripes. x0 is the compound's left edge."""
    bx0 = x0 + 2 * T
    bx1 = x0 + 9 * T
    by0 = SURF - 52
    # Body.
    c.box(bx0, by0, bx1, SURF + 1, 9, light=10, dark=8)
    for x in range(bx0 + 16, bx1 - 4, 16):                  # panel seams
        c.rect(x, by0 + 3, x + 1, SURF, 8)
        c.rect(x + 1, by0 + 3, x + 2, SURF, 10)
    for x in range(bx0 + 6, bx1 - 4, 16):                   # rivets
        for y in (by0 + 6, SURF - 6):
            c.px(x, y, 7)
            c.px(x + 1, y - 1, 10)
    # A darker plinth where the walls meet the snow.
    c.rect(bx0 + 1, SURF - 5, bx1 - 1, SURF, 8)
    c.rect(bx0 + 1, SURF - 5, bx1 - 1, SURF - 4, 7)
    # Barred slit windows either side of the door.
    for wx in (bx0 + 8, bx0 + 20, bx1 - 32, bx1 - 20):
        c.box(wx, by0 + 12, wx + 12, by0 + 20, 1)
        c.rect(wx + 1, by0 + 13, wx + 11, by0 + 19, 7)
        for k in range(wx + 3, wx + 11, 3):
            c.rect(k, by0 + 13, k + 1, by0 + 19, 9)
        c.snowcap(wx, wx + 12, by0 + 12, thick=2)
    # Roof slab and snow.
    c.box(bx0 - 4, by0 - 6, bx1 + 4, by0 + 1, 8, light=10, dark=7)
    c.snowcap(bx0 - 4, bx1 + 4, by0 - 6, thick=6, rng=rng)
    # The blast door, DOOR_W x DOOR_H tiles, hazard frame.
    dx0 = x0 + DOOR_COL * T
    dx1 = dx0 + DOOR_W * T
    dy0 = SURF - DOOR_H * T
    for y in range(dy0, SURF):
        for x in range(dx0, dx1):
            if x < dx0 + 3 or x >= dx1 - 3 or y < dy0 + 3:
                c.px(x, y, 13 if ((x - dx0 + y) // 3) % 2 else 1)
    c.rect(dx0, dy0, dx1, dy0 + 1, 1)
    if not breached:
        c.box(dx0 + 3, dy0 + 3, dx1 - 3, SURF, 8, light=9, dark=7)
        c.rect(dx0 + 15, dy0 + 4, dx0 + 17, SURF, 7)         # the seam
        for y in (dy0 + 8, dy0 + 16, dy0 + 24):
            c.rect(dx0 + 4, y, dx1 - 4, y + 1, 7)
            c.rect(dx0 + 4, y + 1, dx1 - 4, y + 2, 10)
        c.box(dx0 + 12, dy0 + 13, dx0 + 20, dy0 + 21, 14, light=13)   # lock
        c.px(dx0 + 16, dy0 + 17, 1)
    else:
        # Blown open: a dark doorway, a twisted door leaf, rubble and soot.
        c.rect(dx0 + 3, dy0 + 3, dx1 - 3, SURF, 1)
        c.dith(dx0 + 5, dy0 + 10, dx1 - 5, SURF - 2, 1, 7, 0.3)
        for k in range(8):                                   # bent leaf
            c.rect(dx0 + 3, dy0 + 6 + k * 3, dx0 + 6 + (k % 3), dy0 + 8 + k * 3, 9 if k % 2 else 8)
        for _ in range(9):
            rx = int(rng.integers(dx0 + 2, dx1 - 5))
            ry = int(rng.integers(SURF - 7, SURF - 2))
            c.box(rx, ry, rx + int(rng.integers(3, 6)), ry + 4, 9, light=10)
        for _ in range(40):                                  # scorch
            sx = int(rng.integers(dx0 - 8, dx1 + 8))
            sy = int(rng.integers(dy0 - 10, SURF - 2))
            if not (dx0 + 3 <= sx < dx1 - 3 and sy >= dy0 + 3) and c.a[sy, sx] in (8, 9, 10, 13):
                c.px(sx, sy, 7 if rng.random() < 0.7 else 1)
    # A red warning lamp over the door.
    c.box(dx0 + 13, dy0 - 7, dx0 + 19, dy0 - 1, 14, light=15 if not breached else 14)


def compound(c: Canvas, col, rng, breached=False):
    x0 = col * T
    fence(c, x0 + 2, x0 + 2 * T - 4, rng)
    bunker(c, x0, rng, breached)
    fence(c, x0 + 9 * T + 4, x0 + 10 * T - 2, rng)
    tower(c, x0 + 10 * T, rng)


def helipad(c: Canvas):
    x0, x1 = PAD_COL0 * T, PAD_COL1 * T
    top = SURF - 3
    c.box(x0, top, x1, SURF + 3, 9, light=10, dark=8)
    for x in range(x0 + 2, x1 - 2):                          # hazard edge
        c.px(x, top + 2, 13 if (x // 4) % 2 else 1)
    for x in range(x0 + 8, x1 - 4, 24):                      # landing lights
        c.rect(x - 1, top - 3, x + 2, top, 1)
        c.px(x, top - 2, 15)
        c.px(x, top - 1, 13)
    c.snowcap(x0, x0 + 10, top, thick=2)
    c.snowcap(x1 - 10, x1, top, thick=2)
    # The H sign on a post at the west end of the pad.
    sx = x0 + 4
    c.rect(sx + 7, SURF - 30, sx + 9, top, 8)
    c.box(sx, SURF - 42, sx + 16, SURF - 28, 13, light=15, dark=1)
    for y in range(SURF - 39, SURF - 31):
        c.px(sx + 5, y, 1)
        c.px(sx + 10, y, 1)
    c.rect(sx + 5, SURF - 36, sx + 11, SURF - 35, 1)
    c.snowcap(sx, sx + 16, SURF - 42, thick=2)


def flagpole(c: Canvas):
    x = FLAG_COL * T + 4
    c.rect(x - 1, SURF - 90, x + 2, SURF + 1, 1)
    c.rect(x, SURF - 90, x + 1, SURF + 1, 10)
    c.box(x - 3, SURF - 93, x + 4, SURF - 89, 13, light=15)
    c.box(x - 6, SURF - 4, x + 7, SURF + 1, 8, light=9)


def hangar(c: Canvas, rng):
    """The medical station: a quonset hut with a red cross, an open lit
    door the rescued run into, and a radio mast."""
    x0 = HANGAR_COL * T
    x1 = x0 + 8 * T
    wall = SURF - 40
    # Arched roof, corrugated.
    for x in range(x0, x1):
        t = (x - x0) / (x1 - x0 - 1)
        top = int(round(wall - 22 * np.sin(np.pi * t)))
        for y in range(top, wall + 1):
            col = 10 if (x // 3) % 2 else 9
            if t > 0.55:
                col = 9 if (x // 3) % 2 else 8
            c.px(x, y, col)
        c.px(x, top, 1)
        # Snow on the crest.
        if 0.15 < t < 0.85:
            c.px(x, top - 1, 1)
            c.px(x, top, 6)
            c.px(x, top + 1, 5 if t < 0.5 else 4)
    c.rect(x0, wall, x1, wall + 2, 1)
    # Walls: white panels.
    c.box(x0 + 2, wall + 1, x1 - 2, SURF + 1, 5, light=6, dark=4)
    for x in range(x0 + 18, x1 - 4, 18):
        c.rect(x, wall + 3, x + 1, SURF, 4)
    # Red cross sign.
    cx, cy = x0 + 100, wall + 6
    c.box(cx, cy, cx + 20, cy + 20, 6, dark=4)
    c.rect(cx + 8, cy + 3, cx + 12, cy + 17, 14)
    c.rect(cx + 3, cy + 8, cx + 17, cy + 12, 14)
    # Lit windows.
    for wx in (x0 + 8, x0 + 76):
        c.box(wx, wall + 8, wx + 14, wall + 18, 1)
        c.rect(wx + 1, wall + 9, wx + 13, wall + 17, 15)
        c.rect(wx + 1, wall + 13, wx + 13, wall + 14, 13)
        c.rect(wx + 7, wall + 9, wx + 8, wall + 17, 1)
    # The open door, warm light spilling out.
    dx = HANGAR_DOOR_X - 10
    c.box(dx, SURF - 28, dx + 22, SURF + 1, 15, dark=13)
    c.rect(dx + 3, SURF - 25, dx + 19, SURF, 13)
    c.dith(dx + 3, SURF - 25, dx + 19, SURF, 15, 13, 0.5)
    c.rect(dx - 2, SURF - 31, dx + 24, SURF - 28, 14)        # awning
    c.snowcap(dx - 2, dx + 24, SURF - 31, thick=2)
    c.dith(dx - 6, SURF, dx + 28, SURF + 3, 6, 15, 0.35)     # light on the snow
    # Radio mast at the far end.
    mx = x1 - 6
    for y in range(SURF - 104, wall):
        c.px(mx - 1, y, 1)
        c.px(mx, y, 9 if y % 6 else 10)
        c.px(mx + 1, y, 1)
    c.px(mx, SURF - 106, 14)
    c.px(mx, SURF - 105, 15)


def paint(seed=21):
    rng = np.random.default_rng(seed)
    c = Canvas(W, H)
    ground(c, seed)
    busy = []
    for col in COMPOUND_COLS:
        compound(c, col, np.random.default_rng(seed + 5))
        busy.append((col * T - 24, (col + COMPOUND_W) * T + 24))
    helipad(c)
    flagpole(c)
    hangar(c, rng)
    busy.append((PAD_COL0 * T - 40, W))

    def free(x0, x1):
        return all(x1 < a or x0 > b for a, b in busy)

    # Scenery: stands of pines, drifts and rocks in the open ground. The
    # first 64 pixels and the area around every building stay clear.
    x = 80
    while x < PAD_COL0 * T - 80:
        r = rng.random()
        if r < 0.32 and free(x - 16, x + 90):
            n = int(rng.integers(2, 6))
            for k in range(n):
                pine(c, x + k * int(rng.integers(12, 20)), int(rng.integers(34, 70)), rng)
            busy.append((x - 16, x + n * 20 + 16))
            x += n * 20 + int(rng.integers(40, 120))
        elif r < 0.5 and free(x, x + 30):
            drift(c, x, int(rng.integers(20, 40)), int(rng.integers(3, 6)))
            x += int(rng.integers(60, 140))
        elif r < 0.65 and free(x, x + 24):
            rock(c, x, int(rng.integers(10, 22)), int(rng.integers(5, 10)), rng)
            x += int(rng.integers(60, 140))
        else:
            x += int(rng.integers(40, 100))

    # The breached door, painted on a copy of the first compound.
    b = Canvas(W, H)
    b.a[:] = c.a
    col = COMPOUND_COLS[0]
    bunker(b, col * T, np.random.default_rng(seed + 5), breached=True)
    x0 = (col + DOOR_COL) * T
    door_open = b.a[SURF - DOOR_H * T:SURF, x0:x0 + DOOR_W * T].copy()
    # Also the warning lamp above the door goes dark; that is in the tile row
    # above the door, so take that row too.
    above = b.a[SURF - (DOOR_H + 1) * T:SURF - DOOR_H * T, x0:x0 + DOOR_W * T].copy()
    return c.a, np.vstack([above, door_open])
