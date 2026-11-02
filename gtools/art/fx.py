"""Projectiles, the radiant sword and explosions: procedural, radial art."""

import math

import numpy as np

from kit import value_noise


def _radial(size, cx, cy, r, ramp, sx=1.0, sy=1.0):
    """Glowing blob: ramp[0] at the rim to ramp[-1] at the center."""
    f = np.zeros((size[1], size[0]), dtype=np.uint8)
    yy, xx = np.mgrid[0:size[1], 0:size[0]]
    d = np.sqrt(((xx + 0.5 - cx) / sx) ** 2 + ((yy + 0.5 - cy) / sy) ** 2) / r
    for i, idx in enumerate(ramp):
        t = 1.0 - i / len(ramp)
        f[d <= t] = idx
    return f


VULCAN_ART = [
    # Frame 0: Left bolt leads, right bolt trails
    [
        "........",
        ".11.....",
        ".44..11.",
        ".55..44.",
        ".55..55.",
        ".54..55.",
        ".54..54.",
        ".54..54.",
        ".44..54.",
        ".43..44.",
        ".33..43.",
        ".33..33.",
        ".22..33.",
        ".11..22.",
        ".....11.",
        "........",
    ],
    # Frame 1: Right bolt leads, left bolt trails
    [
        "........",
        ".....11.",
        ".11..44.",
        ".44..55.",
        ".55..55.",
        ".55..54.",
        ".54..54.",
        ".54..54.",
        ".54..44.",
        ".44..43.",
        ".43..33.",
        ".33..33.",
        ".33..22.",
        ".22..11.",
        ".11.....",
        "........",
    ],
]


def vulcan_frames():
    """8x16: twin alternating laser bolts in Atari arcade shmup style. Shots palette 2-5."""
    frames = []
    for art in VULCAN_ART:
        f = np.zeros((16, 8), dtype=np.uint8)
        for y, row in enumerate(art):
            for x, ch in enumerate(row):
                if ch != ".":
                    f[y, x] = int(ch, 16)
        frames.append(f)
    return frames


SHOT8_ART = [
    # 0: SPREAD 0 (pulsing orange orb, large)
    [
        "........",
        "..6776..",
        ".689986.",
        ".795597.",
        ".795597.",
        ".689986.",
        "..6776..",
        "........",
    ],
    # 1: SPREAD 1 (pulsing orange orb, small/concentrated)
    [
        "........",
        "........",
        "..7887..",
        ".795597.",
        ".795597.",
        "..7887..",
        "........",
        "........",
    ],
    # 2: HOMING 0 (green emerald diamond, large)
    [
        "........",
        "...AA...",
        "..ABBA..",
        ".AC55CA.",
        ".AC55CA.",
        "..ABBA..",
        "...AA...",
        "........",
    ],
    # 3: HOMING 1 (green emerald diamond, small/hot)
    [
        "........",
        "........",
        "...AA...",
        "..AC5A..",
        "..A5CA..",
        "...AA...",
        "........",
        "........",
    ],
    # 4: SPARK 0 (violet crackling plasma arc, phase A)
    [
        "........",
        "..1EF1..",
        "...1FE1.",
        "..1EF1..",
        ".1FE1...",
        "..1EF1..",
        "...11...",
        "........",
    ],
    # 5: SPARK 1 (violet crackling plasma arc, phase B)
    [
        "........",
        "...11...",
        "..1FE1..",
        ".1EF1...",
        "..1EF1..",
        "...1FE1.",
        "..1EF1..",
        "........",
    ],
    # 6: BACK 0 (cyan defensive bullet, long)
    [
        "........",
        "..1441..",
        "..1551..",
        "..1551..",
        "..1441..",
        "..1331..",
        "..1221..",
        "........",
    ],
    # 7: BACK 1 (cyan defensive bullet, pulse)
    [
        "........",
        "........",
        "..1551..",
        "..1551..",
        "..1441..",
        "..1331..",
        "..1221..",
        "........",
    ],
]


def shot8_frames():
    """8x8 player shots in Atari arcade shmup style. Order: spread x2, homing x2, spark x2, back x2."""
    return [_grid(rows) for rows in SHOT8_ART]


