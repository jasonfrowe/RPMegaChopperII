"""Flies a stage's air waves over its sky at build time, to keep them out
of the towers.

The sky scrolls by a fixed amount for every pixel the ground does, so
where every tower is when each enemy spawns is known in advance. This
replays enemies.c's motion frame by frame (without the steering) and
reports each wave whose enemies would touch a solid sky tile, with the
nearest x that would keep the whole group clear. gen_art.py refuses to
build a stage that has any: move the wave.

Darts are only followed down to where they aim at the player, who could
be anywhere; past that, and in whatever else gets by, the game steers.
"""

import math

PF_W, PF_H = 192, 240
COS8 = [round(127 * math.cos(a * 2 * math.pi / 256)) for a in range(256)]


def sin8(a):
    return COS8[(a - 64) & 255]


# Hitbox half sizes, as etypes[] in enemies.c.
HIT = {"ET_DART": (6, 6), "ET_SAUCER": (7, 6), "ET_DRONE": (7, 7), "ET_GUNSHIP": (14, 13), "ET_WASP": (6, 6)}


def path(kind, x, param, y0):
    """Screen positions (x, y) frame by frame, from spawning until it leaves
    the screen, takes up its station (a drone or gunship, which then holds
    there while the sky slides under it, and steers), or its course
    depends on the player (a dart)."""
    ex, ey, base = x * 16, y0 * 16, x * 16
    vy = 0
    for tt in range(2000):
        if kind == "ET_DART":
            vy = 40
            if ey >= param * 16:
                return
        elif kind == "ET_SAUCER":
            vy = 14
            ex = base + ((COS8[(tt * 3) & 255] * param) >> 3)
        elif kind == "ET_WASP":
            vy = 26
            ex = base + ((sin8((tt * 4) & 255) * param) >> 3)
        elif kind in ("ET_DRONE", "ET_GUNSHIP"):
            vy = 28 if kind == "ET_DRONE" else 12
            if ey >= param * 16:
                return
        else:
            return
        ey += vy
        if ey > (PF_H + 40) * 16:
            return
        yield ex >> 4, ey >> 4


class Sky:
    """A sky map (top row first, as in the bank) and its solid tiles, as
    the game scrolls it."""

    def __init__(self, smap, solid, sky_speed, speed=160):
        self.m, self.solid = smap, set(solid)
        self.rows = smap.shape[0]
        self.sky_q8 = speed * sky_speed // 4
        self.speed = speed

    def top(self, frame):
        return max(0, self.rows * 16 - PF_H - (self.sky_q8 * frame >> 8))

    def frame_at(self, distance):
        """The first frame the ground has scrolled this far."""
        return -(-distance * 256 // self.speed)

    def hit(self, frame, gx, gy):
        if gx < 0 or gx >= PF_W or gy < 0 or gy >= PF_H:
            return False
        return int(self.m[(self.top(frame) + gy) >> 4, gx >> 4]) in self.solid


def _touches(sky, frame, x, y, hw, hh):
    return any(sky.hit(frame, x + dx, y + dy) for dx in (-hw, 0, hw) for dy in (-hh, 0, hh))


def wave_hits(sky, wave, shift=0):
    """How many of a wave's enemies touch a tower on the way."""
    at, kind, _c, x, dx, count, gap, param = wave
    if kind not in HIT:
        return 0
    hw, hh = HIT[kind]
    y0 = -20 if kind == "ET_GUNSHIP" else -12
    f0 = sky.frame_at(at)
    n = 0
    for k in range(count):
        sx = x + shift + k * dx
        spawn = f0 + k * (gap + 1)
        for i, (ex, ey) in enumerate(path(kind, sx, param, y0)):
            if _touches(sky, spawn + i + 1, ex, ey, hw, hh):
                n += 1
                break
    return n


def _span(w, s):
    """The group's left and right edges, weaving and hitboxes included."""
    x, dx, count = w[3] + s, w[4], w[5]
    reach = (w[7] if w[1] in ("ET_SAUCER", "ET_WASP") else 0) + HIT.get(w[1], (8, 8))[0]
    return min(x, x + dx * (count - 1)) - reach, max(x, x + dx * (count - 1)) + reach


def plan(sky, waves):
    """For each wave that hits: (index, wave, hits, fixed wave or None). A
    fix moves the group across first, up to 64 pixels, then later or
    sooner, up to 64 pixels of scroll, by whichever is least."""
    bad = []
    moves = sorted(((s, d) for s in range(-64, 65, 4) for d in range(-64, 65, 8)),
                   key=lambda m: abs(m[0]) + 2 * abs(m[1]))
    for i, w in enumerate(waves):
        hits = wave_hits(sky, w)
        if not hits:
            continue
        fixed = None
        for s, d in moves:
            lo, hi = _span(w, s)
            if lo < 8 or hi > PF_W - 8 or w[0] + d < 100:
                continue
            m = (w[0] + d, w[1], w[2], w[3] + s) + tuple(w[4:])
            if wave_hits(sky, m) == 0:
                fixed = m
                break
        bad.append((i, w, hits, fixed))
    return bad


def report(n, bad):
    lines = [f"stage {n}: air waves fly into solid sky (waves.py):"]
    for i, w, hits, fixed in bad:
        lines.append(f"  wave {i} {w}: {hits} of {w[5]} hit; " + (f"clear at {fixed}" if fixed else "no clear place near"))
    return "\n".join(lines)
