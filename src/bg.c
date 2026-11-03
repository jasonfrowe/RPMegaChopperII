#include <rp6502.h>
#include "bg.h"
#include "game.h"
#include "level.h"
#include "weather.h"
#include "xram.h"

/*
 * Three tile layers, back to front:
 *   plane 0  far: sky, aurora and mountains, 8x8 tiles, a quarter speed
 *   plane 1  mid: hills and forest, 8x8 tiles, half speed
 *   plane 2  fg:  the ground, 16x16 tiles, full speed
 * The far and mid maps repeat (x_wrap); the ground map is the whole world.
 * Plane 2 also carries the status bar and message box (hud.c) on the
 * scanlines the ground leaves free.
 */

static mode2_config_t far_cfg, mid_cfg, fg_cfg;
static bool scrolled;

static void layer(mode2_config_t *c, bool wrap, int16_t y, int16_t w, int16_t h,
                  uint16_t map, uint8_t pal, uint16_t tiles)
{
    c->x_wrap = wrap;
    c->y_wrap = false;
    c->x_pos_px = 0;
    c->y_pos_px = y;
    c->width_tiles = w;
    c->height_tiles = h;
    c->xram_data_ptr = map;
    c->xram_palette_ptr = PAL_ADDR(pal);
    c->xram_tile_ptr = tiles;
}

void bg_init(void)
{
    layer(&far_cfg, true, FAR_Y, FAR_MAP_COLS, FAR_MAP_ROWS, XRAM_MAP_FAR, PAL_FAR, XRAM_TILES_FAR);
    layer(&mid_cfg, true, MID_Y, MID_MAP_COLS, MID_MAP_ROWS, XRAM_MAP_MID, PAL_MID, XRAM_TILES_MID);
    layer(&fg_cfg, false, FG_Y, FG_MAP_COLS, FG_MAP_ROWS, XRAM_MAP_FG, PAL_FG, XRAM_TILES_FG);
    xram0_write(XRAM_FAR_CONFIG, &far_cfg, sizeof(far_cfg));
    xram0_write(XRAM_MID_CONFIG, &mid_cfg, sizeof(mid_cfg));
    xram0_write(XRAM_FG_CONFIG, &fg_cfg, sizeof(fg_cfg));

    xreg_vga_mode2(MODE2_4BPP | MODE2_8X8, XRAM_FAR_CONFIG, 0, HUD_H, FAR_Y + FAR_MAP_ROWS * FAR_TILE);
    xreg_vga_mode2(MODE2_4BPP | MODE2_8X8, XRAM_MID_CONFIG, 1, MID_Y, MID_Y + MID_MAP_ROWS * MID_TILE);
    xreg_vga_mode2(MODE2_4BPP | MODE2_16X16, XRAM_FG_CONFIG, 2, FG_Y, SCREEN_H);
}

void bg_update(int16_t cam)
{
    int16_t fx = -(cam >> 2), mx = -(cam >> 1), gx = -cam;
    if (fx != far_cfg.x_pos_px || mx != mid_cfg.x_pos_px || gx != fg_cfg.x_pos_px) {
        far_cfg.x_pos_px = fx;
        mid_cfg.x_pos_px = mx;
        fg_cfg.x_pos_px = gx;
        scrolled = true;
    }
}

void bg_commit(void)
{
    if (!scrolled)
        return;
    scrolled = false;
    xram0_write(XRAM_FAR_CONFIG + offsetof(mode2_config_t, x_pos_px), &far_cfg.x_pos_px, 2);
    xram0_write(XRAM_MID_CONFIG + offsetof(mode2_config_t, x_pos_px), &mid_cfg.x_pos_px, 2);
    xram0_write(XRAM_FG_CONFIG + offsetof(mode2_config_t, x_pos_px), &fg_cfg.x_pos_px, 2);
}

