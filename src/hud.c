#include <rp6502.h>
#include <string.h>
#include "game.h"
#include "hud.h"
#include "xram.h"

static mode1_4bpp_data_t hud_grid[HUD_ROWS][HUD_COLS];
static bool hud_dirty;

void hud_clear(void)
{
    for (uint8_t r = 0; r < HUD_ROWS; r++) {
        for (uint8_t c = 0; c < HUD_COLS; c++) {
            hud_grid[r][c].glyph_code = ' ';
            hud_grid[r][c].bg_fg_index = (1 << 4) | 7; /* Black bg, white fg */
        }
    }
    hud_dirty = true;
}

void hud_text(uint8_t col, uint8_t row, const char *str, uint8_t fg, uint8_t bg)
{
    if (row >= HUD_ROWS) return;
    uint8_t color_attr = (bg << 4) | (fg & 0x0F);
    while (*str && col < HUD_COLS) {
        hud_grid[row][col].glyph_code = (uint8_t)*str++;
        hud_grid[row][col].bg_fg_index = color_attr;
        col++;
    }
    hud_dirty = true;
}

void hud_u16(uint8_t col, uint8_t row, uint16_t val, uint8_t width, uint8_t fg, uint8_t bg)
{
    char buf[10];
    for (int8_t i = width - 1; i >= 0; i--) {
        buf[i] = '0' + (val % 10);
        val /= 10;
    }
    buf[width] = '\0';
    hud_text(col, row, buf, fg, bg);
}

void hud_u32(uint8_t col, uint8_t row, uint32_t val, uint8_t width, uint8_t fg, uint8_t bg)
{
    char buf[12];
    for (int8_t i = width - 1; i >= 0; i--) {
        buf[i] = '0' + (val % 10);
        val /= 10;
    }
    buf[width] = '\0';
    hud_text(col, row, buf, fg, bg);
}

void hud_init(void)
{
    hud_clear();

    mode1_config_t cfg = {
        .x_wrap = false,
        .y_wrap = false,
        .x_pos_px = 0,
        .y_pos_px = 0,
        .width_chars = HUD_COLS,
        .height_chars = HUD_ROWS,
        .xram_data_ptr = XRAM_HUD,
        .xram_palette_ptr = PAL_ADDR(PAL_HUD),
        .xram_font_ptr = 0xFFFF, /* Default ROM font (IBM CP437) */
    };
    xram0_write(XRAM_HUD_CONFIG, &cfg, sizeof(cfg));

    /* Register Plane 2 Character Mode */
    xreg_vga_mode1(MODE1_4BPP | MODE1_8X8, XRAM_HUD_CONFIG, 2, 0, 0);

    hud_update();
    hud_commit();
}

void hud_update(void)
{
    /* Row 0:
     * SCORE:000000  SAVED:00  CARGO:00/16  LOST:00
     */
    hud_text(0, 0, "SCORE:", 8, 1);  /* Gold */
    hud_u32(6, 0, score, 6, 7, 1);   /* White */

    hud_text(14, 0, "SAVED:", 10, 1); /* Green */
    hud_u16(20, 0, saved_count, 2, 7, 1);

    hud_text(24, 0, "CARGO:", 11, 1); /* Cyan */
    hud_u16(30, 0, cargo_count, 2, (cargo_count == MAX_CARGO ? 9 : 7), 1);
    hud_text(32, 0, "/16", 11, 1);

    hud_text(36, 0, "L:", 9, 1);     /* Red */
    hud_u16(38, 0, lost_count, 2, 7, 1);

    /* Row 1:
     * S1 SHP:3 RADAR:[......................]
     */
    hud_text(0, 1, "S", 14, 1);
    hud_u16(1, 1, current_level, 1, 7, 1);
    hud_text(2, 1, " ", 7, 1);
    hud_text(3, 1, "SHP:", 8, 1);
    hud_u16(7, 1, lives, 1, 7, 1);
    hud_text(8, 1, " ", 7, 1);

    hud_text(9, 1, "RADAR:[", 13, 1);

    /* 22-character tactical radar strip across the 4096-pixel world */
    char radar[23];
    for (uint8_t i = 0; i < 22; i++) {
        radar[i] = '.';
    }
    radar[22] = '\0';

    /* Bunkers at cols: 30, 80, 135, 185 (scaled into 0..21) */
    radar[(30 * 22) / 256] = '4';
    radar[(80 * 22) / 256] = '3';
    radar[(135 * 22) / 256] = '2';
    radar[(185 * 22) / 256] = '1';

    /* Home Base at far right */
    radar[21] = 'H';

    /* Chopper position */
    int16_t chop_x_px = FROM_SUB(camera_x + TO_SUB(SCREEN_W / 2));
    if (chop_x_px < 0) chop_x_px = 0;
    if (chop_x_px >= WORLD_W_PX) chop_x_px = WORLD_W_PX - 1;
    uint8_t chop_radar_idx = (uint8_t)(((uint32_t)chop_x_px * 22) / WORLD_W_PX);
    if (chop_radar_idx >= 22) chop_radar_idx = 21;
    radar[chop_radar_idx] = '^';

    hud_text(16, 1, radar, 10, 1);
    hud_text(38, 1, "]", 13, 1);

    hud_dirty = true;
}

void hud_commit(void)
{
    if (hud_dirty) {
        xram0_write(XRAM_HUD, hud_grid, sizeof(hud_grid));
        hud_dirty = false;
    }
}
