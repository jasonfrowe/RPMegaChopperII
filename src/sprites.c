#include <string.h>
#include "sprites.h"
#include "xram.h"

mode5_csprite_t spr[SPR_TOTAL_COUNT];

void spr_hide_all(void)
{
    for (uint8_t i = 0; i < SPR_TOTAL_COUNT; i++) {
        spr[i].x_pos_px = 0;
        spr[i].y_pos_px = SPR_HIDDEN_Y;
        spr[i].xram_sprite_ptr = XRAM_IMG_BULLET;
        spr[i].palette_ptr = PAL_ADDR(PAL_CHOPPER);
        spr[i].width_height = WH(8, 8);
        spr[i].options = OPT4;
    }
}

void spr_init(void)
{
    spr_hide_all();
    spr_commit();
    /* Register Mode 5 custom sprites on Plane 1, no screen wrap */
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_SPR, SPR_TOTAL_COUNT, 1, 0, 0);
}

void spr_commit(void)
{
    xram0_write(XRAM_SPR, spr, sizeof(spr));
}
