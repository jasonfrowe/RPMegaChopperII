"""Every palette in the game, 16 colors each, as (r, g, b).

Sprite and upper-plane palettes treat index 0 as transparent. The far sky
(plane 0) has no transparency, so its index 0 is a real color.
"""

# --- Far layer (plane 0): night sky, stars, aurora, mountains -------------
SKY = [(6, 8, 26), (10, 14, 40), (15, 21, 56), (22, 31, 74), (32, 45, 94), (46, 64, 116)]
FAR = SKY + [
    (130, 142, 186),  # 6 star, dim
    (236, 242, 255),  # 7 star, bright
    # 8-12: aurora. The game rotates these five every few frames.
    (20, 90, 80), (34, 150, 110), (70, 214, 140), (160, 250, 200), (40, 170, 128),
    (88, 108, 160),   # 13 mountain snow in shadow
    (158, 178, 218),  # 14 mountain snow
    (226, 236, 252),  # 15 mountain snow lit
]
FAR_AURORA = 8
# The aurora's brightness wave: each slot steps through this, offset by its
# index, so bright bands drift along the curtain.
AURORA_WAVE = [(14, 60, 62), (20, 90, 80), (30, 130, 100), (48, 180, 124), (80, 222, 150),
               (150, 252, 196), (90, 230, 160), (50, 190, 130), (32, 140, 108), (20, 96, 84)]

# --- Mid layer (plane 1): hills and forest --------------------------------
MID = [
    (0, 0, 0),
    (12, 16, 32),     # 1 deepest shadow
    (16, 30, 46),     # 2 pine dark
    (24, 46, 60),     # 3 pine
    (40, 68, 78),     # 4 pine, snow-dusted
    (48, 62, 104),    # 5 far hill shadow
    (70, 90, 140),    # 6 hill shadow
    (108, 130, 182),  # 7 hill snow
    (160, 182, 224),  # 8 hill snow lit
    (214, 226, 248),  # 9 snow highlight
    (255, 206, 120),  # 10 window light
    (230, 40, 40),    # 11 beacon (the game blinks it)
    (34, 40, 64),     # 12 building dark
    (60, 70, 100),    # 13 building
    (30, 54, 66),     # 14 spare
    (90, 110, 150),   # 15 spare
]
MID_BEACON = 11

# --- Foreground (plane 2): ground, compounds, home base -------------------
FG = [
    (0, 0, 0),
    (8, 10, 20),      # 1 outline
    (40, 52, 94),     # 2 snow deep shadow
    (78, 98, 152),    # 3 snow shadow
    (128, 150, 202),  # 4 snow mid
    (186, 204, 238),  # 5 snow
    (242, 247, 255),  # 6 snow lit
    (34, 36, 46),     # 7 steel dark
    (62, 66, 80),     # 8 steel
    (100, 106, 122),  # 9 steel mid
    (150, 156, 172),  # 10 concrete light
    (22, 58, 52),     # 11 pine dark
    (42, 96, 76),     # 12 pine
    (236, 186, 50),   # 13 hazard yellow / lamp
    (200, 38, 42),    # 14 red
    (255, 238, 176),  # 15 lamp lit (the game blinks it)
]
FG_LAMP = 15

# --- HUD (plane 2, rows 0-1) ----------------------------------------------
HUD = [
    (0, 0, 0),
    (8, 12, 30),      # 1 panel
    (26, 38, 78),     # 2 panel light
    (60, 80, 130),    # 3 frame
    (110, 130, 180),  # 4 dim text
    (64, 220, 140),   # 5 green
    (255, 120, 60),   # 6 orange
    (240, 244, 255),  # 7 white
    (255, 206, 72),   # 8 gold
    (240, 60, 60),    # 9 red
    (110, 240, 150),  # 10 light green
    (100, 210, 255),  # 11 cyan
    (180, 190, 210),  # 12 grey
    (150, 160, 255),  # 13 lavender
    (120, 255, 220),  # 14 aurora
    (255, 160, 200),  # 15 pink
]

