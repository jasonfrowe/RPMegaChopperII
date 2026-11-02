"""Player ship and its effects."""

import numpy as np

from kit import Material, Sprite, value_noise

PLAYER_MATS = {
    "hull": Material([2, 3, 4, 5]),
    "dark": Material([1, 2, 3]),
    "blue": Material([6, 7, 8]),
    "canopy": Material([9, 10, 5], dither=0.2),
    "trim": Material([15], shaded=False),
    "glow": Material([12, 13], shaded=False),
}


# Atari-style 24x24 4bpp starfighter frames (0=transparent, 1=shadow,
# 2-5=silver hull dark->bright, 6-8=blue scanline bands, 9-A=cockpit glass,
# B-E=engine glow, F=crimson red cannon/stripe accents).
# Twin engine nozzles at y=20..21 align with flame_l={4,5,6}, flame_r={11,10,9}.
PLAYER_ART = [
    # Frame 0: center (symmetric across x=11|12)
    [
        "...........11...........",
        "..........1FF1..........",
        "..........1551..........",
        ".........145541.........",
        ".........145541.........",
        "........134AA431........",
        "........13AAAA31........",
        ".......1349AA9431.......",
        "......134549945431......",
        ".1FF1.135545545531.1FF1.",
        ".1541134884554884311451.",
        ".1433488884554888843341.",
        "134347777745547777743431",
        "13447777774FF47777774431",
        "13556666664FF46666665531",
        "124544444445544444445421",
        "123FF33333455433333FF321",
        "123221111234432111122321",
        ".111.....124421.....111.",
        ".......1123443211.......",
        "......123321123321......",
        "......1211....1121......",
        "........................",
        "........................",
    ],
    # Frame 1: medium bank right (left wing wider/brighter, right wing narrower & flush)
    [
        "............11..........",
        "...........1FF1.........",
        "...........1551.........",
        "..........145531........",
        "..........145531........",
        ".........134AA31........",
        ".........14AAAA21.......",
        "........1349AA931.......",
        ".......13454994321......",
        "..1FF1.135545544211FF1..",
        "..15411348845548321431..",
        "..14334888845548732321..",
        ".1344477777455477633221.",
        ".13557777774FF476633221.",
        ".13556666664FF466443221.",
        ".1245444444455444333221.",
        ".123FF333334554333FF221.",
        ".123221111234432112221..",
        "..111.....124421..111...",
        "........112343211.......",
        ".......12332123321......",
        ".......1211..1121.......",
        "........................",
        "........................",
    ],
    # Frame 2: steep bank right (left wing full profile, right wing foreshortened & flush)
    [
        "............11..........",
        "...........1FF1.........",
        "...........1541.........",
        "..........145421........",
        "..........145421........",
        ".........145AA21........",
        ".........14AAA31........",
        "........1359AA321.......",
        ".......1355499421.......",
        "...1FF113555554311FF1...",
        "...154134888554721431...",
        "...143488888554762321...",
        "..13557777775546633221..",
        "..1355777777FF46633221..",
        "..1355666666FF44433221..",
        "..12454444445543332221..",
        "..123FF3333355322FF221..",
        "..1232211112343212221...",
        "...111.....12431.111....",
        ".........11233321.......",
        "........123312321.......",
        "........1211.1121.......",
        "........................",
        "........................",
    ],
]


def player_sprite() -> Sprite:
    return Sprite(24, 24)


def player_frames():
    """Center, bank 1, bank 2 (rolling right). Left bank is the same frames flipped."""
    frames = []
    for rows in PLAYER_ART:
        f = np.zeros((24, 24), dtype=np.uint8)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    f[y, x] = int(ch, 16)
        frames.append(f)
    return frames


def flame_frames():
    """8x8 engine flame below each nacelle pair, 4 frames of flicker.

    Uses the player palette's engine entries 11-14 (11 red outer, 14 white core).
    """
    frames = []
    lengths = [6, 8, 5, 7]
    for i, ln in enumerate(lengths):
        f = np.zeros((8, 8), dtype=np.uint8)
        for y in range(ln):
            t = y / max(1, ln - 1)
            half = 1.6 * (1 - t) + 0.4
            for x in range(8):
                dx = abs(x - 3.5)
                if dx <= half + 0.5:
                    core = dx / (half + 0.5)
                    v = (1 - t) * 0.7 + (1 - core) * 0.6
                    if v > 0.95:
                        f[y, x] = 14
                    elif v > 0.7:
                        f[y, x] = 13
                    elif v > 0.45:
                        f[y, x] = 12
                    else:
                        f[y, x] = 11
        frames.append(f)
    return frames