def sword_frames():
    """48x32 radiant sword sweep above the ship (ship at bottom center).

    A bright arc of blade energy rotating through 4 frames with 0 border touches.
    """
    w, h = 48, 32
    cx, cy = 23.5, 31.5
    frames = []
    center_angs = [math.pi * 0.68, math.pi * 0.58, math.pi * 0.44, math.pi * 0.32]

    for f_idx, c_ang in enumerate(center_angs):
        f = np.zeros((h, w), dtype=np.uint8)
        span = math.radians(110)
        a_min = c_ang - span / 2.0
        a_max = c_ang + span / 2.0

        for y in range(h):
            for x in range(w):
                if x == 0 or x == w - 1 or y == 0 or y == h - 1:
                    continue
                dx = x - cx
                dy = cy - y
                dist = math.hypot(dx, dy)
                ang = math.atan2(dy, dx)
                r_dist = abs(dist - 20.0)
                in_arc = a_min <= ang <= a_max

                if in_arc and r_dist <= 5.5:
                    rel_a = (ang - a_min) / span
                    trail_fade = math.sin(rel_a * math.pi)
                    spark = math.sin((x * 5 + y * 7 + f_idx * 13) * 0.5)

                    if r_dist <= 1.2 and trail_fade > 0.2:
                        f[y, x] = 5
                    elif r_dist <= 2.4 and trail_fade > 0.1:
                        f[y, x] = 4
                    elif r_dist <= 4.0:
                        f[y, x] = 3 if spark < 0.6 else 15
                    elif r_dist <= 5.0:
                        f[y, x] = 2
                    else:
                        f[y, x] = 1
        frames.append(f)
    return frames


