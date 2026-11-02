"""Stage 4 boss, DUNE WYRM: a sandworm in armoured segments.

The head is the core; nine body segments and a tail follow its path
(motion_t's chain), each one a part to shoot off. Uses boss.MATS, in its
own colors (BOSS4): bone-pale shell, rust plates, a glowing maw.
"""

import math

from boss import MATS
from kit import Sprite

BOSS4 = [
    None, (20, 10, 8),
    (70, 50, 40), (110, 84, 64), (156, 128, 98), (204, 180, 146), (240, 226, 196),  # 2-6 shell
    (110, 40, 20), (170, 70, 34), (220, 120, 60),                                   # 7-9 rust
    (255, 110, 30), (255, 220, 120),                                                # 10-11 maw
    (30, 14, 10), (64, 34, 24),                                                     # 12-13 dark
    (255, 70, 50), (255, 240, 200),                                                 # 14-15 eyes
]
BOSS4_WRECK = [
    None, (10, 6, 6),
    (40, 30, 26), (60, 46, 40), (84, 66, 56), (110, 90, 76), (136, 116, 98),
    (60, 30, 20), (84, 46, 30), (110, 70, 44),
    (110, 50, 20), (150, 100, 60),
    (16, 10, 8), (34, 22, 18),
    (90, 40, 30), (120, 100, 80),
]


def head():
    """48x48 head, maw open toward the bottom of the screen."""
    s = Sprite(48, 48)
    s.poly([(24, 3), (39, 8), (45, 22), (42, 37), (34, 45), (14, 45), (6, 37), (3, 22), (9, 8)], "armor", amp=3,
           bevel=6)
    s.poly([(24, 6), (35, 11), (39, 20), (24, 24), (9, 20), (13, 11)], "gold", z=2, amp=1.4, bevel=2.5)
    # The maw: a ring of teeth around a burning throat.
    s.ellipse((12, 22, 36, 45), "vent", z=2.5, amp=0.4, profile="flat")
    s.ellipse((16, 26, 32, 41), "core", z=3)
    s.ellipse((20, 30, 28, 37), "corehot", z=4)
    for k in range(8):
        a = math.radians(k * 45 + 22)
        x, y = 24 + math.cos(a) * 10.5, 33.5 + math.sin(a) * 10.5
        s.poly([(x, y), (24 + math.cos(a) * 6.5, 33.5 + math.sin(a) * 6.5 - 1.5),
                (24 + math.cos(a) * 6.5 + 1.5, 33.5 + math.sin(a) * 6.5)], "plate", z=4.5, amp=0.8, bevel=0.8)
    s.ellipse((10, 13, 16, 19), "light", z=4, sym=True)
    s.dot(12, 15, "lightb", z=5, sym=True)
    return [s.render(MATS, gloss=0.4)]


def _parse_frames(art_list, fw, fh):
    import numpy as np
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


_HALF_PORTRAIT = [
    "........",  # 0: margin
    "....111.",  # 1: crown tip
    "...16651",  # 2: bone shell crown
    "..165541",  # 3:
    ".1655e11",  # 4: outer shell + glowing red eye (14 = e)
    ".165eff1",  # 5: eye glint (15 = f)
    ".155411.",  # 6: eye orbit rim
    ".154881.",  # 7: rust mandible
    ".15481aa",  # 8: maw opening (10 = a)
    ".1541abb",  # 9: burning throat (11 = b)
    ".1511abb",  # 10:
    "..1811aa",  # 11: inner fangs
    "..18811.",  # 12: lower mandible
    "...1881.",  # 13:
    "....11..",  # 14: bottom chin tip
    "........",  # 15: margin
]


def portrait():
    """16x16 HUD portrait of Dune Wyrm."""
    return _parse_frames([[r + "".join(reversed(r)) for r in _HALF_PORTRAIT]], 16, 16)


def segment():
    """32x32 body ring: a shell plate over a rusted band. Frames: two, so
    neighbors can differ."""
    out = []
    for k in range(2):
        s = Sprite(32, 32)
        s.ellipse((2, 4, 30, 29), "armor", amp=2.6)
        s.ellipse((5, 6, 27, 26), "gold" if k else "plate", z=2, amp=1.2)
        for x in (8, 16, 24):
            s.poly([(x - 2, 7), (x, 3), (x + 2, 7)], "plate", z=3, amp=1, bevel=1)
        s.rect((6, 15, 26, 17), "vent", z=2.6, amp=0.3, profile="flat")
        out.append(s.render(MATS, gloss=0.35))
    return out


def tail():
    """32x32 tail: tapering shell and a stinger."""
    s = Sprite(32, 32)
    s.poly([(6, 4), (26, 4), (22, 18), (16, 30), (10, 18)], "armor", amp=2.2, bevel=4)
    s.poly([(10, 6), (22, 6), (19, 15), (13, 15)], "gold", z=2, amp=1, bevel=1.5)
    s.poly([(14, 20), (16, 30), (18, 20)], "corehot", z=3)
    return [s.render(MATS, gloss=0.35)]
