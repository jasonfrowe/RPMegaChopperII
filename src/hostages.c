#include <rp6502.h>
#include <stdlib.h>
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

hostage_t hostages[MAX_ACTIVE_HOSTAGES];

#define RUN_SPEED 13          /* subpixels per frame */
#define SIGHT_RANGE 150       /* px: how far away they notice a landed chopper */
#define BOARD_RANGE 6         /* px from the chopper's middle */
#define UNLOAD_EVERY 16       /* frames between hostages getting off */

/* Frames in hostages.png */
#define HF_RUN 0 /* 0-3 */
#define HF_WAVE 4 /* 4-5 */
#define HF_STAND 6

static uint8_t unload_timer;

void hostages_init(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++)
        hostages[i].state = H_INACTIVE;
    unload_timer = 0;
}

static hostage_t *free_slot(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++)
        if (hostages[i].state == H_INACTIVE)
            return &hostages[i];
    return 0;
}

/* Somewhere to stand near the prison, spread out so they don't pile up. */
static int16_t wait_spot(uint8_t home, uint8_t n)
{
    static const int8_t spots[8] = {-40, 52, -24, 36, -56, 68, -8, 20};
    return DOOR_X(home) + DOOR_W * 8 + spots[n & 7];
}

bool hostages_spawn(uint8_t home, int16_t x)
{
    /* Wait until the doorway is clear. */
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++)
        if (hostages[i].state != H_INACTIVE && abs(FROM_SUB(hostages[i].world_x) + 8 - x) < 10)
            return false;
    hostage_t *h = free_slot();
    if (!h)
        return false;
    h->state = H_WAIT;
    h->world_x = TO_SUB(x - 8);
    h->home = home;
    h->target = wait_spot(home, (uint8_t)rng_next());
    h->anim = 0;
    h->timer = 0;
    h->left = false;
    return true;
}

static void kill(hostage_t *h)
{
    h->state = H_INACTIVE;
    lost_count++;
    sfx_enemy(SFX_HOSTAGE_DIE, SFX_PRI_TOP);
}

bool hostages_check_hit(int16_t x, int16_t y)
{
    if (y < HOSTAGE_Y)
        return false;
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostage_t *h = &hostages[i];
        if (h->state == H_INACTIVE || h->state == H_CHEER)
            continue;
        if (abs(x - (FROM_SUB(h->world_x) + 8)) < 5) {
            small_explosion_spawn(FROM_SUB(h->world_x) + 8, HOSTAGE_Y + 6);
            kill(h);
            return true;
        }
    }
    return false;
}

void hostages_scatter(void)
{
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++)
        if (hostages[i].state == H_TO_CHOPPER)
            hostages[i].state = H_WAIT;
}

/* Step toward target; true when there. */
static bool run_to(hostage_t *h, int16_t target)
{
    int16_t cx = FROM_SUB(h->world_x) + 8;
    int16_t d = target - cx;
    if (d > 2) {
        h->world_x += RUN_SPEED;
        h->left = false;
    } else if (d < -2) {
        h->world_x -= RUN_SPEED;
        h->left = true;
    } else {
        return true;
    }
    if (++h->timer >= 5) {
        h->timer = 0;
        h->anim = (h->anim + 1) & 3;
    }
    return false;
}

void hostages_update(void)
{
    bool landed = chopper_is_landed && player_status == PL_LANDED;
    int16_t ccx = chopper_cx();
    bool at_home = landed && FROM_SUB(chopper_world_x) >= HOME_PAD_MIN_X && FROM_SUB(chopper_world_x) <= HOME_PAD_MAX_X;
    /* Coming in low over them, skids first: they get crushed. */
    bool crushing = player_alive() && !chopper_is_landed && chopper_y > GROUND_Y_SUB - TO_SUB(8) && chopper_vel_y > 0;

    /* Drop off passengers at the home helipad, one at a time. */
    if (at_home && cargo_count) {
        if (++unload_timer >= UNLOAD_EVERY) {
            hostage_t *h = free_slot();
            if (h) {
                unload_timer = 0;
                h->state = H_TO_BASE;
                h->world_x = TO_SUB(ccx - 8);
                h->target = HOME_DOOR_X;
                h->anim = 0;
                h->timer = 0;
                cargo_count--;
                sfx_player(SFX_HOSTAGE_BOARD, SFX_PRI_EVENT);
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

        if (crushing && h->state != H_CHEER && abs(hx - ccx) < 13) {
            small_explosion_spawn(hx, HOSTAGE_Y + 6);
            kill(h);
            msg_flash("CAREFUL! YOU LANDED ON A HOSTAGE", C_RED, 120);
            continue;
        }

        switch (h->state) {
        case H_WAIT:
            if (landed && !at_home && cargo_count < MAX_CARGO && abs(hx - ccx) < SIGHT_RANGE) {
                h->state = H_TO_CHOPPER;
                if ((rng_next() & 3) == 0)
                    sfx_enemy(SFX_HOSTAGE_WAVE, SFX_PRI_FIRE);
            } else if (run_to(h, h->target)) {
                /* Wave at the chopper when it flies over, otherwise stand. */
                h->anim = 0;
                h->timer++;
                if (h->timer > 90 && (rng_next() & 63) == 0) {
                    h->target = wait_spot(h->home, (uint8_t)rng_next());
                    h->timer = 0;
                }
            }
            break;

        case H_TO_CHOPPER:
            if (!landed || cargo_count >= MAX_CARGO) {
                h->state = H_WAIT;
                break;
            }
            if (abs(hx - ccx) <= BOARD_RANGE) {
                h->state = H_INACTIVE;
                cargo_count++;
                sfx_player(SFX_HOSTAGE_BOARD, SFX_PRI_EVENT);
                if (cargo_count == MAX_CARGO)
                    msg_flash("CARGO FULL! FLY THEM HOME", C_GOLD, 150);
                break;
            }
            run_to(h, ccx);
            break;

        case H_TO_BASE:
            if (run_to(h, h->target)) {
                h->state = H_CHEER;
                h->timer = 0;
            }
            break;

        case H_CHEER:
            if (++h->timer >= 30) {
                h->state = H_INACTIVE;
                saved_count++;
                add_score(250);
                sfx_enemy(SFX_HOSTAGE_SAVED, SFX_PRI_EVENT);
            }
            break;

        default:
            break;
        }
    }
}

void hostages_render(void)
{
    int16_t ccx = chopper_cx();
    for (uint8_t i = 0; i < MAX_ACTIVE_HOSTAGES; i++) {
        hostage_t *h = &hostages[i];
        uint8_t idx = SPR_HOSTAGE_START + i;
        if (h->state == H_INACTIVE) {
            spr_hide(idx);
            continue;
        }
        uint8_t f;
        bool moving = h->state == H_TO_CHOPPER || h->state == H_TO_BASE ||
                      (h->state == H_WAIT && abs(FROM_SUB(h->world_x) + 8 - h->target) > 2);
        if (h->state == H_CHEER)
            f = HF_WAVE + ((frame_count >> 3) & 1);
        else if (moving)
            f = HF_RUN + h->anim;
        else if (player_alive() && abs(FROM_SUB(h->world_x) + 8 - ccx) < 200)
            f = HF_WAVE + (((frame_count >> 3) + i) & 1); /* "over here!" */
        else
            f = HF_STAND;
        spr_place(idx, XRAM_IMG_HOSTAGES + f * HOSTAGES_FRAME_BYTES, PAL_HOSTAGE, WH(16, 16),
                  h->left ? OPT4 : OPT4_FLIP, FROM_SUB(h->world_x - camera_x), HOSTAGE_Y);
    }
}
