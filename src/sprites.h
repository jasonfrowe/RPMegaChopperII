#ifndef SPRITES_H
#define SPRITES_H

#include <stdint.h>
#include "xram.h"

extern mode5_csprite_t spr[SPR_TOTAL_COUNT];

#define WH(w, h) MODE5_SIZE(w, h)
#define OPT4 MODE5_4BPP
#define SPR_HIDDEN_Y (-32)

void spr_init(void);
void spr_hide_all(void);
void spr_commit(void);

static inline void spr_hide(uint8_t idx)
{
    spr[idx].y_pos_px = SPR_HIDDEN_Y;
}

static inline void spr_setup(uint8_t idx, uint16_t img, uint16_t pal, uint8_t wh, uint8_t opt)
{
    spr[idx].xram_sprite_ptr = img;
    spr[idx].palette_ptr = pal;
    spr[idx].width_height = wh;
    spr[idx].options = opt;
}

static inline void spr_pos(uint8_t idx, int16_t x, int16_t y)
{
    spr[idx].x_pos_px = x;
    spr[idx].y_pos_px = y;
}

#endif /* SPRITES_H */