# --- Sprites ---------------------------------------------------------------
OUT = (8, 10, 18)
CHOPPER = [
    (0, 0, 0), OUT,
    (70, 74, 88), (128, 134, 150), (190, 196, 210), (244, 246, 252),   # 2-5 white hull ramp
    (110, 16, 24), (180, 30, 36), (236, 64, 60),                        # 6-8 red trim
    (20, 50, 80), (50, 120, 170), (150, 220, 250),                     # 9-11 glass
    (36, 38, 44), (90, 94, 104),                                        # 12-13 rotor, mast
    (170, 176, 190),                                                    # 14 rotor blur
    (255, 220, 120),                                                    # 15 nav light
]
HOSTAGE = [
    (0, 0, 0), OUT,
    (140, 36, 12), (232, 92, 20), (255, 168, 56),   # 2-4 orange parka
    (26, 38, 86), (62, 88, 160),                    # 5-6 navy trousers & cap
    (168, 102, 70), (240, 182, 140),                # 7-8 skin
    (56, 36, 26),                                   # 9 boots & hair
    (240, 244, 255),                                # 10 white accent
    (104, 140, 216),                                # 11 cap highlight
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
TANK = [
    (0, 0, 0), OUT,
    (40, 46, 40), (70, 80, 66), (108, 118, 98), (150, 158, 136),   # 2-5 winter olive
    (200, 206, 214), (236, 240, 246),                               # 6-7 white camo
    (24, 24, 28), (56, 56, 62), (96, 96, 104),                     # 8-10 treads
    (160, 30, 30), (230, 70, 50),                                  # 11-12 red markings
    (255, 220, 120), (60, 60, 70), (0, 0, 0),                      # 13 muzzle, 14 barrel
]
JET = [
    (0, 0, 0), OUT,
    (40, 44, 56), (74, 80, 98), (116, 124, 144), (168, 176, 196),   # 2-5 grey hull
    (150, 24, 28), (220, 60, 50),                                   # 6-7 red
    (30, 60, 90), (90, 160, 210),                                   # 8-9 canopy
    (255, 120, 40), (255, 220, 110), (255, 255, 230),               # 10-12 afterburner
    (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
BALLOON = [
    (0, 0, 0), OUT,
    (52, 58, 72), (92, 100, 116), (142, 150, 166), (198, 204, 216),   # 2-5 silver envelope
    (130, 20, 26), (206, 46, 42),                                   # 6-7 red bands
    (36, 38, 44), (78, 80, 88),                                     # 8-9 gondola, cables
    (255, 60, 50), (255, 210, 140),                                 # 10-11 warning light
    (230, 180, 30), (60, 64, 70),                                   # 12-13 mine: hazard yellow, casing
    (170, 176, 188), (240, 244, 252),                               # 14 propeller blur, 15 glint
]
FX = [
    (0, 0, 0), OUT,
    (90, 20, 10), (180, 40, 16), (240, 100, 24), (255, 180, 50), (255, 240, 150), (255, 255, 255),  # 2-7 fire
    (40, 40, 46), (80, 80, 88), (130, 130, 138), (180, 180, 186),   # 8-11 smoke
    (60, 64, 70), (120, 126, 136),                                  # 12-13 bomb casing
    (255, 230, 90), (100, 240, 255),                                # 14 tracer, 15 cyan
]
FLAG = [
    (0, 0, 0), OUT,
    (150, 16, 24), (214, 36, 40), (250, 80, 76),    # 2-4 red
    (196, 200, 214), (246, 248, 255),               # 5-6 white
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
TARGET = [
    (0, 0, 0), OUT,
    (200, 20, 30), (255, 70, 60), (255, 200, 180),
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]
SNOW = [
    (0, 0, 0), (150, 170, 210), (210, 222, 245), (255, 255, 255),
] + [(0, 0, 0)] * 12

# The logo's three 2-color palettes (shadow, rim, face), back to back:
# each pair is (transparent, color).
LOGO = [(0, 0, 0), (14, 20, 60), (0, 0, 0), (255, 246, 190), (0, 0, 0), (240, 170, 40)] + [(0, 0, 0)] * 10

# --- Level 2: the boreal forest and its lakes ----------------------------
B_SKY = [(6, 6, 24), (10, 10, 36), (16, 16, 52), (24, 26, 70), (34, 40, 90), (50, 58, 110)]
B_FAR = B_SKY + [
    (130, 136, 186),  # 6 star, dim
    (236, 240, 255),  # 7 star, bright
    # 8-12: aurora, rotated by the game like level 1's.
    (40, 30, 96), (40, 140, 120), (70, 214, 150), (170, 250, 210), (120, 70, 170),
    (8, 16, 26),      # 13 far ridge, dark
    (16, 30, 42),     # 14 far ridge
    (44, 76, 96),     # 15 far ridge rim, lit by the aurora
]
# Green curtains with violet hems: the light runs violet, green, white.
B_AURORA_WAVE = [(36, 22, 70), (64, 34, 120), (96, 60, 160), (50, 140, 130), (70, 210, 150),
                 (170, 252, 210), (100, 230, 170), (60, 170, 140), (90, 70, 160), (54, 30, 96)]

B_MID = [
    (0, 0, 0),
    (5, 8, 18),       # 1 deepest shadow
    (10, 22, 30),     # 2 spruce dark
    (18, 38, 44),     # 3 spruce
    (38, 74, 72),     # 4 spruce, rimmed by the aurora
    (14, 20, 40),     # 5 far shore
    (26, 36, 64),     # 6 shore, cabin logs
    (84, 104, 146),   # 7 snow in shadow
    (146, 166, 208),  # 8 snow
    (206, 220, 244),  # 9 snow lit
    (255, 206, 120),  # 10 window light
    (230, 40, 40),    # 11 beacon (the game blinks it)
    (8, 14, 34),      # 12 water, dark
    (18, 30, 60),     # 13 water
    (40, 130, 110),   # 14 aurora in the water
    (130, 230, 190),  # 15 aurora in the water, bright
]

B_FG = [
    (0, 0, 0),
    (6, 8, 16),       # 1 outline
    (30, 40, 78),     # 2 snow deep shadow
    (60, 78, 128),    # 3 snow shadow / ice
    (102, 122, 178),  # 4 snow mid / ice
    (158, 178, 222),  # 5 snow
    (222, 232, 250),  # 6 snow lit
    (40, 26, 22),     # 7 timber dark
    (76, 52, 38),     # 8 timber
    (114, 80, 54),    # 9 timber mid
    (158, 118, 80),   # 10 timber light
    (12, 36, 36),     # 11 spruce dark
    (26, 70, 58),     # 12 spruce / aurora in the ice
    (236, 186, 50),   # 13 hazard yellow / lamp
    (200, 38, 42),    # 14 red
    (255, 238, 176),  # 15 lamp lit (the game blinks it)
]

# Level 2's enemies, in level 1's enemy palette slots.
JEEP = [
    (0, 0, 0), OUT,
    (30, 40, 30), (52, 70, 46), (84, 104, 66), (126, 144, 96),      # 2-5 forest olive
    (200, 206, 214), (236, 240, 246),                               # 6-7 snow on the bonnet
    (22, 22, 26), (54, 54, 60), (100, 100, 108),                    # 8-10 tyres, hub
    (150, 26, 30), (226, 66, 50),                                   # 11-12 red markings
    (255, 220, 120), (60, 62, 72), (255, 250, 210),                 # 13 muzzle, 14 gun, 15 headlight
]
TURRET = [
    (0, 0, 0), OUT,
    (44, 50, 30), (86, 98, 54), (138, 152, 88), (250, 200, 40),     # 2-4 olive drab, 5 hazard yellow
    (130, 20, 26), (206, 46, 42),                                   # 6-7 red
    (34, 36, 42), (70, 74, 82),                                     # 8-9 launcher steel
    (255, 60, 50), (255, 210, 140),                                 # 10-11 warning light
    (224, 228, 236), (180, 30, 36),                                 # 12 rocket body, 13 rocket nose
    (255, 140, 40), (255, 236, 130),                                # 14-15 rocket flame
]
WORM = [
    (0, 0, 0), OUT,
    (64, 26, 52), (122, 54, 84), (184, 100, 124), (236, 162, 168),  # 2-5 hide
    (70, 6, 18), (160, 26, 40),                                     # 6-7 maw
    (240, 236, 206),                                                # 8 teeth
    (255, 236, 90),                                                 # 9 glints
    (36, 26, 20), (74, 54, 36), (116, 88, 58),                      # 10-12 earth
    (170, 186, 220), (236, 242, 255),                               # 13-14 snow
    (0, 0, 0),
]

# Each level's own colors, over the shared ones. A level's bank carries
# every palette, so its enemies can reuse level 1's slots.
LEVELS = {
    1: {},
    2: {"FAR": B_FAR, "MID": B_MID, "FG": B_FG, "TANK": JEEP, "BALLOON": TURRET, "JET": WORM},
}
AURORA_WAVES = {1: AURORA_WAVE, 2: B_AURORA_WAVE}


def level_pal(level, name):
    return LEVELS[level].get(name, dict(ORDER)[name])


# Palette slots in XRAM, in order. assets.h gets PAL_<NAME> for each.
ORDER = [
    ("CHOPPER", CHOPPER), ("HOSTAGE", HOSTAGE), ("TANK", TANK), ("JET", JET), ("BALLOON", BALLOON),
    ("FX", FX), ("FLAG", FLAG), ("TARGET", TARGET), ("SNOW", SNOW),
    ("FAR", FAR), ("MID", MID), ("FG", FG), ("HUD", HUD), ("LOGO", LOGO),
]

# Palettes whose index 0 is a real, opaque color.
OPAQUE0 = {"FAR"}


def rgb555(c, opaque=True):
    r, g, b = c
    return ((b >> 3) << 11) | ((g >> 3) << 6) | ((1 << 5) if opaque else 0) | (r >> 3)


def blob(level=1):
    out = bytearray()
    for name, _ in ORDER:
        pal = level_pal(level, name)
        assert len(pal) == 16, name
        for i, c in enumerate(pal):
            opaque = (i != 0 or name in OPAQUE0) and not (name == "LOGO" and i % 2 == 0)
            v = rgb555(c, opaque=opaque)
            out += bytes((v & 0xFF, v >> 8))
    return bytes(out)
