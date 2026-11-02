#include <rp6502.h>
#include <stdlib.h>
#include "compounds.h"
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "input.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

/* The rules are the original game's: see docs/ORIGINAL_GAMEPLAY.md. */

hostage_t hostages[MAX_ACTIVE_HOSTAGES];

#define RUN_SPEED 8          /* subpixels per frame: half a pixel */
#define SIGHT_RANGE 150      /* px: how far off they see a low chopper */
#define SIGHT_HEIGHT 64      /* px above landed height: "low" */
#define ARRIVE 8             /* px: close enough to where it was going */
#define BOARD_RANGE 12       /* px from the chopper's middle */
#define SPACING 12           /* px: never closer than this behind the one ahead */
#define DOOR_CLEAR 8         /* px: the next one waits until the doorway is this clear */
#define CRUSH_HEIGHT 14      /* px above landed height */
#define CRUSH_FRONT 8        /* px either side of the middle, facing the screen */
#define CRUSH_SIDE 15        /* px, facing sideways */
#define UNLOAD_EVERY 30      /* frames */
#define WAVE_TIME 120        /* frames the last one waves at the door */

/* Frames in hostages.png */
#define HF_RUN 0 /* 0-3 */
#define HF_WAVE 4 /* 4-5 */

static uint8_t unload_timer;

void hostages_init(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++)
        hostages[i].state = H_INACTIVE;
    unload_timer = 0;
}

static hostage_t *free_slot(void)
{
    uint8_t out = 0;
    hostage_t *slot = 0;
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        if (hostages[i].state == H_INACTIVE) {
            if (!slot)
                slot = &hostages[i];
        } else {
            out++;
        }
    }
    return out + cargo_count < MAX_ACTIVE_HOSTAGES ? slot : 0;
}

/* Where each one waits outside the prison, by the order it came out
 * (0-15): alternately either side of the door, SPACING apart, the first
 * ones furthest out. Each newcomer stops short of those already standing,
 * so nobody has to get past anybody, and the doorway stays clear. (The
 * original had four spots, and its hostages bunched at the door.) */
static int16_t wait_spot(uint8_t home, uint8_t n)
{
    int16_t off = 20 + SPACING * (7 - (n >> 1));
    return DOOR_X(home) + DOOR_W * 8 + ((n & 1) ? off : -off);
}

bool hostages_spawn(uint8_t home, int16_t x)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++)
        if (hostages[i].state != H_INACTIVE && abs(FROM_SUB(hostages[i].world_x) + 8 - x) < DOOR_CLEAR)
            return false;
    hostage_t *h = free_slot();
    if (!h)
        return false;
    h->state = H_OUT;
    h->world_x = TO_SUB(x - 8);
    h->home = home;
    h->spot = HOSTAGES_PER_COMPOUND - compounds[home].hostages_remaining;
    h->anim = 0;
    h->timer = 0;
    h->move = 0;
    h->left = false;
    return true;
}

static void kill(hostage_t *h)
{
    small_explosion_spawn(FROM_SUB(h->world_x) + 8, HOSTAGE_Y + 8);
    h->state = H_INACTIVE;
    lost_count++;
    sfx_enemy(SFX_HOSTAGE_DIE, SFX_PRI_TOP);
}

bool hostages_check_hit(int16_t x, int16_t y)
{
    if (abs(y - (HOSTAGE_Y + 8)) >= 7)
        return false;
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostage_t *h = &hostages[i];
        if (h->state != H_INACTIVE && abs(x - (FROM_SUB(h->world_x) + 8)) < 5) {
            kill(h);
            return true;
        }
    }
    return false;
}

static void saved(hostage_t *h)
{
    h->state = H_INACTIVE;
    saved_count++;
    add_score(250);
    sfx_enemy(SFX_HOSTAGE_SAVED, SFX_PRI_EVENT);
}

/* Is someone within SPACING ahead of h, going its way or standing? Then h
 * waits, and they line up. The one waving at the door doesn't count, and
 * neither does one walking straight at h, or the two would stop face to
 * face for good. */
static bool blocked(hostage_t *h, int8_t dir)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostage_t *o = &hostages[i];
        if (o == h || o->state == H_INACTIVE || o->state == H_WAVE || o->move == -dir)
            continue;
        int16_t sep = FROM_SUB(o->world_x - h->world_x);
        if (dir > 0 ? (sep > 0 && sep < SPACING) : (sep < 0 && sep > -SPACING))
            return true;
    }
    return false;
}

