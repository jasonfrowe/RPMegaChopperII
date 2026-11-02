#include <string.h>
#include "game.h"
#include "sprites.h"
#include "xram.h"

mode5_csprite_t spr[SPR_TOTAL_COUNT];

void spr_hide_all(void)
{
    for (uint8_t i = 0; i < SPR_TOTAL_COUNT; i++) {
        spr[i].x_pos_px = 0;
        spr[i].y_pos_px = SPR_HIDDEN_Y;
        spr[i].xram_sprite_ptr = XRAM_IMG_SNOW;
        spr[i].palette_ptr = PAL_ADDR(PAL_SNOW);
        spr[i].width_height = WH(4, 4);
        spr[i].options = OPT4;
    }
}

void spr_init(void)
{
    spr_hide_all();
    spr_commit();
    /* Everything moving is on plane 2, over the ground, under the HUD. */
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_SPR, SPR_TOTAL_COUNT, 2, HUD_H, SCREEN_H);
}

void spr_commit(void)
{
    xram0_write(XRAM_SPR, spr, sizeof(spr));
}

void spr_place(uint8_t idx, uint16_t img, uint8_t pal, uint8_t wh, uint8_t opt, int16_t x, int16_t y)
{
    mode5_csprite_t *s = &spr[idx];
    if (x <= -64 || x >= SCREEN_W || y >= SCREEN_H) {
        s->y_pos_px = SPR_HIDDEN_Y;
        return;
    }
    s->x_pos_px = x;
    s->y_pos_px = y;
    s->xram_sprite_ptr = img;
    s->palette_ptr = PAL_ADDR(pal);
    s->width_height = wh;
    s->options = opt;
}