def _grid(rows):
    f = np.zeros((len(rows), len(rows[0])), dtype=np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                f[y, x] = int(ch, 16)
    return f


def bullet8_frames():
    """8x8 enemy bullets, palette 1-5. Order: small orb x2, needle x2."""
    grids = [
        [
            "..1111..",
            ".124421.",
            "12455421",
            "13555431",
            "12344321",
            "12333221",
            ".122221.",
            "..1111..",
        ],
        [
            "..1221..",
            ".134431.",
            "13555531",
            "24555542",
            "23455432",
            "13444431",
            ".123321.",
            "..1221..",
        ],
        [
            "...11...",
            "..1221..",
            ".123321.",
            "12344321",
            ".135531.",
            "..1551..",
            "..1441..",
            "...33...",
        ],
        [
            "...11...",
            "..1331..",
            ".134431.",
            "13455431",
            ".145541.",
            "..1551..",
            "..1441..",
            "...33...",
        ],
    ]
    return [_grid(g) for g in grids]


def bullet16_frames():
    """16x16 big orbs, 2 pulse frames with horizontal scanline energy bands."""
    grids = [
        [
            "................",
            ".....111111.....",
            "...1123443211...",
            "..123445544321..",
            ".12334555543321.",
            ".12445555554421.",
            ".12345555554321.",
            ".12445555554421.",
            ".12334455443321.",
            ".12344444444321.",
            ".12233344333221.",
            ".12233333333221.",
            "..122222222221..",
            "...1122222211...",
            ".....111111.....",
            "................",
        ],
        [
            "................",
            ".....112211.....",
            "...1134554311...",
            "..123455554321..",
            ".12445555554421.",
            ".13455555555431.",
            ".13455555555431.",
            ".12455555555421.",
            ".13445555554431.",
            ".12344555544321.",
            ".12344444444321.",
            ".12233444433221.",
            "..122333333221..",
            "...1122332211...",
            ".....112211.....",
            "................",
        ],
    ]
    return [_grid(g) for g in grids]


def explosion_frames(size, seed=0, count=6):
    """Fireball that blooms then breaks into smoke in Atari arcade shmup style.

    Zero border touches to avoid clipping in 16x16 and 32x32 sprites.
    """
    mid = (size - 1) / 2.0
    frames = []
    lobe_angles = [0.2, 1.3, 2.1, 3.4, 4.3, 5.5]
    max_safe_r = (size / 2.0) - 1.5

    for k in range(count):
        grid = np.zeros((size, size), dtype=np.uint8)
        if k == 0:
            for y in range(size):
                for x in range(size):
                    d = math.hypot(x - mid, y - mid)
                    flare = max(0.0, 1.0 - abs(x - mid) * 0.35) * max(0.0, 1.0 - abs(y - mid) * 0.9) + \
                            max(0.0, 1.0 - abs(y - mid) * 0.35) * max(0.0, 1.0 - abs(x - mid) * 0.9)
                    if d <= max_safe_r * 0.3:
                        grid[y, x] = 8
                    elif d <= max_safe_r * 0.55 or flare > 0.4:
                        grid[y, x] = 7 if (d <= max_safe_r * 0.4 or flare > 0.7) else 6
        elif k == 1:
            r_outer = max_safe_r * 0.72
            for y in range(size):
                for x in range(size):
                    d = math.hypot(x - mid, y - mid)
                    ang = math.atan2(y - mid, x - mid)
                    wob = math.sin(ang * 5) * 0.15 + math.cos(ang * 3) * 0.1
                    r_eff = r_outer * (1.0 + wob)
                    if d <= r_eff:
                        rel = d / r_eff
                        if rel <= 0.28:
                            grid[y, x] = 8
                        elif rel <= 0.52:
                            grid[y, x] = 7
                        elif rel <= 0.75:
                            grid[y, x] = 6
                        elif rel <= 0.90:
                            grid[y, x] = 5
                        else:
                            grid[y, x] = 4
        elif k == 2:
            r_outer = max_safe_r * 0.96
            for y in range(size):
                for x in range(size):
                    d = math.hypot(x - mid, y - mid)
                    ang = math.atan2(y - mid, x - mid)
                    wob = math.cos(ang * 6) * 0.18 + math.sin(ang * 2) * 0.08
                    r_eff = r_outer * (0.85 + wob)
                    if d <= r_eff and d <= max_safe_r:
                        rel = d / r_eff
                        if rel <= 0.22:
                            grid[y, x] = 7
                        elif rel <= 0.48:
                            grid[y, x] = 6
                        elif rel <= 0.72:
                            grid[y, x] = 5
                        elif rel <= 0.90:
                            grid[y, x] = 4
                        else:
                            grid[y, x] = 1
        elif k == 3:
            lobes = [(mid + math.cos(a) * max_safe_r * 0.52, mid + math.sin(a) * max_safe_r * 0.52, max_safe_r * 0.44) for a in lobe_angles]
            for y in range(size):
                for x in range(size):
                    d_center = math.hypot(x - mid, y - mid)
                    if d_center > max_safe_r:
                        continue
                    min_lobe_d = min(math.hypot(x - lx, y - ly) / lr for lx, ly, lr in lobes)
                    if min_lobe_d <= 1.0:
                        if min_lobe_d <= 0.35:
                            grid[y, x] = 6
                        elif min_lobe_d <= 0.65:
                            grid[y, x] = 5
                        elif min_lobe_d <= 0.88:
                            grid[y, x] = 4
                        else:
                            grid[y, x] = 1
                    elif d_center <= max_safe_r * 0.45:
                        grid[y, x] = 9 if (x + y) % 2 == 0 else 2
        elif k == 4:
            lobes = [(mid + math.cos(a) * max_safe_r * 0.70, mid + math.sin(a) * max_safe_r * 0.70, max_safe_r * 0.32) for a in lobe_angles]
            for y in range(size):
                for x in range(size):
                    d_center = math.hypot(x - mid, y - mid)
                    if d_center > max_safe_r:
                        continue
                    min_lobe_d = min(math.hypot(x - lx, y - ly) / lr for lx, ly, lr in lobes)
                    if min_lobe_d <= 1.0:
                        if min_lobe_d <= 0.4:
                            grid[y, x] = 3 if (x ^ y) % 3 == 0 else 4
                        elif min_lobe_d <= 0.8:
                            grid[y, x] = 9 if (x + y) % 2 == 0 else 10
                        else:
                            grid[y, x] = 1
            for i, a in enumerate(lobe_angles):
                sx = int(round(mid + math.cos(a + 0.3) * max_safe_r * 0.88))
                sy = int(round(mid + math.sin(a + 0.3) * max_safe_r * 0.88))
                if 1 <= sx < size - 1 and 1 <= sy < size - 1:
                    grid[sy, sx] = 15 if i % 2 == 0 else 12
        elif k == 5:
            lobes = [(mid + math.cos(a) * max_safe_r * 0.82, mid + math.sin(a) * max_safe_r * 0.82, max_safe_r * 0.22) for a in lobe_angles]
            for y in range(size):
                for x in range(size):
                    d_center = math.hypot(x - mid, y - mid)
                    if d_center > max_safe_r:
                        continue
                    min_lobe_d = min(math.hypot(x - lx, y - ly) / lr for lx, ly, lr in lobes)
                    if min_lobe_d <= 1.0:
                        if (x * 3 + y * 7) % 4 == 0:
                            grid[y, x] = 1
                        elif (x * 5 + y * 3) % 4 == 0:
                            grid[y, x] = 2
            for i, a in enumerate(lobe_angles):
                sx = int(round(mid + math.cos(a) * max_safe_r * 0.92))
                sy = int(round(mid + math.sin(a) * max_safe_r * 0.92))
                if 1 <= sx < size - 1 and 1 <= sy < size - 1:
                    grid[sy, sx] = 3 if i % 2 == 0 else 15

        for i in range(size):
            grid[0, i] = 0
            grid[size - 1, i] = 0
            grid[i, 0] = 0
            grid[i, size - 1] = 0

        frames.append(grid)
    return frames


def beam_frames():
    """32x64 hyper sword beam segment, tiles vertically. Shots palette."""
    out = []
    for frame in range(2):
        f = np.zeros((64, 32), dtype=np.uint8)
        phase = 0 if frame == 0 else 8
        for y in range(64):
            t = ((y + phase) % 16) / 16.0 * 2.0 * math.pi
            node = math.cos(t)
            r_core = 2.4 + 1.2 * (node + 1) / 2.0
            r_pale = 4.2 + 2.2 * (node + 1) / 2.0
            r_cyan = 6.5 + 3.0 * (node + 1) / 2.0
            r_deep = 8.5 + 3.2 * (node + 1) / 2.0
            r_edge = 9.8 + 2.8 * (node + 1) / 2.0

            rib = 0.4 if (y % 2 == 1) else 0.0

            for x in range(32):
                dx = abs(x - 15.5)
                spark = math.sin((y * 7 + frame * 11) * 0.4) * math.cos(x * 1.3)
                if dx <= r_core - rib:
                    f[y, x] = 5
                elif dx <= r_pale:
                    f[y, x] = 4
                elif dx <= r_cyan:
                    f[y, x] = 3
                elif dx <= r_deep:
                    if dx > r_cyan + 0.5 and spark > 0.65:
                        f[y, x] = 15 if spark > 0.85 else 14
                    else:
                        f[y, x] = 2
                elif dx <= r_edge:
                    if spark > 0.7:
                        f[y, x] = 14
                    else:
                        f[y, x] = 1
        out.append(f)
    return out


MISSILE_ART = [
    # 0: Right (+x)
    [
        "........",
        "........",
        "..17....",
        ".388951.",
        ".388951.",
        "..17....",
        "........",
        "........",
    ],
    # 1: Down-Right (+x, +y)
    [
        "........",
        ".31.....",
        ".178....",
        "..889...",
        "...951..",
        "....11..",
        "........",
        "........",
    ],
    # 2: Down (+y)
    [
        "........",
        "..33....",
        "..11....",
        ".7887...",
        "..88....",
        "..99....",
        "..551...",
        "........",
    ],
    # 3: Down-Left (-x, +y)
    [
        "........",
        ".....13.",
        "....871.",
        "...988..",
        "..159...",
        "..11....",
        "........",
        "........",
    ],
    # 4: Left (-x)
    [
        "........",
        "........",
        "....71..",
        ".159883.",
        ".159883.",
        "....71..",
        "........",
        "........",
    ],
    # 5: Up-Left (-x, -y)
    [
        "........",
        "..11....",
        "..159...",
        "...988..",
        "....871.",
        ".....13.",
        "........",
        "........",
    ],
    # 6: Up (-y)
    [
        "........",
        "..551...",
        "..99....",
        "..88....",
        ".7887...",
        "..11....",
        "..33....",
        "........",
    ],
    # 7: Up-Right (+x, -y)
    [
        "........",
        "....11..",
        "...951..",
        "..889...",
        ".178....",
        ".31.....",
        "........",
        "........",
    ],
]


def missile_frames():
    """8x8 missile pointing in 8 directions (0 right, 64 down), Shots palette, 0 border touches."""
    return [_grid(rows) for rows in MISSILE_ART]


def lock_frames():
    """16x16 lock-on reticle, 2 frames (brackets pulse in). Shots palette, 0 border touches."""
    out = []
    for f_idx in range(2):
        f = np.zeros((16, 16), dtype=np.uint8)
        inset = 1 if f_idx == 0 else 3
        lo, hi = inset, 15 - inset
        for (cx, cy, sx, sy) in ((lo, lo, 1, 1), (hi, lo, -1, 1), (lo, hi, 1, -1), (hi, hi, -1, -1)):
            for i in range(4 if f_idx == 0 else 3):
                f[cy, cx + sx * i] = 4
                f[cy + sy * i, cx] = 4
            f[cy, cx] = 5
        f[7, 7] = 8
        f[7, 8] = 9
        f[8, 7] = 9
        f[8, 8] = 8
        out.append(f)
    return out