/* Step toward target; true once within ARRIVE of it. */
static bool walk(hostage_t *h, int16_t target)
{
    int16_t d = target - (FROM_SUB(h->world_x) + 8);
    h->move = 0;
    if (abs(d) <= ARRIVE)
        return true;
    int8_t dir = d > 0 ? 1 : -1;
    h->left = dir < 0;
    if (!blocked(h, dir)) {
        h->move = dir;
        h->world_x += dir * RUN_SPEED;
    }
    return false;
}

void hostages_update(void)
{
    int16_t cx = FROM_SUB(chopper_world_x);
    int16_t ccx = chopper_cx();
    bool landed = player_status == PL_LANDED;
    bool low = player_alive() && chopper_y >= GROUND_Y_SUB - TO_SUB(SIGHT_HEIGHT);
    bool at_home = landed && cx >= HOME_PAD_MIN_X && cx <= HOME_PAD_MAX_X;
    bool crushing = player_alive() && !landed && chopper_y > GROUND_Y_SUB - TO_SUB(CRUSH_HEIGHT) &&
                    !(in_held & IN_UP);
    uint8_t crush = chopper_heading == FACING_FRONT ? CRUSH_FRONT : CRUSH_SIDE;

    /* Let passengers off at home, one every UNLOAD_EVERY frames. The last
     * one off waves at the door before going in. */
    if (at_home && cargo_count) {
        if (++unload_timer > UNLOAD_EVERY) {
            unload_timer = 0;
            for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
                hostage_t *h = &hostages[i];
                if (h->state != H_INACTIVE)
                    continue;
                cargo_count--;
                h->state = H_TO_BASE;
                h->world_x = TO_SUB(ccx - 8);
                h->spot = cargo_count == 0; /* 1: the last one */
                h->anim = 0;
                h->timer = 0;
                h->move = 0;
                sfx_player(SFX_HOSTAGE_BOARD, SFX_PRI_EVENT);
                break;
            }
        }
    } else {
        unload_timer = 0;
    }

    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostage_t *h = &hostages[i];
        if (h->state == H_INACTIVE)
            continue;
        int16_t hx = FROM_SUB(h->world_x) + 8;

        if (crushing && abs(hx - ccx) < crush) {
            kill(h);
            msg_flash("CAREFUL! YOU LANDED ON A HOSTAGE", C_RED, 120);
            continue;
        }

        switch (h->state) {
        case H_OUT:
            if (low && abs(hx - ccx) < SIGHT_RANGE) {
                /* Run for the chopper; climb aboard once it is down. */
                if (walk(h, ccx) && landed && abs(hx - ccx) < BOARD_RANGE && cargo_count < MAX_CARGO) {
                    h->state = H_INACTIVE;
                    cargo_count++;
                    sfx_player(SFX_HOSTAGE_BOARD, SFX_PRI_EVENT);
                    if (cargo_count == MAX_CARGO)
                        msg_flash("CARGO FULL! FLY THEM HOME", C_GOLD, 150);
                }
            } else {
                walk(h, wait_spot(h->home, h->spot));
            }
            break;

        case H_TO_BASE:
            if (walk(h, HOME_DOOR_X)) {
                if (h->spot) {
                    h->state = H_WAVE;
                    h->timer = 0;
                } else {
                    saved(h);
                }
            }
            break;

        case H_WAVE:
            if (++h->timer >= WAVE_TIME)
                saved(h);
            break;

        default:
            break;
        }

        /* Running frames while walking, waving frames while standing. */
        if (h->state == H_WAVE) {
            h->anim = (h->timer / 10) & 1;
        } else if (++h->timer > 6) {
            h->timer = 0;
            h->anim = h->move ? (h->anim + 1) & 3 : !h->anim;
        }
    }
}

void hostages_render(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostage_t *h = &hostages[i];
        uint8_t idx = SPR_HOSTAGE_START + i;
        if (h->state == H_INACTIVE) {
            spr_hide(idx);
            continue;
        }
        uint8_t f = h->move ? HF_RUN + h->anim : HF_WAVE + (h->anim & 1);
        spr_place(idx, XRAM_IMG_HOSTAGES + f * HOSTAGES_FRAME_BYTES, PAL_HOSTAGE, WH(16, 16),
                  h->left ? OPT4 : OPT4_FLIP, FROM_SUB(h->world_x - camera_x), HOSTAGE_Y);
    }
}
