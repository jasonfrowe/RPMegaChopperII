#include <rp6502.h>
#include "bg.h"
#include "compounds.h"
#include "game.h"
#include "hostages.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

compound_t compounds[NUM_COMPOUNDS];

static const uint8_t compound_cols[NUM_COMPOUNDS] = {185, 135, 80, 30};

void compounds_init(void)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        compounds[i].col = compound_cols[i];
        compounds[i].door_x = (int16_t)(compound_cols[i] + 5) * 16;
        compounds[i].door_y = 180;
        compounds[i].breached = false;
        compounds[i].hostages_remaining = 16;
        compounds[i].spawn_timer = 20;
    }
}

void compounds_update(void)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        if (compounds[i].breached && compounds[i].hostages_remaining > 0) {
            if (--compounds[i].spawn_timer == 0) {
                compounds[i].spawn_timer = 45; /* Spawn a hostage every 45 frames */
                if (hostages_spawn(compounds[i].door_x + 8, compounds[i].door_y)) {
                    compounds[i].hostages_remaining--;
                }
            }
        }
    }
}

bool compounds_check_hit(int16_t hit_x, int16_t hit_y)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        if (!compounds[i].breached) {
            int16_t dx = hit_x - compounds[i].door_x;
            int16_t dy = hit_y - compounds[i].door_y;
            /* Target hitbox: 32x24 px */
            if (dx >= -4 && dx <= 32 && dy >= -8 && dy <= 24) {
                compounds[i].breached = true;
                bg_breach_bunker(compounds[i].col);
                sfx_enemy(SFX_BIG_EXPLODE, SFX_PRI_TOP);

                int16_t scr_x = compounds[i].door_x - FROM_SUB(camera_x);
                explosion_spawn(scr_x, compounds[i].door_y - 8, true);

                add_score(500);
                return true;
            }
        }
    }
    return false;
}

void compounds_render(void)
{
    uint8_t anim = (frame_count >> 3) & 1;
    uint16_t img_addr = XRAM_IMG_TARGET + (uint16_t)anim * TARGET_FRAME_BYTES;

    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        uint8_t spr_idx = SPR_TARGET_START + i;
        if (!compounds[i].breached) {
            int16_t screen_x = compounds[i].door_x - FROM_SUB(camera_x);
            int16_t screen_y = compounds[i].door_y - 4;
            if (screen_x > -16 && screen_x < SCREEN_W) {
                spr_setup(spr_idx, img_addr, PAL_ADDR(PAL_TARGET), WH(16, 16), OPT4);
                spr_pos(spr_idx, screen_x, screen_y);
            } else {
                spr_hide(spr_idx);
            }
        } else {
            spr_hide(spr_idx);
        }
    }
}
