#include <rp6502.h>
#include "bg.h"
#include "game.h"
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

/* Palette animation: the aurora's five colors step along a brightness
 * wave, so light ripples along the curtains; the radio masts blink. */
void bg_animate(void)
{
    static uint8_t t, beacon;
    if ((frame_count & 7) == 0) {
        uint16_t c[5];
        t = (uint8_t)(t + 1) % AURORA_WAVE_N;
        for (uint8_t i = 0; i < 5; i++)
            c[i] = aurora_wave[(uint8_t)(i * 2 + t) % AURORA_WAVE_N];
        xram0_write(PAL_ADDR(PAL_FAR) + FAR_AURORA_FIRST * 2, c, sizeof(c));
    }
    if ((frame_count & 31) == 0) {
        beacon = !beacon;
        xram0_poke16(PAL_ADDR(PAL_MID) + MID_BEACON_INDEX * 2, beacon ? MID_BEACON_ON : MID_BEACON_OFF);
    }
}

static void door_tiles(uint8_t i, const uint8_t (*t)[DOOR_W])
{
    for (uint8_t r = 0; r < DOOR_TILE_ROWS; r++)
        xram0_write(XRAM_MAP_FG + (DOOR_TILE_ROW0 + r) * FG_MAP_COLS + compound_cols[i] + DOOR_COL, t[r], DOOR_W);
}

void bg_breach_door(uint8_t i)
{
    door_tiles(i, door_breached);
}

void bg_reset_doors(void)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
        door_tiles(i, door_intact);
}
