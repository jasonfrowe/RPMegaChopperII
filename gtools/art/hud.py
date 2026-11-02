"""HUD sprites, drawn on plane 2 in front of the text panels.

  mini_ship()     16x16 ship for the lives count (palette PLAYER)
  gems()          8x8 chain gems, unlit and lit (an enemy palette colours them)
  weapon_icons()  16x16 icon per weapon id, 0 to 9 (palette SHOTS)
"""

import math

from kit import Material, Shape, Sprite
from ships import PLAYER_MATS, player_sprite


def mini_ship():
    """16x16 Atari-style starfighter icon for the HUD lives count (palette PLAYER)."""
    import numpy as np
    rows = [
        ".......11.......",
        "......1FF1......",
        "......1551......",
        ".....14AA41.....",
        ".....13AA31.....",
        "....13499431....",
        ".1F1134554311F1.",
        ".14348855884341.",
        "1344777FF7774431",
        "1355666FF6665531",
        "1244444554444421",
        "123FF334433FF321",
        ".111.124421.111.",
        "....12311321....",
        "....1BB11BB1....",
        ".....11..11.....",
    ]
    f = np.zeros((16, 16), dtype=np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                f[y, x] = int(ch, 16)
    return [f]


GEM_MATS = {
    "paint": Material([6, 7, 8, 9]),
    "dark": Material([2, 3]),
    "white": Material([15], shaded=False),
}


def gems():
    """A cut gem: frame 0 unlit (dark facets), frame 1 lit with a glint."""
    out = []
    for lit in (False, True):
        s = Sprite(8, 8)
        s.poly([(4, 0), (8, 4), (4, 8), (0, 4)], "paint" if lit else "dark", amp=1.6, bevel=2.5)
        if lit:
            s.dot(3, 2, "white", z=3)
        out.append(s.render(GEM_MATS, gloss=0.6))
    return out


ICON_MATS = {
    "cyan": Material([1, 2, 3, 4]),
    "white": Material([5], shaded=False),
    "orange": Material([6, 7, 8, 9]),
    "green": Material([10, 11, 12, 13]),
    "violet": Material([14, 15], dither=0.0),
}


def _icon(draw):
    s = Sprite(16, 16)
    draw(s)
    return s.render(ICON_MATS, gloss=0.5)


def weapon_icons():
    """16x16 weapon icons (0..9) in SHOTS palette, framed inside 1..14 with no edge clipping."""
    import numpy as np
    vulcan = [
        "................",
        "...11......11...",
        "..1451....1451..",
        "..1451....1451..",
        ".134531..134531.",
        ".123521..123521.",
        ".134531..134531.",
        ".123521..123521.",
        ".134531..134531.",
        ".123421..123421.",
        ".134431..134431.",
        ".123321..123321.",
        "..1221....1221..",
        "..1111....1111..",
        "................",
        "................",
    ]
    grids = [
        ["................"] * 16,
        vulcan,
        [
            "................",
            ".........AA..AA.",
            "........AC555CA.",
            "........AD555DA.",
            "........AC555CA.",
            ".......ACCBDAA..",
            "......ACBA..A...",
            ".....ACBA.......",
            "...AA.AA........",
            "..ACCA..........",
            ".AC55CA.........",
            ".AD55DA.........",
            "..ACCA..........",
            "...AA...........",
            "................",
            "................",
        ],
        [
            "................",
            ".....111111.....",
            "....12455421....",
            "....13455431....",
            ".....123321.....",
            "......1EE1......",
            ".....1E55E1.....",
            "....1E5FF1......",
            ".....11E5E1.....",
            ".......1E55E1...",
            "......1E5FFE1...",
            ".....1E5F111....",
            "....1E5E1.......",
            "....124421......",
            ".....1111.......",
            "................",
        ],
        [
            "................",
            "......6666......",
            ".....689986.....",
            "..66.678876.66..",
            ".6896.6666.6986.",
            ".6786......6876.",
            "..66........66..",
            ".66..........66.",
            "6896........6986",
            "6786..6666..6876",
            ".66..689986..66.",
            "....68955986....",
            "....67955976....",
            ".....678876.....",
            "......6666......",
            "................",
        ],
        [
            "................",
            "......1111......",
            ".....135531.....",
            ".....135531.....",
            ".....124421.....",
            ".....123321.....",
            ".66...1221...66.",
            "6896..1441..6986",
            "6786.135531.6876",
            ".66..124421..66.",
            "......1111......",
            "...66......66...",
            "..6896....6986..",
            "..6786....6876..",
            "...66......66...",
            "................",
        ],
        [
            "................",
            ".AAAA..66..AAAA.",
            ".ACCC.6896.CCCA.",
            ".AC..685586..CA.",
            ".AA..678876..AA.",
            ".....689986.....",
            ".....678876.....",
            "....66899866....",
            "...6788998876...",
            "...6897887986...",
            "...6666776666...",
            ".AA...6336...AA.",
            ".AC...1451...CA.",
            ".ACCC..11..CCCA.",
            ".AAAA......AAAA.",
            "................",
        ],
        vulcan,
        [
            "................",
            ".......11.......",
            "......1451......",
            ".....135531.....",
            ".....145541.....",
            ".....135531.....",
            ".....145541.....",
            ".....135531.....",
            ".....124421.....",
            "..666613316666..",
            ".68999955999986.",
            ".67888899888876.",
            "..666668866666..",
            ".....689986.....",
            "......6666......",
            "................",
        ],
        [
            "................",
            ".....EE11EE.....",
            "...EE114511EE...",
            "..EF51355315FE..",
            ".EFF11455411FFE.",
            ".EF1.135531.1FE.",
            ".EF5.145541.5FE.",
            ".EFF.135531.FFE.",
            ".EF1.124421.1FE.",
            ".E666613316666E.",
            ".68999955999986.",
            ".67888899888876.",
            "..E6666886666E..",
            "...EE689986EE...",
            "......6666......",
            "................",
        ],
    ]
    out = []
    for g in grids:
        f = np.zeros((16, 16), dtype=np.uint8)
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                if ch != ".":
                    f[y, x] = int(ch, 16)
        out.append(f)
    return out


# Classic Atari 2600 / Activision 6x7 geometric score digits, doubled
# vertically with scanline color banding in 8x16 cells.
DIGIT_ART = [
    [
        ".####.",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        "##..##",
        ".####.",
    ],
    [
        "..##..",
        ".###..",
        "..##..",
        "..##..",
        "..##..",
        "..##..",
        ".####.",
    ],
    [
        ".####.",
        "##..##",
        "....##",
        ".####.",
        "##....",
        "##....",
        "######",
    ],
    [
        ".####.",
        "##..##",
        "....##",
        "..###.",
        "....##",
        "##..##",
        ".####.",
    ],
    [
        "##..##",
        "##..##",
        "##..##",
        "######",
        "....##",
        "....##",
        "....##",
    ],
    [
        "######",
        "##....",
        "#####.",
        "....##",
        "....##",
        "##..##",
        ".####.",
    ],
    [
        ".####.",
        "##....",
        "#####.",
        "##..##",
        "##..##",
        "##..##",
        ".####.",
    ],
    [
        "######",
        "##..##",
        "....##",
        "...##.",
        "..##..",
        "..##..",
        "..##..",
    ],
    [
        ".####.",
        "##..##",
        "##..##",
        ".####.",
        "##..##",
        "##..##",
        ".####.",
    ],
    [
        ".####.",
        "##..##",
        "##..##",
        ".#####",
        "....##",
        "##..##",
        ".####.",
    ],
]


def digits(gold):
    """0-9 in 8x16 cells: classic Atari 2600 blocky 7-row digits with
    TIA-style horizontal scanline color bands (palette SHOTS)."""
    import numpy as np
    if gold:
        bands = [(9, 8), (9, 8), (8, 7), (8, 7), (8, 7), (7, 6), (8, 6)]
    else:
        bands = [(5, 4), (4, 3), (4, 3), (3, 2), (3, 2), (2, 1), (3, 1)]
    out = []
    for art in DIGIT_ART:
        f = np.zeros((16, 8), dtype=np.uint8)
        for r, row in enumerate(art):
            c_top, c_bot = bands[r]
            y0 = 1 + r * 2
            for x, c in enumerate(row):
                if c == "#":
                    f[y0, x + 1] = c_top
                    f[y0 + 1, x + 1] = c_bot
        out.append(f)
    return out


# 10x7 Atari 2600 / Activision style capitals and digits for the stage/warning banners.
GLYPHS = {
    "S": [
        ".########.",
        "###....###",
        "###.......",
        ".########.",
        ".......###",
        "###....###",
        ".########.",
    ],
    "T": [
        "##########",
        "...####...",
        "...####...",
        "...####...",
        "...####...",
        "...####...",
        "...####...",
    ],
    "A": [
        ".########.",
        "###....###",
        "###....###",
        "##########",
        "###....###",
        "###....###",
        "###....###",
    ],
    "G": [
        ".########.",
        "###....###",
        "###.......",
        "###..#####",
        "###....###",
        "###....###",
        ".########.",
    ],
    "E": [
        "##########",
        "###.......",
        "###.......",
        "########..",
        "###.......",
        "###.......",
        "##########",
    ],
    "W": [
        "###....###",
        "###....###",
        "###....###",
        "###.##.###",
        "###.##.###",
        "##########",
        ".###..###.",
    ],
    "R": [
        "########..",
        "###....###",
        "###....###",
        "########..",
        "###..###..",
        "###...###.",
        "###....###",
    ],
    "N": [
        "###....###",
        "#####..###",
        "######.###",
        "###.######",
        "###..#####",
        "###...####",
        "###....###",
    ],
    "I": [
        ".########.",
        "...####...",
        "...####...",
        "...####...",
        "...####...",
        "...####...",
        ".########.",
    ],
    "1": [
        "....###...",
        "..#####...",
        "....###...",
        "....###...",
        "....###...",
        "....###...",
        ".########.",
    ],
    "2": [
        ".########.",
        "###....###",
        ".......###",
        ".########.",
        "###.......",
        "###.......",
        "##########",
    ],
    "3": [
        ".########.",
        "###....###",
        ".......###",
        "..#######.",
        ".......###",
        "###....###",
        ".########.",
    ],
    "4": [
        "###....###",
        "###....###",
        "###....###",
        "##########",
        ".......###",
        ".......###",
        ".......###",
    ],
    "5": [
        "##########",
        "###.......",
        "#########.",
        ".......###",
        ".......###",
        "###....###",
        ".########.",
    ],
    "6": [
        ".########.",
        "###.......",
        "#########.",
        "###....###",
        "###....###",
        "###....###",
        ".########.",
    ],
    "7": [
        "##########",
        "###....###",
        "......###.",
        ".....###..",
        "....###...",
        "....###...",
        "....###...",
    ],
    "8": [
        ".########.",
        "###....###",
        "###....###",
        ".########.",
        "###....###",
        "###....###",
        ".########.",
    ],
    "9": [
        ".########.",
        "###....###",
        "###....###",
        ".#########",
        ".......###",
        "###....###",
        ".########.",
    ],
}

BANNER_BANDS = [(9, 8), (9, 8), (8, 8), (8, 7), (8, 7), (7, 7), (8, 7)]
BANNER_SHADOW = 6


def _render_banner_text(w, h, text, x0, step=12):
    import numpy as np
    f = np.zeros((h, w), dtype=np.uint8)
    for k, ch in enumerate(text):
        g = GLYPHS[ch]
        gx0 = x0 + k * step
        for r, row in enumerate(g):
            c_top, c_bot = BANNER_BANDS[r]
            y0 = 1 + r * 2
            for gx, c in enumerate(row):
                if c == "#":
                    f[y0, gx0 + gx] = c_top
                    f[y0 + 1, gx0 + gx] = c_bot
    lit = f != 0
    for y in range(h):
        for x in range(w):
            if not lit[y, x]:
                if (y > 0 and lit[y - 1, x]) or (y > 0 and x > 0 and lit[y - 1, x - 1]) or (x > 0 and lit[y, x - 1]):
                    f[y, x] = BANNER_SHADOW
    return f


def banner():
    """The stage banner: "STAGE" in 64x16, then the digits 1-9 in 16x16 (palette SHOTS),
    drawn doubled."""
    out = [_render_banner_text(64, 16, "STAGE", 2, 12)]
    nums = [_render_banner_text(16, 16, d, 3, 12) for d in "123456789"]
    return out, nums


def portrait(img, size=16):
    """A boss's portrait for the HUD: its sprite shrunk to size x size,
    taking the commonest colour in each block, then outlined."""
    import numpy as np
    h, w = img.shape
    k = max(h, w) // size
    out = np.zeros((size, size), dtype=np.uint8)
    oy, ox = (size - h // k) // 2, (size - w // k) // 2
    for y in range(h // k):
        for x in range(w // k):
            block = img[y * k:(y + 1) * k, x * k:(x + 1) * k].ravel()
            block = block[block != 0]
            if len(block) * 2 >= k * k:
                vals, counts = np.unique(block, return_counts=True)
                out[oy + y, ox + x] = vals[np.argmax(counts)]
    filled = out != 0
    pad = np.pad(filled, 1)
    nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    out[(~filled) & nb] = 1
    return [out]


def warning():
    """"WARNING", 88x16, cut into a 64 and a 24 wide piece (sprites are at
    most 64 wide), drawn doubled. The same art flashes gold with palette
    SHOTS and red with ENEMY_RED, whose entries 5-9 line up with it."""
    img = _render_banner_text(88, 16, "WARNING", 2, 12)
    return [img[:, :64].copy()], [img[:, 64:].copy()]
