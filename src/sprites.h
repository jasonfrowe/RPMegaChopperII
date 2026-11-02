#ifndef SPRITES_H
#define SPRITES_H

#include <stdint.h>
#include "xram.h"

extern mode5_csprite_t spr[SPR_TOTAL_COUNT];

#define WH(w, h) MODE5_SIZE(w, h)
#define OPT4 MODE5_4BPP
#define OPT4_FLIP (MODE5_4BPP | MODE5_HFLIP)
#define SPR_HIDDEN_Y (-64)

void spr_init(void);
void spr_hide_all(void);
void spr_commit(void);
/* Show sprite idx at screen (x, y), or hide it if it is off screen. */
void spr_place(uint8_t idx, uint16_t img, uint8_t pal, uint8_t wh, uint8_t opt, int16_t x, int16_t y);

static inline void spr_hide(uint8_t idx)
{
    spr[idx].y_pos_px = SPR_HIDDEN_Y;
}

#endif /* SPRITES_H */
