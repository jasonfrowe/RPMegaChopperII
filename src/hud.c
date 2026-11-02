#include <rp6502.h>
#include <string.h>
#include "compounds.h"
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "player.h"
#include "xram.h"

static mode1_4bpp_data_t hud_grid[HUD_ROWS][HUD_COLS];
static mode1_4bpp_data_t msg_grid[MSG_ROWS][MSG_COLS];
static bool hud_dirty, msg_dirty;
static uint8_t flash_timer;

/* CP437 glyphs */
#define G_BOX 254   /* filled square */
#define G_DOT 250   /* middle dot */
#define G_UP 30     /* up triangle */
#define G_HOUSE 127

static void put(mode1_4bpp_data_t *cell, uint8_t ch, uint8_t fg, uint8_t bg)
{
    cell->glyph_code = ch;
    cell->bg_fg_index = (uint8_t)((bg << 4) | (fg & 0x0F));
}

void hud_clear(void)
{
    for (uint8_t r = 0; r < HUD_ROWS; r++)
        for (uint8_t c = 0; c < HUD_COLS; c++)
            put(&hud_grid[r][c], ' ', C_WHITE, C_PANEL);
    hud_dirty = true;
}

void hud_text(uint8_t col, uint8_t row, const char *str, uint8_t fg)
{
    while (*str && col < HUD_COLS)
        put(&hud_grid[row][col++], (uint8_t)*str++, fg, C_PANEL);
    hud_dirty = true;
}

static void digits(char *buf, uint32_t val, uint8_t width)
{
    buf[width] = '\0';
    for (int8_t i = width - 1; i >= 0; i--) {
        buf[i] = '0' + (val % 10);
        val /= 10;
    }
}

void hud_num(uint8_t col, uint8_t row, uint32_t val, uint8_t width, uint8_t fg)
{
    char buf[11];
    digits(buf, val, width);
    hud_text(col, row, buf, fg);
}

static void config(uint16_t addr, int16_t y, int16_t w, int16_t h, uint16_t data)
{
    mode1_config_t cfg = {
        .x_wrap = false,
        .y_wrap = false,
        .x_pos_px = 0,
        .y_pos_px = y,
        .width_chars = w,
        .height_chars = h,
        .xram_data_ptr = data,
        .xram_palette_ptr = PAL_ADDR(PAL_HUD),
        .xram_font_ptr = 0xFFFF, /* the built-in CP437 font */
    };
    xram0_write(addr, &cfg, sizeof(cfg));
}

void hud_init(void)
{
    hud_clear();
    msg_clear();
    hud_commit();
    config(XRAM_HUD_CONFIG, 0, HUD_COLS, HUD_ROWS, XRAM_HUD);
    config(XRAM_MSG_CONFIG, MSG_Y, MSG_COLS, MSG_ROWS, XRAM_MSG);
    xreg_vga_mode1(MODE1_4BPP | MODE1_8X8, XRAM_HUD_CONFIG, 2, 0, HUD_H);
    xreg_vga_mode1(MODE1_4BPP | MODE1_8X8, XRAM_MSG_CONFIG, 2, MSG_Y, MSG_Y + MSG_ROWS * 8);
}

/*
 * Row 0: SCORE 000000  SAVED 00/64  LOST 00  ^^^
 * Row 1: CARGO ################  [radar.........]
 */
#define RADAR_COL 23
#define RADAR_N 17

