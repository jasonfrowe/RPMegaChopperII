#include <rp6502.h>
#include <stdlib.h>
#include "game.h"
#include "hostages.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

hostage_t hostages[MAX_ACTIVE_HOSTAGES];

static uint8_t disembark_timer = 0;

void hostages_init(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostages[i].state = H_INACTIVE;
    }
    disembark_timer = 0;
}

bool hostages_spawn(int16_t x, int16_t y)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        if (hostages[i].state == H_INACTIVE) {
            hostages[i].state = H_WAVING;
            hostages[i].world_x = TO_SUB(x);
            hostages[i].y = y;
            hostages[i].dir = 1;
            hostages[i].anim_frame = 3;
            hostages[i].timer = 0;
            return true;
        }
    }
    return false;
}

void hostages_disembark_all(void)
{
    /* Triggered when chopper lands at Home Base */
    if (cargo_count > 0 && disembark_timer == 0) {
        disembark_timer = 15; /* Disembark rate */
        int16_t chop_x = FROM_SUB(chopper_world_x) + 16;
        for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
            if (hostages[i].state == H_INACTIVE) {
                hostages[i].state = H_RUN_TO_BASE;
                hostages[i].world_x = TO_SUB(chop_x);
                hostages[i].y = 188;
                hostages[i].dir = 1;
                hostages[i].anim_frame = 0;
                hostages[i].timer = 0;
                cargo_count--;
                sfx_player(SFX_HOSTAGE_BOARD, SFX_PRI_FIRE);
                break;
            }
        }
    }
}

void hostages_update(void)
{
    if (disembark_timer > 0)
        disembark_timer--;

    /* If chopper is landed at Home Base, unload passengers */
    if (chopper_is_landed) {
        int16_t chop_px = FROM_SUB(chopper_world_x);
        if (chop_px >= HOME_PAD_MIN_X && chop_px <= HOME_PAD_MAX_X) {
            hostages_disembark_all();
        }
    }

    int32_t chop_sub_x = chopper_world_x + TO_SUB(8);

    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        if (hostages[i].state == H_INACTIVE)
            continue;

        hostages[i].timer++;

        if (hostages[i].state == H_RUN_TO_BASE) {
            /* Running right toward Canadian medical tent (~3980 px) */
            hostages[i].world_x += TO_SUB(1);
            hostages[i].dir = 1;
            hostages[i].anim_frame = (hostages[i].timer >> 2) % 3; // frames 0..2

            if (FROM_SUB(hostages[i].world_x) >= 3980) {
                /* Safely arrived inside medical tents! */
                hostages[i].state = H_INACTIVE;
                saved_count++;
                add_score(1000);
                sfx_player(SFX_HOSTAGE_SAVED, SFX_PRI_EVENT);
            }
            continue;
        }

        /* Check interaction with Chopper */
        int32_t dist_to_chop = chop_sub_x - hostages[i].world_x;
        int16_t abs_dist = FROM_SUB(labs(dist_to_chop));

        if (chopper_is_landed && cargo_count < MAX_CARGO && abs_dist < 200) {
            hostages[i].state = H_RUN_TO_CHOPPER;
        } else if (hostages[i].state == H_RUN_TO_CHOPPER && (!chopper_is_landed || cargo_count >= MAX_CARGO)) {
            hostages[i].state = H_WAVING;
        }

        if (hostages[i].state == H_RUN_TO_CHOPPER) {
            if (dist_to_chop > TO_SUB(4)) {
                hostages[i].world_x += TO_SUB(1);
                hostages[i].dir = 1;
                hostages[i].anim_frame = (hostages[i].timer >> 2) % 3; // frames 0..2
            } else if (dist_to_chop < -TO_SUB(4)) {
                hostages[i].world_x -= TO_SUB(1);
                hostages[i].dir = -1;
                hostages[i].anim_frame = 6 + ((hostages[i].timer >> 2) % 3); // frames 6..8
            } else {
                /* Reached chopper door: board! */
                hostages[i].state = H_BOARDING;
                hostages[i].anim_frame = 9;
            }
        } else if (hostages[i].state == H_BOARDING) {
            if (cargo_count < MAX_CARGO) {
                cargo_count++;
                sfx_player(SFX_HOSTAGE_BOARD, SFX_PRI_EVENT);
                add_score(100);
            }
            hostages[i].state = H_INACTIVE;
        } else if (hostages[i].state == H_WAVING) {
            /* Jumping and waving arms */
            hostages[i].anim_frame = 3 + ((hostages[i].timer >> 3) % 3); // frames 3..5
            if ((hostages[i].timer & 0x7F) == 0 && ((rng_next() & 3) == 0)) {
                sfx_enemy(SFX_HOSTAGE_WAVE, SFX_PRI_FIRE);
            }
        }
    }
}

bool hostages_check_hit(int16_t hit_x, int16_t hit_y)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        if (hostages[i].state != H_INACTIVE && hostages[i].state != H_DEAD) {
            int16_t hx = FROM_SUB(hostages[i].world_x);
            int16_t hy = hostages[i].y;
            if (abs(hit_x - hx) < 8 && abs(hit_y - hy) < 12) {
                hostages[i].state = H_DEAD;
                lost_count++;
                sfx_enemy(SFX_HOSTAGE_DIE, SFX_PRI_TOP);

                int16_t scr_x = hx - FROM_SUB(camera_x);
                small_explosion_spawn(scr_x, hy);

                if (saved_count + lost_count >= TOTAL_HOSTAGES) {
                    gstate = GS_LEVEL_CLEAR;
                }
                return true;
            }
        }
    }
    return false;
}

void hostages_render(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        uint8_t spr_idx = SPR_HOSTAGE_START + i;
        if (hostages[i].state != H_INACTIVE && hostages[i].state != H_DEAD) {
            int16_t screen_x = FROM_SUB(hostages[i].world_x - camera_x);
            int16_t screen_y = hostages[i].y;
            if (screen_x > -16 && screen_x < SCREEN_W) {
                uint16_t img_addr = XRAM_IMG_HOSTAGES + (uint16_t)hostages[i].anim_frame * HOSTAGES_FRAME_BYTES;
                spr_setup(spr_idx, img_addr, PAL_ADDR(PAL_HOSTAGES), WH(16, 16), OPT4);
                spr_pos(spr_idx, screen_x, screen_y);
            } else {
                spr_hide(spr_idx);
            }
        } else {
            spr_hide(spr_idx);
        }
    }
}
