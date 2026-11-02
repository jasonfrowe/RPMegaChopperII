#include <rp6502.h>
#include "bg.h"
#include "game.h"
#include "xram.h"

static mode2_config_t bg_cfg;
static mode2_config_t fg_cfg;

void bg_init(void)
{
    /* Plane 0: Distant Northern Mountain Parallax */
    bg_cfg.x_wrap = true;
    bg_cfg.y_wrap = false;
    bg_cfg.x_pos_px = 0;
    bg_cfg.y_pos_px = 0;
    bg_cfg.width_tiles = WORLD_MAP_COLS;
    bg_cfg.height_tiles = WORLD_MAP_ROWS;
    bg_cfg.xram_data_ptr = XRAM_MAP_BG;
    bg_cfg.xram_palette_ptr = PAL_ADDR(PAL_BG);
    bg_cfg.xram_tile_ptr = XRAM_TILES_BG;

    /* Plane 1: Foreground Tundra Terrain & Fortified Bunkers */
    fg_cfg.x_wrap = true;
    fg_cfg.y_wrap = false;
    fg_cfg.x_pos_px = 0;
    fg_cfg.y_pos_px = 0;
    fg_cfg.width_tiles = WORLD_MAP_COLS;
    fg_cfg.height_tiles = WORLD_MAP_ROWS;
    fg_cfg.xram_data_ptr = XRAM_MAP_FG;
    fg_cfg.xram_palette_ptr = PAL_ADDR(PAL_FG);
    fg_cfg.xram_tile_ptr = XRAM_TILES_FG;

    xram0_write(XRAM_BG_CONFIG, &bg_cfg, sizeof(bg_cfg));
    xram0_write(XRAM_FG_CONFIG, &fg_cfg, sizeof(fg_cfg));

    /* Register Plane 0 and Plane 1 Mode 2 layers */
    xreg_vga_mode2(MODE2_4BPP | MODE2_16X16, XRAM_BG_CONFIG, 0, 0, 0);
    xreg_vga_mode2(MODE2_4BPP | MODE2_16X16, XRAM_FG_CONFIG, 1, 0, 0);
}

void bg_update(int16_t camera_x_px)
{
    /* Foreground scrolls 1:1 with camera */
    fg_cfg.x_pos_px = camera_x_px;

    /* Background mountains scroll with parallax (approx 3/8 speed) */
    bg_cfg.x_pos_px = (int16_t)(((int32_t)camera_x_px * 3) >> 3);
}

void bg_commit(void)
{
    /* Write updated scroll positions to XRAM */
    xram0_write(XRAM_BG_CONFIG, &bg_cfg, sizeof(bg_cfg));
    xram0_write(XRAM_FG_CONFIG, &fg_cfg, sizeof(fg_cfg));
}

void bg_breach_bunker(uint8_t base_col)
{
    /* Change the blast door tiles (cols base_col+5 and base_col+6, rows 11 & 12)
     * to breached rubble tile (tile 12) */
    uint8_t rubble = 12;
    for (uint8_t dc = 5; dc <= 6; dc++) {
        uint16_t addr_row11 = XRAM_MAP_FG + 11 * WORLD_MAP_COLS + (base_col + dc);
        uint16_t addr_row12 = XRAM_MAP_FG + 12 * WORLD_MAP_COLS + (base_col + dc);
        xram0_poke8(addr_row11, rubble);
        xram0_poke8(addr_row12, rubble);
    }
}

void bg_reset_bunkers(void)
{
    static const uint8_t compound_cols[4] = {185, 135, 80, 30};
    uint8_t intact_door = 11;
    for (uint8_t i = 0; i < 4; i++) {
        uint8_t base_col = compound_cols[i];
        for (uint8_t dc = 5; dc <= 6; dc++) {
            uint16_t addr_row11 = XRAM_MAP_FG + 11 * WORLD_MAP_COLS + (base_col + dc);
            uint16_t addr_row12 = XRAM_MAP_FG + 12 * WORLD_MAP_COLS + (base_col + dc);
            xram0_poke8(addr_row11, intact_door);
            xram0_poke8(addr_row12, intact_door);
        }
    }
}
