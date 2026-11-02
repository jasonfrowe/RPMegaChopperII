"""The title logo: "MEGA CHOPPER II" in chunky letters, 1 bit per pixel.

The game draws the same bitmap three times, a dark shadow down and right,
a light rim up and left, and the face on top, which gives it a bevel
without spending more than one bit per pixel. Cut into 64-pixel pieces,
since a sprite is at most 64 wide.
"""

from __future__ import annotations

import numpy as np

# 5x7 letters, '#' set.
FONT = {
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "G": [".####", "#....", "#....", "#.###", "#...#", "#...#", ".####"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "I": ["#", "#", "#", "#", "#", "#", "#"],
    " ": [".", ".", ".", ".", ".", ".", "."],
}

TEXT = "MEGA CHOPPER II"
SCALE = 3
GAP = 2
W, H = 256, 24
PIECE = 64


def bitmap():
    cols = []
    for k, ch in enumerate(TEXT):
        g = np.array([[c == "#" for c in row] for row in FONT[ch]], bool)
        g = np.kron(g, np.ones((SCALE, SCALE), bool))
        cols.append(g)
        if k < len(TEXT) - 1:
            cols.append(np.zeros((7 * SCALE, GAP), bool))
    word = np.concatenate(cols, axis=1)
    out = np.zeros((H, W), bool)
    h, w = word.shape
    assert w <= W - 3, w
    y0, x0 = 1, (W - w) // 2
    out[y0:y0 + h, x0:x0 + w] = word
    return out


def pieces():
    b = bitmap().astype(np.uint8)
    return [b[:, x:x + PIECE] for x in range(0, W, PIECE)]


# Colors for the three passes: shadow, rim, face (index 1 of each 2-color
# palette; index 0 is transparent).
SHADOW = (14, 20, 60)
RIM = (255, 246, 190)
FACE = (240, 170, 40)