/*
 * Palettes. The far, mid and ground palettes are kept here as built, and
 * what goes to XRAM is worked out from them: the aurora's five colors step
 * along a brightness wave, so light ripples along the curtains; the radio
 * masts blink; and in a storm everything fades toward a white haze, the far
 * layers most, the ground least.
 */
static palette_t base[3]; /* far, mid, ground */
static const uint8_t pal_id[3] = {PAL_FAR, PAL_MID, PAL_FG};
/* How far each layer fades at the storm's worst, in sixteenths. */
static const uint8_t fade_max[3] = {13, 10, 4};
#define HAZE_R 22 /* the whiteout, in 5-bit channels */
#define HAZE_G 23
#define HAZE_B 26

static uint8_t aurora_t, beacon;
static uint8_t last_storm = 0xFF;

void bg_palettes_init(void)
{
    for (uint8_t i = 0; i < 3; i++)
        xram0_read(&base[i], PAL_ADDR(pal_id[i]), sizeof(palette_t));
    last_storm = 0xFF;
}

static uint16_t haze(uint16_t c, uint8_t k)
{
    int8_t r = c & 31, g = (c >> 6) & 31, b = (c >> 11) & 31;
    r += (int8_t)(((HAZE_R - r) * k) >> 4);
    g += (int8_t)(((HAZE_G - g) * k) >> 4);
    b += (int8_t)(((HAZE_B - b) * k) >> 4);
    return (uint16_t)((uint16_t)b << 11 | (uint16_t)g << 6 | (c & 0x20) | r);
}

static palette_t faded[3]; /* base, faded by the current storm */
static uint8_t fade_k[3];

/* Fade the built palettes for a storm level. Only when it changes. */
static void refade(uint8_t storm_level)
{
    for (uint8_t l = 0; l < 3; l++) {
        uint8_t k = (uint8_t)(storm_level * fade_max[l] / STORM_MAX);
        fade_k[l] = k;
        for (uint8_t i = 0; i < 16; i++) {
            uint16_t c = base[l].c[i];
            faded[l].c[i] = (k && (c & 0x20)) ? haze(c, k) : c; /* transparent ones stay */
        }
    }
}

static void write_palette(uint8_t layer)
{
    palette_t *p = &faded[layer];
    uint8_t k = fade_k[layer];
    if (layer == 0)
        for (uint8_t i = 0; i < 5; i++) {
            uint16_t c = aurora_waves[level_theme][(uint8_t)(i * 2 + aurora_t) % AURORA_WAVE_N];
            p->c[FAR_AURORA_FIRST + i] = k ? haze(c, k) : c;
        }
    if (layer == 1) {
        uint16_t c = beacon ? mid_beacon_on[level_theme] : MID_BEACON_OFF;
        p->c[MID_BEACON_INDEX] = k ? haze(c, k) : c;
    }
    xram0_write(PAL_ADDR(pal_id[layer]), p, sizeof(palette_t));
}

void bg_animate(uint8_t storm_level)
{
    bool all = storm_level != last_storm;
    if (all) {
        last_storm = storm_level;
        refade(storm_level);
    }
    if ((frame_count & 7) == 0) {
        aurora_t = (uint8_t)(aurora_t + 1) % AURORA_WAVE_N;
        write_palette(0);
    } else if (all) {
        write_palette(0);
    }
    if ((frame_count & 31) == 0) {
        beacon = !beacon;
        write_palette(1);
    } else if (all) {
        write_palette(1);
    }
    if (all)
        write_palette(2);
}

static void door_tiles(uint8_t i, const uint8_t (*t)[DOOR_W])
{
    for (uint8_t r = 0; r < DOOR_TILE_ROWS; r++)
        xram0_write(XRAM_MAP_FG + (DOOR_TILE_ROW0 + r) * FG_MAP_COLS + compound_cols[i] + DOOR_COL, t[r], DOOR_W);
}

void bg_breach_door(uint8_t i)
{
    door_tiles(i, door_breached[level_theme]);
}

void bg_reset_doors(void)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
        door_tiles(i, door_intact[level_theme]);
}
