"""Every 16-color palette in the game, in XRAM order.

The order here is the order of palettes.bin, and gen_art.py writes
src/gen/palettes.h with an index per name so xram.h can find each one.
Entry 0 of every palette is transparent.
"""

T = None  # transparent

PLAYER = [
    T, (12, 14, 28),
    (52, 58, 84), (98, 108, 140), (156, 168, 196), (222, 230, 244),  # 2-5 hull silver
    (24, 48, 128), (48, 96, 208), (110, 170, 255),                   # 6-8 blue accent
    (20, 40, 60), (90, 220, 255),                                    # 9-10 canopy
    (255, 80, 40), (255, 170, 60), (255, 240, 150), (255, 255, 255),  # 11-14 engine (cycled)
    (220, 40, 60),                                                    # 15 red trim
]

SHOTS = [
    T, (0, 40, 90),
    (0, 140, 255), (80, 220, 255), (200, 250, 255), (255, 255, 255),  # 2-5 cyan/white
    (120, 30, 0), (240, 110, 0), (255, 200, 40), (255, 250, 200),      # 6-9 orange
    (0, 80, 40), (0, 200, 90), (120, 255, 170), (230, 255, 240),       # 10-13 green
    (140, 60, 255), (220, 180, 255),                                   # 14-15 violet
]

_METAL = [(40, 42, 56), (76, 80, 98), (120, 126, 144), (180, 186, 200)]
_ENEMY_TAIL = [(60, 255, 140), (210, 255, 225), (30, 30, 50), (120, 140, 200), (22, 18, 30), (255, 255, 255)]


def _enemy(paint):
    return [T, (16, 10, 18)] + _METAL + paint + _ENEMY_TAIL


ENEMY_RED = _enemy([(90, 10, 20), (170, 30, 40), (235, 70, 60), (255, 160, 130)])
ENEMY_BLUE = _enemy([(10, 30, 100), (30, 80, 200), (70, 150, 255), (170, 220, 255)])
ENEMY_YELLOW = _enemy([(110, 70, 0), (200, 150, 0), (255, 215, 40), (255, 250, 170)])
# Neutral enemies (no chain color), armour gray-green.
ENEMY_GRAY = _enemy([(30, 50, 40), (60, 90, 72), (100, 140, 110), (170, 200, 170)])

FLASH = [T] + [(255, 255, 255)] * 15
FLASH[1] = (255, 120, 160)
FLASH[2] = (255, 200, 220)

BULLET_PINK = [T, (110, 0, 70), (230, 40, 150), (255, 120, 210), (255, 220, 245), (255, 255, 255)] + [T] * 10
BULLET_BLUE = [T, (0, 20, 110), (40, 90, 255), (120, 190, 255), (220, 240, 255), (255, 255, 255)] + [T] * 10

EXPLOSION = [
    T, (40, 20, 24), (90, 60, 56), (150, 34, 12), (225, 75, 12), (255, 145, 24),
    (255, 212, 64), (255, 250, 200), (255, 255, 255), (60, 60, 72), (112, 112, 124),
    (30, 30, 40), (180, 180, 190), (255, 90, 150), (120, 200, 255), (255, 255, 255),
]

BOSS = [
    T, (10, 10, 18),
    (30, 34, 48), (56, 64, 84), (92, 104, 128), (140, 152, 176), (200, 210, 228),  # 2-6 armour
    (110, 70, 20), (200, 150, 40), (255, 225, 120),                                # 7-9 gold
    (255, 40, 60), (255, 180, 190),                                                # 10-11 core (cycled)
    (16, 16, 24), (44, 32, 56),                                                    # 12-13 vents
    (40, 200, 255), (220, 250, 255),                                               # 14-15 lights
]

# Wrecked parts: armour scorched, lights out.
BOSS_WRECK = [
    T, (8, 6, 10),
    (26, 20, 22), (44, 34, 34), (66, 50, 46), (92, 70, 60), (120, 92, 76),
    (70, 40, 20), (110, 70, 30), (150, 100, 50),
    (120, 30, 20), (200, 90, 40),
    (12, 10, 12), (30, 20, 24),
    (40, 30, 30), (80, 60, 50),
]

