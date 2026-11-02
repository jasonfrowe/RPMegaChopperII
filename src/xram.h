/* RP6502 XRAM Mapping for RPMegaChopperII */

#ifndef XRAM_H
#define XRAM_H

#include <rp6502.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "gen/assets.h"

/* ------------------------------------------------------------------ */
/* RIA Keyboard & Gamepad Definitions                                 */
/* ------------------------------------------------------------------ */

#define KEYBOARD_NO_KEY 0
#define KEYBOARD_NUM_LOCK 1
#define KEYBOARD_CAPS_LOCK 2
#define KEYBOARD_SCROLL_LOCK 3

#define KEYBOARD_PRESSED(keys, code) ((keys)[(code) >> 3] & (1 << ((code) & 7)))
#define xreg_ria_keyboard(...) xreg(0, 0, 0, __VA_ARGS__)

typedef struct
{
    uint8_t keys[32];
} keyboard_t;

#define GAMEPAD_PLAYERS 4
#define GAMEPAD_DPAD_UP 0x01
#define GAMEPAD_DPAD_DOWN 0x02
#define GAMEPAD_DPAD_LEFT 0x04
#define GAMEPAD_DPAD_RIGHT 0x08

#define GAMEPAD_FEAT_TYPE_MASK 0x30
#define GAMEPAD_FEAT_STICKS 0x40
#define GAMEPAD_FEAT_CONNECTED 0x80

#define GAMEPAD_BTN0_A 0x01
#define GAMEPAD_BTN0_B 0x02
#define GAMEPAD_BTN0_C 0x04
#define GAMEPAD_BTN0_X 0x08
#define GAMEPAD_BTN0_Y 0x10
#define GAMEPAD_BTN0_Z 0x20
#define GAMEPAD_BTN0_L1 0x40
#define GAMEPAD_BTN0_R1 0x80

#define GAMEPAD_BTN1_L2 0x01
#define GAMEPAD_BTN1_R2 0x02
#define GAMEPAD_BTN1_SELECT 0x04
#define GAMEPAD_BTN1_START 0x08

#define xreg_ria_gamepad(...) xreg(0, 0, 2, __VA_ARGS__)

typedef struct
{
    uint8_t dpad;
    uint8_t sticks;
    uint8_t btn0;
    uint8_t btn1;
    int8_t lx;
    int8_t ly;
    int8_t rx;
    int8_t ry;
    uint8_t l2;
    uint8_t r2;
} gamepad_player_t;

typedef struct
{
    gamepad_player_t player[GAMEPAD_PLAYERS];
} gamepad_t;

/* ------------------------------------------------------------------ */
/* RIA OPL2 Soundcard                                                 */
/* ------------------------------------------------------------------ */

#define xreg_ria_opl(...) xreg(0, 1, 1, __VA_ARGS__)

typedef struct
{
    uint8_t reg[256];
} opl_t;

/* ------------------------------------------------------------------ */
/* VGA Modes and Configurations                                       */
/* ------------------------------------------------------------------ */

#define xreg_vga_canvas(...) xreg(1, 0, 0, __VA_ARGS__)
#define CANVAS_320X240 1

#define COLOR_FROM_RGB8(r, g, b) \
    ((((unsigned)(b) >> 3) << 11) | (((unsigned)(g) >> 3) << 6) | ((unsigned)(r) >> 3))
#define COLOR_ALPHA_MASK (1u << 5)

/* VGA Mode 1: Character (HUD text) */
#define xreg_vga_mode1(...) xreg(1, 0, 1, 1, __VA_ARGS__)
#define MODE1_4BPP 0x02
#define MODE1_8X8 0x00

typedef struct
{
    bool x_wrap;
    bool y_wrap;
    int16_t x_pos_px;
    int16_t y_pos_px;
    int16_t width_chars;
    int16_t height_chars;
    uint16_t xram_data_ptr;
    uint16_t xram_palette_ptr;
    uint16_t xram_font_ptr;
} mode1_config_t;

typedef struct
{
    uint8_t glyph_code;
    uint8_t bg_fg_index;
} mode1_4bpp_data_t;

/* VGA Mode 2: Tilemap (Ground & Parallax) */
#define xreg_vga_mode2(...) xreg(1, 0, 1, 2, __VA_ARGS__)
#define MODE2_4BPP 0x02
#define MODE2_8X8 0x00
#define MODE2_16X16 0x08

typedef struct
{
    bool x_wrap;
    bool y_wrap;
    int16_t x_pos_px;
    int16_t y_pos_px;
    int16_t width_tiles;
    int16_t height_tiles;
    uint16_t xram_data_ptr;
    uint16_t xram_palette_ptr;
    uint16_t xram_tile_ptr;
} mode2_config_t;

