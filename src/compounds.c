#include <rp6502.h>
#include "bg.h"
#include "compounds.h"
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

compound_t compounds[NUM_COMPOUNDS];

void compounds_init(void)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        compounds[i].breached = false;
        compounds[i].hostages_remaining = HOSTAGES_PER_COMPOUND;
        compounds[i].spawn_timer = 45;
    }
    bg_reset_doors();
}

uint8_t compounds_freed(void)
{
    uint8_t n = 0;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
        n += HOSTAGES_PER_COMPOUND - compounds[i].hostages_remaining;
    return n;
}

void compounds_update(void)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        compound_t *c = &compounds[i];
        if (!c->breached || !c->hostages_remaining)
            continue;
        if (c->spawn_timer) {
            c->spawn_timer--;
            continue;
        }
        /* One every 45 frames, once the doorway is clear. */
        if (hostages_spawn(i, DOOR_X(i) + DOOR_W * 8)) {
            c->hostages_remaining--;
            c->spawn_timer = 45;
        }
    }
}

static void breach(uint8_t i)
{
    compounds[i].breached = true;
    compounds[i].spawn_timer = 45;
    bg_breach_door(i);
    explosion_spawn(DOOR_X(i) + DOOR_W * 8, DOOR_TOP + 14, true);
    small_explosion_spawn(DOOR_X(i) + 4, DOOR_TOP + 8);
    small_explosion_spawn(DOOR_X(i) + 28, DOOR_TOP + 20);
    sfx_enemy(SFX_BIG_EXPLODE, SFX_PRI_TOP);
    add_score(500);
    msg_flash("PRISON BREACHED! LAND TO PICK THEM UP", C_ORANGE, 150);
}

bool compounds_check_hit(int16_t x, int16_t y, bool bomb)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        if (x < BUNKER_X0(i) - 2 || x >= BUNKER_X1(i) + 2 || y < BUNKER_TOP)
            continue;
        int16_t dx = x - DOOR_X(i);
        bool on_door = dx >= -4 && dx < DOOR_W * 16 + 4 && y >= DOOR_TOP - 4;
        /* A bomb anywhere on the roof over the door also blows it. */
        bool roof_bomb = bomb && dx >= -16 && dx < DOOR_W * 16 + 16;
        if (!compounds[i].breached && (on_door || roof_bomb)) {
            breach(i);
            return true;
        }
        /* Bullets fly past the front wall; a bomb bursts on the roof. */
        return bomb;
    }
    return false;
}

void compounds_render(void)
{
    uint16_t img = XRAM_IMG_TARGET + ((frame_count >> 3) & 1) * TARGET_FRAME_BYTES;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        if (compounds[i].breached)
            spr_hide(SPR_TARGET_START + i);
        else
            spr_place(SPR_TARGET_START + i, img, PAL_TARGET, WH(16, 16), OPT4, screen_x(DOOR_X(i) + 8),
                      DOOR_TOP + 8);
    }
}