void hud_update(void)
{
    hud_text(0, 0, "SCORE", C_GOLD);
    hud_num(6, 0, score, 6, C_WHITE);
    hud_text(13, 0, "SAVED", C_LGREEN);
    hud_num(19, 0, saved_count, 2, C_WHITE);
    hud_text(21, 0, "/64", C_DIM);
    hud_text(25, 0, "LOST", C_RED);
    hud_num(30, 0, lost_count, 2, lost_count ? C_RED : C_WHITE);
    /* Spare choppers, as up arrows. */
    for (uint8_t i = 0; i < 6; i++)
        put(&hud_grid[0][34 + i], i < lives ? G_UP : ' ', C_CYAN, C_PANEL);

    hud_text(0, 1, "CARGO", C_CYAN);
    for (uint8_t i = 0; i < MAX_CARGO; i++) {
        uint8_t fg = i < cargo_count ? (cargo_count == MAX_CARGO ? C_ORANGE : C_WHITE) : C_FRAME;
        put(&hud_grid[1][6 + i], i < cargo_count ? G_BOX : G_DOT, fg, C_PANEL);
    }

    /* Radar: the world squeezed into RADAR_N cells. */
    put(&hud_grid[1][RADAR_COL - 1], '[', C_FRAME, C_PANEL);
    put(&hud_grid[1][RADAR_COL + RADAR_N], ']', C_FRAME, C_PANEL);
    for (uint8_t i = 0; i < RADAR_N; i++)
        put(&hud_grid[1][RADAR_COL + i], G_DOT, C_FRAME, C_PANEL);
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        uint8_t cell = (uint8_t)((uint16_t)(DOOR_X(i) >> 4) * RADAR_N / (WORLD_W_PX >> 4));
        uint8_t fg = !compounds[i].breached ? C_RED : (compounds[i].hostages_remaining ? C_ORANGE : C_DIM);
        put(&hud_grid[1][RADAR_COL + cell], G_BOX, fg, C_PANEL);
    }
    /* Hostages out in the snow. */
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        if (hostages[i].state == H_INACTIVE)
            continue;
        uint8_t cell = (uint8_t)((uint16_t)(FROM_SUB(hostages[i].world_x) >> 4) * RADAR_N / (WORLD_W_PX >> 4));
        put(&hud_grid[1][RADAR_COL + cell], '*', C_ORANGE, C_PANEL);
    }
    put(&hud_grid[1][RADAR_COL + RADAR_N - 1], G_HOUSE, C_LGREEN, C_PANEL);
    {
        int16_t x = FROM_SUB(chopper_world_x) + CHOPPER_W / 2;
        uint8_t cell = (uint8_t)((uint16_t)(x >> 4) * RADAR_N / (WORLD_W_PX >> 4));
        if (cell >= RADAR_N)
            cell = RADAR_N - 1;
        put(&hud_grid[1][RADAR_COL + cell], G_UP, (frame_count & 16) ? C_WHITE : C_AURORA, C_PANEL);
    }
    hud_dirty = true;
}

void hud_commit(void)
{
    if (hud_dirty) {
        xram0_write(XRAM_HUD, hud_grid, sizeof(hud_grid));
        hud_dirty = false;
    }
    if (msg_dirty) {
        xram0_write(XRAM_MSG, msg_grid, sizeof(msg_grid));
        msg_dirty = false;
    }
}

void msg_clear(void)
{
    memset(msg_grid, 0, sizeof(msg_grid));
    for (uint8_t r = 0; r < MSG_ROWS; r++)
        for (uint8_t c = 0; c < MSG_COLS; c++)
            msg_grid[r][c].glyph_code = ' ';
    flash_timer = 0;
    msg_dirty = true;
}

void msg_text(uint8_t col, uint8_t row, const char *str, uint8_t fg)
{
    while (*str && col < MSG_COLS)
        put(&msg_grid[row][col++], (uint8_t)*str++, fg, 0);
    msg_dirty = true;
}

void msg_center(uint8_t row, const char *str, uint8_t fg)
{
    uint8_t n = (uint8_t)strlen(str);
    for (uint8_t c = 0; c < MSG_COLS; c++)
        put(&msg_grid[row][c], ' ', fg, 0);
    msg_text((uint8_t)((MSG_COLS - n) / 2), row, str, fg);
}

void msg_band(uint8_t row, const char *str, uint8_t fg)
{
    uint8_t n = (uint8_t)strlen(str);
    uint8_t c0 = (uint8_t)((MSG_COLS - n) / 2);
    for (uint8_t c = 0; c < MSG_COLS; c++)
        put(&msg_grid[row][c], ' ', fg, C_PANEL);
    for (uint8_t c = 0; c < n; c++)
        put(&msg_grid[row][c0 + c], (uint8_t)str[c], fg, C_PANEL);
    msg_dirty = true;
}

void msg_num(uint8_t col, uint8_t row, uint32_t val, uint8_t width, uint8_t fg)
{
    char buf[11];
    digits(buf, val, width);
    msg_text(col, row, buf, fg);
}

void msg_flash(const char *str, uint8_t fg, uint8_t frames)
{
    msg_clear();
    msg_center(1, str, fg);
    flash_timer = frames;
}

void msg_tick(void)
{
    if (flash_timer && --flash_timer == 0)
        msg_clear();
}