/* VGA Mode 5: Custom 4bpp Sprites */
#define xreg_vga_mode5(...) xreg(1, 0, 1, 5, __VA_ARGS__)
#define MODE5_1BPP 0x00
#define MODE5_4BPP 0x02
#define MODE5_CUSTOM 0x38
#define MODE5_HFLIP 0x10
#define MODE5_VFLIP 0x20

#define MODE5_SIZE(width, height) \
    ((((height) / 4 - 1) << 4) | ((width) / 4 - 1))

typedef struct
{
    int16_t x_pos_px;
    int16_t y_pos_px;
    uint16_t xram_sprite_ptr;
    uint16_t palette_ptr;
    uint8_t width_height;
    uint8_t options;
} mode5_csprite_t;

/* ------------------------------------------------------------------ */
/* Sprites (plane 2), back to front: later ones cover earlier ones.   */
/* ------------------------------------------------------------------ */

#define SPR_TARGET_START 0
#define SPR_TARGET_COUNT NUM_COMPOUNDS
#define SPR_FLAG (SPR_TARGET_START + SPR_TARGET_COUNT)
#define SPR_BORDER_FLAG (SPR_FLAG + 1)
#define SPR_TANK_START (SPR_BORDER_FLAG + 1)
#define SPR_TANK_COUNT 4
#define SPR_HOSTAGE_START (SPR_TANK_START + SPR_TANK_COUNT)
#define SPR_HOSTAGE_COUNT 16
#define SPR_BALLOON_START (SPR_HOSTAGE_START + SPR_HOSTAGE_COUNT)
#define SPR_BALLOON_COUNT 4
#define SPR_JET_START (SPR_BALLOON_START + SPR_BALLOON_COUNT)
#define SPR_JET_COUNT 2
#define SPR_BOMB_START (SPR_JET_START + SPR_JET_COUNT)
#define SPR_BOMB_COUNT 4
#define SPR_EBULLET_START (SPR_BOMB_START + SPR_BOMB_COUNT)
#define SPR_EBULLET_COUNT 8
#define SPR_BULLET_START (SPR_EBULLET_START + SPR_EBULLET_COUNT)
#define SPR_BULLET_COUNT 6
#define SPR_CHOPPER (SPR_BULLET_START + SPR_BULLET_COUNT)
#define SPR_EXPLOSION_START (SPR_CHOPPER + 1)
#define SPR_EXPLOSION_COUNT 6
#define SPR_SMALLEXP_START (SPR_EXPLOSION_START + SPR_EXPLOSION_COUNT)
#define SPR_SMALLEXP_COUNT 8
#define SPR_SNOW_START (SPR_SMALLEXP_START + SPR_SMALLEXP_COUNT)
#define SPR_SNOW_COUNT 24
#define SPR_TOTAL_COUNT (SPR_SNOW_START + SPR_SNOW_COUNT)

/* Text: the status bar at the top, and a message box over the sky. */
#define HUD_COLS 40
#define HUD_ROWS 2
#define MSG_COLS 40
#define MSG_ROWS 6
#define MSG_Y 40

#define SFX_DATA_MAX 3072

typedef struct
{
    uint16_t c[16];
} palette_t;

/* ------------------------------------------------------------------ */
/* Full XRAM Memory Structure                                         */
/* ------------------------------------------------------------------ */