TILES = [
    (6, 10, 26),                                                      # 0 deep backdrop (opaque)
    (10, 30, 70), (14, 38, 84), (18, 46, 98), (24, 54, 112),        # 1-4 sea (2-4 cycled, kept close)
    (30, 32, 44), (52, 56, 72), (82, 88, 108), (122, 130, 150), (170, 178, 196),  # 5-9 deck
    (14, 14, 22),                                                     # 10 shadow
    (160, 120, 30), (230, 190, 60),                                   # 11-12 hazard / gold
    (255, 60, 60), (120, 255, 200),                                   # 13-14 lights (cycled)
    (200, 230, 255),                                                  # 15 foam
]

HUD = [
    T, (8, 10, 28), (36, 46, 96), (255, 255, 255), (150, 160, 190), (80, 220, 255),
    (255, 220, 60), (255, 70, 70), (70, 120, 255), (90, 255, 140), (255, 150, 40),
    (255, 110, 220), (60, 70, 112), (20, 24, 56), (180, 140, 255), (0, 0, 0),
]

# Palettes that are always loaded, in XRAM order.
RESIDENT = [
    ("PLAYER", PLAYER),
    ("SHOTS", SHOTS),
    ("ENEMY_RED", ENEMY_RED),
    ("ENEMY_BLUE", ENEMY_BLUE),
    ("ENEMY_YELLOW", ENEMY_YELLOW),
    ("ENEMY_GRAY", ENEMY_GRAY),
    ("FLASH", FLASH),
    ("BULLET_PINK", BULLET_PINK),
    ("BULLET_BLUE", BULLET_BLUE),
    ("EXPLOSION", EXPLOSION),
    ("HUD", HUD),
]

# Palettes each stage brings in its bank, loaded over these slots, which
# follow the resident ones. TILES is the ground (plane 0), SKY the plane 1
# layer (parallax, clouds), LAYER the boss's tile layer (stage 3's ship).
# By convention entries 2-4 of TILES, SKY and LAYER rotate and 13-14 blink
# (see bg.c), so draw with them only where that should happen.
STAGE_SLOTS = ["TILES", "SKY", "LAYER", "BOSS", "BOSS_WRECK"]

BLANK = [T] * 16

# Stage 2, NEON SPIRES. Ground and sky colors live with the art in city.py.
BOSS2 = [
    T, (10, 6, 18),
    (32, 24, 48), (56, 44, 80), (90, 74, 120), (136, 118, 170), (196, 182, 226),  # 2-6 armour
    (10, 90, 100), (30, 170, 170), (140, 250, 230),                              # 7-9 teal trim
    (255, 40, 180), (255, 170, 230),                                             # 10-11 eye
    (14, 10, 22), (40, 26, 56),                                                  # 12-13 vents
    (255, 200, 60), (255, 250, 220),                                             # 14-15 lights
]
BOSS2_WRECK = [
    T, (8, 6, 10),
    (24, 18, 24), (40, 30, 36), (60, 46, 52), (84, 64, 70), (110, 86, 90),
    (30, 40, 40), (50, 70, 66), (80, 100, 90),
    (110, 30, 50), (180, 80, 90),
    (12, 10, 12), (28, 20, 26),
    (60, 40, 30), (90, 70, 60),
]

STAGE1 = {"TILES": TILES, "SKY": BLANK, "LAYER": BLANK, "BOSS": BOSS, "BOSS_WRECK": BOSS_WRECK}

ALL = RESIDENT + [(name, STAGE1[name]) for name in STAGE_SLOTS]


def rgb555(c):
    if c is None:
        return 0
    r, g, b = c
    return ((b >> 3) << 11) | ((g >> 3) << 6) | (r >> 3) | (1 << 5)


def view(pal):
    """RGB triples for an indexed PNG preview."""
    return [(255, 0, 255) if c is None else c for c in pal]
