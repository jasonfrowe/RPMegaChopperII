#!/usr/bin/env python3
"""Asset generation for RPMegaChopperII (Picocomputer 6502).

Extracts and adapts sprite graphics from the original RPMegaChopper into
clean, Mode 5 4bpp indexed PNG sheets, generates Mode 2 Northern Tundra
tilemaps and parallax backgrounds, and packs the 16-color RGB555 palette bank.

Uses standard Python library only (struct, zlib) - no external dependencies.
"""

import os
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
GEN_DIR = ROOT / "src" / "gen"
OLD_IMAGES_DIR = Path("/Users/jasonrowe/Software/rp6502/RPMegaChopper/images")

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
GEN_DIR.mkdir(parents=True, exist_ok=True)


def rgb555(c):
    if c is None:
        return 0
    r, g, b = c
    return ((b >> 3) << 11) | ((g >> 3) << 6) | (r >> 3) | (1 << 5)


def write_indexed_png(path, w, h, palette, pixels):
    """Write an indexed 8-bit non-interlaced PNG using only stdlib."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0)
    plte = bytearray()
    for c in palette:
        if c is None:
            plte += bytes([0, 0, 0])
        else:
            plte += bytes([c[0], c[1], c[2]])
    # Pad palette to at least 16 entries
    while len(plte) < 16 * 3:
        plte += bytes([0, 0, 0])

    raw = bytearray()
    for y in range(h):
        raw.append(0)  # Filter type 0 (None)
        raw.extend(pixels[y * w : (y + 1) * w])

    idat = zlib.compress(bytes(raw))
    png_data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"PLTE", bytes(plte)) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    Path(path).write_bytes(png_data)


# =========================================================================
# Palettes
# =========================================================================
T = None

PAL_CHOPPER = [
    T, (0, 0, 0), (0, 48, 24), (20, 60, 36), (40, 80, 50),
    (180, 24, 24), (220, 36, 36), (255, 60, 60),
    (60, 64, 72), (120, 130, 140), (190, 200, 210), (255, 255, 255),
    (240, 160, 20), (255, 220, 50), (10, 20, 30), (50, 12, 12)
]

PAL_HOSTAGES = [
    T, (0, 0, 0), (40, 60, 40), (80, 110, 70), (130, 170, 110),
    (220, 170, 120), (255, 210, 170), (180, 120, 80),
    (180, 20, 20), (230, 40, 40), (40, 80, 160), (90, 140, 220),
    (240, 240, 240), (100, 100, 100), (40, 40, 40), (255, 230, 80)
]

PAL_TANK = [
    T, (0, 0, 0), (24, 32, 28), (48, 64, 52), (80, 100, 84),
    (120, 144, 124), (160, 180, 164), (180, 40, 30),
    (220, 70, 40), (255, 180, 50), (40, 48, 56), (70, 80, 92),
    (110, 120, 134), (200, 210, 220), (255, 255, 255), (14, 18, 16)
]

PAL_JET = [
    T, (0, 0, 0), (32, 36, 44), (64, 72, 84), (100, 112, 128),
    (150, 164, 184), (200, 214, 234), (255, 255, 255),
    (255, 60, 20), (255, 140, 30), (255, 220, 60), (120, 200, 255),
    (40, 80, 160), (20, 30, 40), (200, 30, 30), (80, 20, 20)
]

PAL_BALLOON = [
    T, (0, 0, 0), (60, 10, 10), (120, 20, 20), (180, 30, 30),
    (230, 50, 40), (255, 100, 80), (255, 180, 160),
    (200, 160, 20), (255, 220, 40), (40, 40, 48), (80, 84, 96),
    (140, 144, 160), (200, 204, 220), (255, 255, 255), (30, 20, 50)
]

PAL_EXPLOSION = [
    T, (20, 10, 10), (60, 20, 10), (120, 40, 10), (180, 60, 10),
    (230, 90, 15), (255, 140, 20), (255, 190, 40),
    (255, 235, 100), (255, 255, 200), (255, 255, 255),
    (60, 60, 70), (100, 100, 110), (150, 150, 160), (200, 200, 210), (10, 10, 12)
]

PAL_FLAGS = [
    T, (0, 0, 0), (140, 144, 152), (200, 204, 212), (255, 255, 255),
    (160, 20, 24), (210, 28, 32), (245, 40, 44),
    (60, 64, 72), (90, 94, 104), (30, 32, 36), (10, 10, 12),
    (255, 200, 50), (255, 120, 20), (80, 10, 14), (255, 255, 255)
]

PAL_TARGET = [
    T, (0, 0, 0), (120, 10, 10), (180, 20, 20), (230, 30, 30),
    (255, 60, 60), (255, 120, 120), (255, 200, 200), (255, 255, 255),
    (255, 220, 40), (200, 160, 20), (100, 80, 10), (40, 40, 40),
    (80, 80, 80), (160, 160, 160), (20, 20, 20)
]

# Mode 2 Background: Northern Tundra Sky & Snowy Mountains
PAL_BG = [
    T, (10, 18, 32), (22, 34, 54), (38, 56, 84), (60, 84, 118),
    (90, 120, 156), (130, 160, 196), (180, 204, 230), (220, 234, 248),
    (255, 255, 255), (14, 28, 22), (24, 46, 36), (40, 70, 54),
    (68, 102, 80), (110, 140, 120), (160, 185, 170)
]

# Mode 2 Foreground: Snowdrifts, Ice, Bunker Concrete & Metal
PAL_FG = [
    T, (16, 20, 28), (32, 40, 52), (54, 64, 80), (84, 96, 114),
    (124, 138, 156), (170, 184, 202), (210, 222, 236), (240, 246, 255),
    (255, 255, 255), (180, 30, 30), (230, 45, 45), (255, 80, 80),
    (40, 80, 40), (70, 120, 70), (255, 210, 40)
]

# Mode 1 HUD Text
PAL_HUD = [
    T, (0, 0, 0), (20, 28, 36), (50, 65, 80), (90, 110, 130),
    (140, 165, 190), (200, 220, 240), (255, 255, 255), (255, 215, 0),
    (255, 80, 40), (50, 220, 90), (40, 180, 255), (255, 120, 210),
    (180, 180, 180), (120, 120, 120), (70, 70, 70)
]

ALL_PALETTES = [
    ("PAL_CHOPPER", PAL_CHOPPER),
    ("PAL_HOSTAGES", PAL_HOSTAGES),
    ("PAL_TANK", PAL_TANK),
    ("PAL_JET", PAL_JET),
    ("PAL_BALLOON", PAL_BALLOON),
    ("PAL_EXPLOSION", PAL_EXPLOSION),
    ("PAL_FLAGS", PAL_FLAGS),
    ("PAL_TARGET", PAL_TARGET),
    ("PAL_BG", PAL_BG),
    ("PAL_FG", PAL_FG),
    ("PAL_HUD", PAL_HUD),
]


def generate_palettes_blob():
    blob = bytearray()
    for name, pal in ALL_PALETTES:
        assert len(pal) == 16
        for c in pal:
            blob += struct.pack("<H", rgb555(c))
    # Pad to 16 full palettes (512 bytes)
    while len(blob) < 16 * 16 * 2:
        blob += struct.pack("<H", 0)
    (IMAGES_DIR / "palettes.bin").write_bytes(bytes(blob))
    print(f"Palettes: {len(ALL_PALETTES)} palettes -> {len(blob)} bytes")


# =========================================================================
# Sprites Conversion from RPMegaChopper
# =========================================================================

def convert_chopper():
    raw = (OLD_IMAGES_DIR / "Chopper.bin").read_bytes()
    num_frames = len(raw) // 1024
    w, h = num_frames * 32, 16
    pixels = [0] * (w * h)

    color_map = {
        0x0000: 0,
        0x0020: 3,  # dark canopy
        0x0861: 4,  # body
        0x0873: 6,  # red trim
        0xFFFF: 11, # white rotor / highlights
    }

    for f in range(num_frames):
        frame_data = raw[f * 1024 : (f + 1) * 1024]
        left_words = [struct.unpack("<H", frame_data[i : i + 2])[0] for i in range(0, 512, 2)]
        right_words = [struct.unpack("<H", frame_data[512 + i : 512 + i + 2])[0] for i in range(0, 512, 2)]
        fx_start = f * 32
        for y in range(16):
            for x in range(16):
                c = color_map.get(left_words[y * 16 + x], 0)
                pixels[y * w + (fx_start + x)] = c
            for x in range(16):
                c = color_map.get(right_words[y * 16 + x], 0)
                pixels[y * w + (fx_start + 16 + x)] = c

    write_indexed_png(IMAGES_DIR / "chopper.png", w, h, PAL_CHOPPER, pixels)
    print(f"Chopper: {num_frames} frames (32x16) -> chopper.png")


def convert_hostages():
    raw = (OLD_IMAGES_DIR / "Hostages.bin").read_bytes()
    num_frames = len(raw) // 512
    w, h = num_frames * 16, 16
    pixels = [0] * (w * h)

    color_map = {
        0x0000: 0,
        0x0027: 3,  # uniform
        0x6020: 5,  # face/skin
        0xFFFF: 12, # white helmet/hands
    }

    for f in range(num_frames):
        words = [struct.unpack("<H", raw[f * 512 + i : f * 512 + i + 2])[0] for i in range(0, 512, 2)]
        fx_start = f * 16
        for y in range(16):
            for x in range(16):
                c = color_map.get(words[y * 16 + x], 0)
                pixels[y * w + (fx_start + x)] = c

    write_indexed_png(IMAGES_DIR / "hostages.png", w, h, PAL_HOSTAGES, pixels)
    print(f"Hostages: {num_frames} frames (16x16) -> hostages.png")


def convert_tank():
    raw = (OLD_IMAGES_DIR / "Tank.bin").read_bytes()
    tiles = []
    for i in range(22):
        tb = raw[i * 128 : (i + 1) * 128]
        words = [struct.unpack("<H", tb[j : j + 2])[0] for j in range(0, 128, 2)]
        tiles.append(words)

    color_map = {
        0x0000: 0,
        0x0120: 3,  # dark treads/shadow
        0x24A7: 4,  # tank hull green/camo
        0x8FF4: 6,  # bright highlights
    }

    # 6 composite frames: 2 body anims x 3 turret angles (UP_LEFT, UP, UP_RIGHT)
    # Each frame is 40x16
    turrets = [10, 14, 18]
    bodies = [0, 5]
    num_frames = 6
    w, h = num_frames * 40, 16
    pixels = [0] * (w * h)

    frame_idx = 0
    for b_idx in bodies:
        for t_idx in turrets:
            fx_start = frame_idx * 40
            # Turret: y=0..7, x=4..35 (4 tiles of 8x8)
            for t in range(4):
                tw = tiles[t_idx + t]
                for y in range(8):
                    for x in range(8):
                        c = color_map.get(tw[y * 8 + x], 0)
                        pixels[y * w + (fx_start + 4 + t * 8 + x)] = c
            # Body: y=8..15, x=0..39 (5 tiles of 8x8)
            for b in range(5):
                bw = tiles[b_idx + b]
                for y in range(8):
                    for x in range(8):
                        c = color_map.get(bw[y * 8 + x], 0)
                        pixels[(8 + y) * w + (fx_start + b * 8 + x)] = c
            frame_idx += 1

    write_indexed_png(IMAGES_DIR / "tank.png", w, h, PAL_TANK, pixels)
    print(f"Tank: {num_frames} frames (40x16) -> tank.png")


def convert_jet():
    raw = (OLD_IMAGES_DIR / "Jet.bin").read_bytes()
    tiles = []
    for i in range(4):
        tb = raw[i * 128 : (i + 1) * 128]
        words = [struct.unpack("<H", tb[j : j + 2])[0] for j in range(0, 128, 2)]
        tiles.append(words)

    color_map = {
        0x0000: 0,
        0x0260: 4,  # fuselage
        0x0362: 6,  # wings
        0x6960: 7,  # canopy / highlights
    }

    # Frame 0: Facing Left (tiles 0, 1) -> 32x16
    # Frame 1: Facing Right (tiles 2, 3) -> 32x16
    w, h = 64, 16
    pixels = [0] * (w * h)

    # Frame 0 (left): 16x8 centered vertically in 32x16
    for t in range(2):
        tw = tiles[t]
        for y in range(8):
            for x in range(8):
                c = color_map.get(tw[y * 8 + x], 0)
                pixels[(4 + y) * w + (8 + t * 8 + x)] = c
    # Afterburner orange flame on right side
    pixels[7 * w + 24] = 9
    pixels[8 * w + 24] = 8

    # Frame 1 (right): 16x8 centered in second 32x16 block
    for t in range(2):
        tw = tiles[2 + t]
        for y in range(8):
            for x in range(8):
                c = color_map.get(tw[y * 8 + x], 0)
                pixels[(4 + y) * w + (32 + 8 + t * 8 + x)] = c
    # Afterburner flame on left side
    pixels[7 * w + 32 + 7] = 9
    pixels[8 * w + 32 + 7] = 8

    write_indexed_png(IMAGES_DIR / "jet.png", w, h, PAL_JET, pixels)
    print("Jet: 2 frames (32x16) -> jet.png")


def convert_balloon():
    raw = (OLD_IMAGES_DIR / "Balloon.bin").read_bytes()
    num_frames = 3
    w, h = num_frames * 16, 32
    pixels = [0] * (w * h)

    color_map = {
        0x0000: 0,
        0x003F: 4,  # red body
        0x5AEB: 8,  # gold bands
        0xEB2F: 6,  # highlight
        0xFFFF: 14, # white highlight
    }

    for f in range(num_frames):
        fx_start = f * 16
        # Top 16x16 at offset 1024 bytes (512 words) + f*512
        top_offset = 1024 + f * 512
        top_words = [struct.unpack("<H", raw[top_offset + i : top_offset + i + 2])[0] for i in range(0, 512, 2)]
        bot_offset = f * 512
        bot_words = [struct.unpack("<H", raw[bot_offset + i : bot_offset + i + 2])[0] for i in range(0, 512, 2)]

        for y in range(16):
            for x in range(16):
                c = color_map.get(top_words[y * 16 + x], 0)
                pixels[y * w + (fx_start + x)] = c
        for y in range(16):
            for x in range(16):
                c = color_map.get(bot_words[y * 16 + x], 0)
                pixels[(16 + y) * w + (fx_start + x)] = c

    write_indexed_png(IMAGES_DIR / "balloon.png", w, h, PAL_BALLOON, pixels)
    print(f"Balloon: {num_frames} frames (16x32) -> balloon.png")


def convert_bomb():
    # 2 frames of 8x8
    w, h = 16, 8
    pixels = [0] * (w * h)
    # Frame 0: Bomb vertical
    bomb_f0 = [
        [0,0,0,1,1,0,0,0],
        [0,0,1,1,1,1,0,0],
        [0,1,2,2,2,2,1,0],
        [0,1,2,3,2,2,1,0],
        [0,1,2,2,2,2,1,0],
        [0,0,1,2,2,1,0,0],
        [0,1,0,1,1,0,1,0],
        [0,1,1,0,0,1,1,0],
    ]
    # Frame 1: Bomb slight tilt
    bomb_f1 = [
        [0,0,0,1,1,0,0,0],
        [0,0,1,1,1,1,0,0],
        [0,1,2,2,3,2,1,0],
        [0,1,2,2,2,2,1,0],
        [0,1,2,2,2,2,1,0],
        [0,0,1,2,2,1,0,0],
        [0,1,1,0,1,1,0,0],
        [0,1,0,0,0,1,1,0],
    ]
    for y in range(8):
        for x in range(8):
            pixels[y * w + x] = bomb_f0[y][x]
            pixels[y * w + 8 + x] = bomb_f1[y][x]
    write_indexed_png(IMAGES_DIR / "bomb.png", w, h, PAL_TANK, pixels)
    print("Bomb: 2 frames (8x8) -> bomb.png")


def convert_bullet():
    # 1 frame of 8x8 tracer
    w, h = 8, 8
    pixels = [0] * 64
    for x in range(2, 6):
        pixels[3 * 8 + x] = 11  # bright yellow/white tracer
        pixels[4 * 8 + x] = 10
    write_indexed_png(IMAGES_DIR / "bullet.png", w, h, PAL_CHOPPER, pixels)
    print("Bullet: 1 frame (8x8) -> bullet.png")


def convert_explosions():
    raw = (OLD_IMAGES_DIR / "Explosion.bin").read_bytes()
    num_frames = 5
    w, h = num_frames * 32, 16
    pixels = [0] * (w * h)

    color_map = {
        0x0000: 0,
        0x002A: 3,
        0x0035: 4,
        0x07FF: 6,
        0x503F: 7,
        0xAD7F: 9,
        0xFFFF: 10,
    }

    for f in range(num_frames):
        fx_start = f * 32
        frame_data = raw[f * 1024 : (f + 1) * 1024]
        left_words = [struct.unpack("<H", frame_data[i : i + 2])[0] for i in range(0, 512, 2)]
        right_words = [struct.unpack("<H", frame_data[512 + i : 512 + i + 2])[0] for i in range(0, 512, 2)]
        for y in range(16):
            for x in range(16):
                c = color_map.get(left_words[y * 16 + x], 0)
                pixels[y * w + (fx_start + x)] = c
            for x in range(16):
                c = color_map.get(right_words[y * 16 + x], 0)
                pixels[y * w + (fx_start + 16 + x)] = c

    write_indexed_png(IMAGES_DIR / "explosion.png", w, h, PAL_EXPLOSION, pixels)
    print(f"Explosion: {num_frames} frames (32x16) -> explosion.png")


def convert_smallexplosion():
    # 4 frames of 16x16
    num_frames = 4
    w, h = num_frames * 16, 16
    pixels = [0] * (w * h)
    for f in range(num_frames):
        fx_start = f * 16
        rad = f + 2
        for y in range(16):
            for x in range(16):
                dx, dy = x - 8, y - 8
                d2 = dx * dx + dy * dy
                if d2 <= rad * rad:
                    pixels[y * w + (fx_start + x)] = 10 if d2 <= 2 else (7 if d2 <= rad * rad // 2 else 4)

    write_indexed_png(IMAGES_DIR / "smallexplosion.png", w, h, PAL_EXPLOSION, pixels)
    print(f"SmallExplosion: {num_frames} frames (16x16) -> smallexplosion.png")


def convert_flags():
    raw = (OLD_IMAGES_DIR / "Flags.bin").read_bytes()
    num_frames = 2
    w, h = num_frames * 16, 16
    pixels = [0] * (w * h)

    color_map = {
        0x0000: 0,
        0x003F: 6,  # red leaf & bars
        0xD6BA: 3,  # flagpole silver
        0xFFFF: 4,  # white center
    }

    for f in range(num_frames):
        fx_start = f * 16
        words = [struct.unpack("<H", raw[f * 512 + i : f * 512 + i + 2])[0] for i in range(0, 512, 2)]
        for y in range(16):
            for x in range(16):
                c = color_map.get(words[y * 16 + x], 0)
                pixels[y * w + (fx_start + x)] = c

    write_indexed_png(IMAGES_DIR / "flags.png", w, h, PAL_FLAGS, pixels)
    print("Flags: 2 frames (16x16) -> flags.png")


def convert_target():
    # 2 frames of 16x16 (red pulsating target indicator marking bunker blast doors)
    w, h = 32, 16
    pixels = [0] * (w * h)
    for f in range(2):
        fx_start = f * 16
        for y in range(16):
            for x in range(16):
                dx, dy = x - 8, y - 8
                d2 = dx * dx + dy * dy
                # Ring + crosshair
                if (dx == 0 or dy == 0) and (2 <= abs(dx) <= 6 or 2 <= abs(dy) <= 6):
                    pixels[y * w + (fx_start + x)] = 7 if f == 0 else 5
                elif 14 <= d2 <= 28:
                    pixels[y * w + (fx_start + x)] = 5 if f == 0 else 7
                elif d2 <= 3:
                    pixels[y * w + (fx_start + x)] = 8

    write_indexed_png(IMAGES_DIR / "target.png", w, h, PAL_TARGET, pixels)
    print("Target: 2 frames (16x16) -> target.png")


# =========================================================================
# Mode 2 Northern Tundra Background & Foreground Tiles and Maps
# =========================================================================

def generate_tiles_and_maps():
    """Generates Mode 2 16x16 4bpp tile sheets and 256x15 world maps."""
    # BG Tiles: 16 tiles (each 16x16)
    # Tile 0: Sky flat (pale northern sky)
    # Tile 1-3: Pale sky gradient with frosty cloud wisps
    # Tile 4-7: Snowy mountain peaks & slopes
    # Tile 8-11: Dark evergreen pine trees (distant forest canopy)
    # Tile 12-15: Low misty hills
    num_bg_tiles = 16
    bg_w, bg_h = num_bg_tiles * 16, 16
    bg_px = [0] * (bg_w * bg_h)

    for t in range(num_bg_tiles):
        tx = t * 16
        for y in range(16):
            for x in range(16):
                idx = y * bg_w + (tx + x)
                if t == 0:
                    bg_px[idx] = 4  # pale sky
                elif t in (1, 2, 3):
                    bg_px[idx] = 4 if y > 8 else 5 if (x + y) % 5 == 0 else 4
                elif t in (4, 5, 6, 7):
                    # Mountain slope
                    slope_y = 15 - ((t - 4) * 4 + x // 4)
                    if y >= slope_y:
                        bg_px[idx] = 8 if y == slope_y or (x + y) % 4 == 0 else 7  # snow & rock
                    else:
                        bg_px[idx] = 4
                elif t in (8, 9, 10, 11):
                    # Pine tree silhouettes
                    center = 8
                    w_tree = max(0, (y - 3) // 2)
                    if abs(x - center) <= w_tree and y >= 3:
                        bg_px[idx] = 11 if (x + y) % 3 == 0 else 10  # dark pine green
                    else:
                        bg_px[idx] = 4
                else:
                    bg_px[idx] = 6 if y >= 10 else 4

    write_indexed_png(IMAGES_DIR / "bg_tiles.png", bg_w, bg_h, PAL_BG, bg_px)

    # FG Tiles: 16 tiles (each 16x16)
    # Tile 0: Empty / transparent air
    # Tile 1: Flat snowy surface
    # Tile 2: Snowbank slope left
    # Tile 3: Snowbank slope right
    # Tile 4: Deep solid ice / rock subsurface
    # Tile 5: Landing pad surface (diamond tread / hazard edge)
    # Tile 6: Canadian Home Base medical tent left roof
    # Tile 7: Canadian Home Base medical tent right roof
    # Tile 8: Canadian Home Base tent wall with Red Cross / Maple emblem
    # Tile 9: Bunker concrete roof / parapet
    # Tile 10: Bunker wall (reinforced concrete)
    # Tile 11: Bunker blast door (intact steel blast door)
    # Tile 12: Bunker blast door (breached / blown open rubble!)
    # Tile 13: Bunker foundation / ground anchor
    # Tile 14: Trench / barbed wire post
    # Tile 15: Snow mound
    num_fg_tiles = 16
    fg_w, fg_h = num_fg_tiles * 16, 16
    fg_px = [0] * (fg_w * fg_h)

    for t in range(num_fg_tiles):
        tx = t * 16
        for y in range(16):
            for x in range(16):
                idx = y * fg_w + (tx + x)
                if t == 0:
                    fg_px[idx] = 0  # air
                elif t == 1:
                    # Flat snowy ground
                    if y == 0:
                        fg_px[idx] = 8  # pure snow white
                    elif y < 4:
                        fg_px[idx] = 7  # packed snow
                    else:
                        fg_px[idx] = 5 if (x ^ y) & 4 else 6  # frozen dirt/rock
                elif t == 2:
                    # Slope left
                    if y >= 15 - x:
                        fg_px[idx] = 8 if y == 15 - x else 6
                    else:
                        fg_px[idx] = 0
                elif t == 3:
                    # Slope right
                    if y >= x:
                        fg_px[idx] = 8 if y == x else 6
                    else:
                        fg_px[idx] = 0
                elif t == 4:
                    # Deep rock
                    fg_px[idx] = 3 if (x ^ y) & 6 else 4
                elif t == 5:
                    # Landing pad surface
                    if y == 0:
                        fg_px[idx] = 14 if x % 4 < 2 else 2  # hazard striping
                    elif y == 1:
                        fg_px[idx] = 6
                    else:
                        fg_px[idx] = 5 if (x % 4 == 0 or y % 4 == 0) else 4  # metal grating
                elif t == 6:
                    # Tent roof left
                    if y >= 15 - x:
                        fg_px[idx] = 7 if y == 15 - x else 6
                    else:
                        fg_px[idx] = 0
                elif t == 7:
                    # Tent roof right
                    if y >= x:
                        fg_px[idx] = 7 if y == x else 6
                    else:
                        fg_px[idx] = 0
                elif t == 8:
                    # Medical tent wall with red cross
                    fg_px[idx] = 7  # white canvas
                    if 4 <= x <= 11 and 4 <= y <= 11:
                        if (6 <= x <= 9) or (6 <= y <= 9):
                            fg_px[idx] = 10  # Red Cross!
                elif t == 9:
                    # Bunker roof
                    fg_px[idx] = 2 if y == 0 else (4 if y < 4 else 3)
                elif t == 10:
                    # Bunker wall
                    fg_px[idx] = 3 if (x % 8 == 0 or y % 8 == 0) else 4
                elif t == 11:
                    # Intact steel blast door
                    if 2 <= x <= 13:
                        fg_px[idx] = 1 if (x in (2, 13) or y in (0, 15)) else (5 if y % 3 == 0 else 4)
                    else:
                        fg_px[idx] = 3
                elif t == 12:
                    # Breached blast door rubble
                    if 2 <= x <= 13:
                        fg_px[idx] = 0 if (y < 12 and 4 <= x <= 11) else (1 if (x + y) % 3 == 0 else 3)
                    else:
                        fg_px[idx] = 3
                elif t == 13:
                    # Bunker foundation
                    fg_px[idx] = 2 if y < 4 else 3
                elif t == 14:
                    # Trench / barbed wire
                    fg_px[idx] = 2 if (x in (4, 11) and y >= 6) else (7 if y == 8 else 0)
                elif t == 15:
                    # Snow mound
                    if y >= 8:
                        fg_px[idx] = 8 if y == 8 else 7
                    else:
                        fg_px[idx] = 0

    write_indexed_png(IMAGES_DIR / "fg_tiles.png", fg_w, fg_h, PAL_FG, fg_px)
    print("Tiles: bg_tiles.png and fg_tiles.png generated.")

    # World Map: 256 tiles wide x 15 tiles high (4096 px x 240 px)
    # Ground starts at tile row 12 (Y = 192 px)
    fg_map = bytearray(256 * 15)
    bg_map = bytearray(256 * 15)

    # Populate Distant BG Parallax:
    # Row 0-7: Sky (tiles 0-3)
    # Row 8-10: Mountain peaks (tiles 4-7)
    # Row 11: Pine forest canopy (tiles 8-11)
    # Row 12-14: Misty snow ground (tile 12)
    for c in range(256):
        for r in range(15):
            idx = r * 256 + c
            if r < 7:
                bg_map[idx] = (c // 16) % 3 + 1
            elif 7 <= r <= 10:
                bg_map[idx] = 4 + ((c + r) % 4)
            elif r == 11:
                bg_map[idx] = 8 + (c % 4)
            else:
                bg_map[idx] = 12

    # Populate Foreground World Map:
    # Row 0-11: Air (tile 0)
    # Row 12: Ground surface (tile 1)
    # Row 13-14: Solid rock/ice (tile 4)
    for c in range(256):
        for r in range(12):
            fg_map[r * 256 + c] = 0
        fg_map[12 * 256 + c] = 1
        fg_map[13 * 256 + c] = 4
        fg_map[14 * 256 + c] = 4

    # Place 4 Enemy Fortified Compounds across the 256-column map:
    # Compound 1: col 30..42 (~X=480..672)
    # Compound 2: col 80..92 (~X=1280..1472)
    # Compound 3: col 135..147 (~X=2160..2352)
    # Compound 4: col 185..197 (~X=2960..3152)
    compounds = [30, 80, 135, 185]
    for base_col in compounds:
        # Bunker roof at row 10, walls at row 11-12
        for dc in range(12):
            c = base_col + dc
            fg_map[10 * 256 + c] = 9  # roof
            if dc in (5, 6):
                fg_map[11 * 256 + c] = 11  # blast door top
                fg_map[12 * 256 + c] = 11  # blast door bottom
            else:
                fg_map[11 * 256 + c] = 10  # wall
                fg_map[12 * 256 + c] = 10  # wall

    # Place Canadian Home Base at far right (col 235..255, ~X=3760..4080)
    # Landing pad: col 238..246
    for c in range(238, 247):
        fg_map[12 * 256 + c] = 5  # landing pad surface
    # Medical rescue tents: col 248..253
    fg_map[11 * 256 + 249] = 6
    fg_map[11 * 256 + 250] = 7
    fg_map[12 * 256 + 249] = 8
    fg_map[12 * 256 + 250] = 8

    fg_map[11 * 256 + 252] = 6
    fg_map[11 * 256 + 253] = 7
    fg_map[12 * 256 + 252] = 8
    fg_map[12 * 256 + 253] = 8

    (IMAGES_DIR / "bg_map.bin").write_bytes(bytes(bg_map))
    (IMAGES_DIR / "fg_map.bin").write_bytes(bytes(fg_map))
    print("Maps: bg_map.bin and fg_map.bin written (256x15 = 3840 bytes each).")


def generate_header():
    lines = [
        "/* Generated by gtools/gen_art.py. Do not edit; regenerate instead. */",
        "#ifndef ASSETS_H",
        "#define ASSETS_H",
        "",
        "/* Palette Indices */",
    ]
    for i, (name, _) in enumerate(ALL_PALETTES):
        lines.append(f"#define {name} {i}")
    lines.append(f"#define PAL_COUNT {len(ALL_PALETTES)}")
    lines.append("")

    sheets = [
        ("CHOPPER", 32, 16, 22),
        ("HOSTAGES", 16, 16, 10),
        ("TANK", 40, 16, 6),
        ("JET", 32, 16, 2),
        ("BALLOON", 16, 32, 3),
        ("BOMB", 8, 8, 2),
        ("BULLET", 8, 8, 1),
        ("EXPLOSION", 32, 16, 5),
        ("SMALLEXPLOSION", 16, 16, 4),
        ("FLAGS", 16, 16, 2),
        ("TARGET", 16, 16, 2),
    ]

    for pfx, w, h, frames in sheets:
        lines += [
            f"#define {pfx}_W {w}",
            f"#define {pfx}_H {h}",
            f"#define {pfx}_FRAMES {frames}",
            f"#define {pfx}_FRAME_BYTES {w * h // 2}",
            f"#define {pfx}_TOTAL_BYTES {w * h // 2 * frames}",
            "",
        ]

    lines += [
        "#define WORLD_MAP_COLS 256",
        "#define WORLD_MAP_ROWS 15",
        "#define WORLD_MAP_BYTES (WORLD_MAP_COLS * WORLD_MAP_ROWS)",
        "",
        "#endif /* ASSETS_H */",
        "",
    ]
    (GEN_DIR / "assets.h").write_text("\n".join(lines))
    print("Header: src/gen/assets.h generated.")


def main():
    generate_palettes_blob()
    convert_chopper()
    convert_hostages()
    convert_tank()
    convert_jet()
    convert_balloon()
    convert_bomb()
    convert_bullet()
    convert_explosions()
    convert_smallexplosion()
    convert_flags()
    convert_target()
    generate_tiles_and_maps()
    generate_header()
    print("All graphic assets successfully generated!")


if __name__ == "__main__":
    main()
