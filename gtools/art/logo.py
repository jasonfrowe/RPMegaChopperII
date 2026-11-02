"""Title logo: chunky beveled letters, shaded with the kit, in the BOSS palette."""

import numpy as np

from kit import Material, Sprite

GLYPHS = {
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    "E": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"],
    "G": [".XXXX", "X....", "X....", "X.XXX", "X...X", "X...X", ".XXXX"],
    "A": [".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "F": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "X...."],
    "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "R": ["XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"],
    "C": [".XXXX", "X....", "X....", "X....", "X....", "X....", ".XXXX"],
    " ": ["....."] * 7,
}

MATS = {
    "gold": Material([7, 8, 9, 15]),
    "chrome": Material([3, 4, 5, 6, 15]),
    "edge": Material([2], shaded=False),
}


def _line(s: Sprite, text, x0, y0, cell, mat, bevel):
    m = np.zeros((s.h, s.w), dtype=bool)
    x = x0
    for ch in text:
        for r, row in enumerate(GLYPHS[ch]):
            for c, v in enumerate(row):
                if v == "X":
                    m[y0 + r * cell:y0 + (r + 1) * cell, x + c * cell:x + (c + 1) * cell] = True
        x += 6 * cell
    s.mask(m, mat, amp=2.5, bevel=bevel)


def logo():
    """192x64 as three 64x64 frames. MEGA GAMMA small and chrome; FORCE big and gold."""
    s = Sprite(192, 64)
    # MEGA GAMMA: 10 glyphs at cell 3 -> 10*18-3 = 177 wide.
    w1 = 10 * 6 * 3 - 3
    _line(s, "MEGA GAMMA", (192 - w1) // 2, 2, 3, "chrome", 1.6)
    # FORCE: 5 glyphs at cell 5 -> 5*30-5 = 145 wide, 35 tall.
    w2 = 5 * 6 * 5 - 5
    _line(s, "FORCE", (192 - w2) // 2, 26, 5, "gold", 2.6)
    img = s.render(MATS, gloss=0.6, ambient=0.25)
    return [img[:, 0:64], img[:, 64:128], img[:, 128:192]]