typedef struct
{
    /* OPL2 registers must begin at page boundary 0x0000 */
    opl_t opl;

    keyboard_t keyboard;
    gamepad_t gamepad;
    mode2_config_t far_config; /* Plane 0: sky, aurora, mountains */
    mode2_config_t mid_config; /* Plane 1: hills and forest */
    mode2_config_t fg_config;  /* Plane 2: the ground */
    mode1_config_t hud_config; /* Plane 2: status bar */
    mode1_config_t msg_config; /* Plane 2: message box */
    mode5_csprite_t spr[SPR_TOTAL_COUNT];
    mode1_4bpp_data_t hud[HUD_ROWS][HUD_COLS];
    mode1_4bpp_data_t msg[MSG_ROWS][MSG_COLS];

    palette_t palettes[PAL_COUNT];
    uint8_t img_chopper[CHOPPER_FRAMES][CHOPPER_FRAME_BYTES];
    uint8_t img_hostages[HOSTAGES_FRAMES][HOSTAGES_FRAME_BYTES];
    uint8_t img_tank[TANK_FRAMES][TANK_FRAME_BYTES];
    uint8_t img_jet[JET_FRAMES][JET_FRAME_BYTES];
    uint8_t img_balloon[BALLOON_FRAMES][BALLOON_FRAME_BYTES];
    uint8_t img_bomb[BOMB_FRAMES][BOMB_FRAME_BYTES];
    uint8_t img_bullet[BULLET_FRAMES][BULLET_FRAME_BYTES];
    uint8_t img_explosion[EXPLOSION_FRAMES][EXPLOSION_FRAME_BYTES];
    uint8_t img_smallexplosion[SMALLEXPLOSION_FRAMES][SMALLEXPLOSION_FRAME_BYTES];
    uint8_t img_flags[FLAGS_FRAMES][FLAGS_FRAME_BYTES];
    uint8_t img_target[TARGET_FRAMES][TARGET_FRAME_BYTES];
    uint8_t img_snow[SNOW_FRAMES][SNOW_FRAME_BYTES];
    uint8_t img_gust[GUST_FRAMES][GUST_FRAME_BYTES];
    uint8_t img_logo[LOGO_PIECES][LOGO_PIECE_BYTES];

    uint8_t tiles_far[FAR_TILES][FAR_TILE_BYTES];
    uint8_t tiles_mid[MID_TILES][MID_TILE_BYTES];
    uint8_t tiles_fg[FG_TILES][FG_TILE_BYTES];
    uint8_t map_far[FAR_MAP_ROWS][FAR_MAP_COLS];
    uint8_t map_mid[MID_MAP_ROWS][MID_MAP_COLS];
    uint8_t map_fg[FG_MAP_ROWS][FG_MAP_COLS];

    uint8_t sfx_data[SFX_DATA_MAX];
} xram_layout_t;

#define XRAM_OPL offsetof(xram_layout_t, opl)
_Static_assert((XRAM_OPL & 0xFF) == 0, "The OPL2 registers must start on a page boundary.");

#define XRAM_KEYBOARD offsetof(xram_layout_t, keyboard)
#define XRAM_GAMEPAD offsetof(xram_layout_t, gamepad)
#define XRAM_FAR_CONFIG offsetof(xram_layout_t, far_config)
#define XRAM_MID_CONFIG offsetof(xram_layout_t, mid_config)
#define XRAM_FG_CONFIG offsetof(xram_layout_t, fg_config)
#define XRAM_HUD_CONFIG offsetof(xram_layout_t, hud_config)
#define XRAM_MSG_CONFIG offsetof(xram_layout_t, msg_config)
#define XRAM_SPR offsetof(xram_layout_t, spr)
#define XRAM_HUD offsetof(xram_layout_t, hud)
#define XRAM_MSG offsetof(xram_layout_t, msg)
#define XRAM_PALETTES offsetof(xram_layout_t, palettes)

#define XRAM_IMG_CHOPPER offsetof(xram_layout_t, img_chopper)
#define XRAM_IMG_HOSTAGES offsetof(xram_layout_t, img_hostages)
#define XRAM_IMG_TANK offsetof(xram_layout_t, img_tank)
#define XRAM_IMG_JET offsetof(xram_layout_t, img_jet)
#define XRAM_IMG_BALLOON offsetof(xram_layout_t, img_balloon)
#define XRAM_IMG_BOMB offsetof(xram_layout_t, img_bomb)
#define XRAM_IMG_BULLET offsetof(xram_layout_t, img_bullet)
#define XRAM_IMG_EXPLOSION offsetof(xram_layout_t, img_explosion)
#define XRAM_IMG_SMALLEXPLOSION offsetof(xram_layout_t, img_smallexplosion)
#define XRAM_IMG_FLAGS offsetof(xram_layout_t, img_flags)
#define XRAM_IMG_TARGET offsetof(xram_layout_t, img_target)
#define XRAM_IMG_SNOW offsetof(xram_layout_t, img_snow)
#define XRAM_IMG_GUST offsetof(xram_layout_t, img_gust)
#define XRAM_IMG_LOGO offsetof(xram_layout_t, img_logo)

#define XRAM_TILES_FAR offsetof(xram_layout_t, tiles_far)
#define XRAM_TILES_MID offsetof(xram_layout_t, tiles_mid)
#define XRAM_TILES_FG offsetof(xram_layout_t, tiles_fg)
#define XRAM_MAP_FAR offsetof(xram_layout_t, map_far)
#define XRAM_MAP_MID offsetof(xram_layout_t, map_mid)
#define XRAM_MAP_FG offsetof(xram_layout_t, map_fg)
#define XRAM_SFX_DATA offsetof(xram_layout_t, sfx_data)

#define PAL_ADDR(p) (XRAM_PALETTES + (p) * sizeof(palette_t))

/* The top of XRAM is left alone, as in MegaGammaForce. */
_Static_assert(sizeof(xram_layout_t) <= 0xFF00, "xram_layout_t exceeds XRAM budget.");

#endif /* XRAM_H */
