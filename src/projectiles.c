#include <rp6502.h>
#include <stdlib.h>
#include "compounds.h"
#include "enemies.h"
#include "game.h"
#include "hostages.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

typedef struct
{
    bool active;
    int32_t world_x; // Subpixels
    int32_t world_y; // Subpixels
    int16_t vx;
    int16_t vy;
} bullet_t;

typedef struct
{
    bool active;
    int32_t world_x;
    int32_t world_y;
    int16_t vx;
    int16_t vy;
    uint8_t anim;
} bomb_t;

typedef struct
{
    bool active;
    int16_t screen_x;
    int16_t screen_y;
    uint8_t frame;
    uint8_t timer;
    bool is_big;
} explosion_t;

static bullet_t bullets[SPR_BULLET_COUNT];
static bomb_t bombs[SPR_BOMB_COUNT];
static bullet_t ebullets[SPR_EBULLET_COUNT];
static explosion_t explosions[SPR_EXPLOSION_COUNT];
static explosion_t small_explosions[SPR_SMALLEXP_COUNT];

void projectiles_init(void)
{
    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) bullets[i].active = false;
    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) bombs[i].active = false;
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) ebullets[i].active = false;
    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) explosions[i].active = false;
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) small_explosions[i].active = false;
}

void bullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy)
{
    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) {
        if (!bullets[i].active) {
            bullets[i].active = true;
            bullets[i].world_x = TO_SUB(x);
            bullets[i].world_y = TO_SUB(y);
            bullets[i].vx = vx;
            bullets[i].vy = vy;
            break;
        }
    }
}

void bomb_spawn(int16_t x, int16_t y, int16_t vx)
{
    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) {
        if (!bombs[i].active) {
            bombs[i].active = true;
            bombs[i].world_x = TO_SUB(x);
            bombs[i].world_y = TO_SUB(y);
            bombs[i].vx = vx;
            bombs[i].vy = TO_SUB(1); // Downward velocity
            bombs[i].anim = 0;
            break;
        }
    }
}

void ebullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy)
{
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) {
        if (!ebullets[i].active) {
            ebullets[i].active = true;
            ebullets[i].world_x = TO_SUB(x);
            ebullets[i].world_y = TO_SUB(y);
            ebullets[i].vx = vx;
            ebullets[i].vy = vy;
            break;
        }
    }
}

void explosion_spawn(int16_t screen_x, int16_t screen_y, bool is_big)
{
    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) {
        if (!explosions[i].active) {
            explosions[i].active = true;
            explosions[i].screen_x = screen_x;
            explosions[i].screen_y = screen_y;
            explosions[i].frame = 0;
            explosions[i].timer = 0;
            explosions[i].is_big = is_big;
            sfx_enemy(SFX_EXPLODE, SFX_PRI_DESTROY);
            break;
        }
    }
}

void small_explosion_spawn(int16_t screen_x, int16_t screen_y)
{
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) {
        if (!small_explosions[i].active) {
            small_explosions[i].active = true;
            small_explosions[i].screen_x = screen_x;
            small_explosions[i].screen_y = screen_y;
            small_explosions[i].frame = 0;
            small_explosions[i].timer = 0;
            break;
        }
    }
}

void projectiles_update(void)
{
    /* Update Player Bullets */
    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) {
        if (!bullets[i].active) continue;

        bullets[i].world_x += bullets[i].vx;
        bullets[i].world_y += bullets[i].vy;

        int16_t wx = FROM_SUB(bullets[i].world_x);
        int16_t wy = FROM_SUB(bullets[i].world_y);
        int16_t sx = wx - FROM_SUB(camera_x);

        if (sx < -8 || sx > SCREEN_W + 8 || wy < CEILING_Y || wy >= GROUND_Y + 8) {
            bullets[i].active = false;
            continue;
        }

        if (compounds_check_hit(wx, wy) ||
            tanks_check_hit(wx, wy) ||
            balloons_check_hit(wx, wy) ||
            jets_check_hit(wx, wy)) {
            bullets[i].active = false;
            small_explosion_spawn(sx, wy);
        }
    }

    /* Update Bombs */
    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) {
        if (!bombs[i].active) continue;

        bombs[i].world_x += bombs[i].vx;
        bombs[i].vy += TO_SUB(1) / 5; // Gravity
        bombs[i].world_y += bombs[i].vy;

        int16_t wx = FROM_SUB(bombs[i].world_x);
        int16_t wy = FROM_SUB(bombs[i].world_y);
        int16_t sx = wx - FROM_SUB(camera_x);

        if (wy >= GROUND_Y) {
            bombs[i].active = false;
            explosion_spawn(sx - 12, GROUND_Y - 8, true);
            compounds_check_hit(wx, GROUND_Y);
            tanks_check_hit(wx, GROUND_Y);
            hostages_check_hit(wx, GROUND_Y);
            continue;
        }

        if (compounds_check_hit(wx, wy) || tanks_check_hit(wx, wy) || hostages_check_hit(wx, wy)) {
            bombs[i].active = false;
            explosion_spawn(sx - 12, wy - 8, true);
        }
    }

    /* Update Enemy Flak Bullets */
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) {
        if (!ebullets[i].active) continue;

        ebullets[i].world_x += ebullets[i].vx;
        ebullets[i].world_y += ebullets[i].vy;

        int16_t wx = FROM_SUB(ebullets[i].world_x);
        int16_t wy = FROM_SUB(ebullets[i].world_y);
        int16_t sx = wx - FROM_SUB(camera_x);

        if (sx < -8 || sx > SCREEN_W + 8 || wy < CEILING_Y || wy > GROUND_Y + 8) {
            ebullets[i].active = false;
            continue;
        }

        /* Check hit against player chopper */
        if (player_status == PL_ALIVE || player_status == PL_LANDED) {
            int16_t c_wx = FROM_SUB(chopper_world_x) + 16;
            int16_t c_wy = FROM_SUB(chopper_y) + 8;
            if (abs(wx - c_wx) < 16 && abs(wy - c_wy) < 10) {
                ebullets[i].active = false;
                player_kill();
                continue;
            }
        }

        /* Check hit against hostages */
        if (hostages_check_hit(wx, wy)) {
            ebullets[i].active = false;
        }
    }

    /* Update Explosions */
    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) {
        if (!explosions[i].active) continue;
        if (++explosions[i].timer >= 4) {
            explosions[i].timer = 0;
            if (++explosions[i].frame >= EXPLOSION_FRAMES) {
                explosions[i].active = false;
            }
        }
    }

    /* Update Small Explosions */
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) {
        if (!small_explosions[i].active) continue;
        if (++small_explosions[i].timer >= 3) {
            small_explosions[i].timer = 0;
            if (++small_explosions[i].frame >= SMALLEXPLOSION_FRAMES) {
                small_explosions[i].active = false;
            }
        }
    }
}

void projectiles_render(void)
{
    /* Render Bullets */
    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) {
        uint8_t s_idx = SPR_BULLET_START + i;
        if (bullets[i].active) {
            int16_t sx = FROM_SUB(bullets[i].world_x - camera_x);
            int16_t sy = FROM_SUB(bullets[i].world_y);
            spr_setup(s_idx, XRAM_IMG_BULLET, PAL_ADDR(PAL_CHOPPER), WH(8, 8), OPT4);
            spr_pos(s_idx, sx, sy);
        } else {
            spr_hide(s_idx);
        }
    }

    /* Render Bombs */
    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) {
        uint8_t s_idx = SPR_BOMB_START + i;
        if (bombs[i].active) {
            int16_t sx = FROM_SUB(bombs[i].world_x - camera_x);
            int16_t sy = FROM_SUB(bombs[i].world_y);
            uint8_t anim = (frame_count >> 2) & 1;
            uint16_t addr = XRAM_IMG_BOMB + (uint16_t)anim * BOMB_FRAME_BYTES;
            spr_setup(s_idx, addr, PAL_ADDR(PAL_TANK), WH(8, 8), OPT4);
            spr_pos(s_idx, sx, sy);
        } else {
            spr_hide(s_idx);
        }
    }

    /* Render Enemy Bullets */
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) {
        uint8_t s_idx = SPR_EBULLET_START + i;
        if (ebullets[i].active) {
            int16_t sx = FROM_SUB(ebullets[i].world_x - camera_x);
            int16_t sy = FROM_SUB(ebullets[i].world_y);
            spr_setup(s_idx, XRAM_IMG_BULLET, PAL_ADDR(PAL_TANK), WH(8, 8), OPT4);
            spr_pos(s_idx, sx, sy);
        } else {
            spr_hide(s_idx);
        }
    }

    /* Render Big Explosions */
    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) {
        uint8_t s_idx = SPR_EXPLOSION_START + i;
        if (explosions[i].active) {
            uint16_t addr = XRAM_IMG_EXPLOSION + (uint16_t)explosions[i].frame * EXPLOSION_FRAME_BYTES;
            spr_setup(s_idx, addr, PAL_ADDR(PAL_EXPLOSION), WH(32, 16), OPT4);
            spr_pos(s_idx, explosions[i].screen_x, explosions[i].screen_y);
        } else {
            spr_hide(s_idx);
        }
    }

    /* Render Small Explosions */
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) {
        uint8_t s_idx = SPR_SMALLEXP_START + i;
        if (small_explosions[i].active) {
            uint16_t addr = XRAM_IMG_SMALLEXPLOSION + (uint16_t)small_explosions[i].frame * SMALLEXPLOSION_FRAME_BYTES;
            spr_setup(s_idx, addr, PAL_ADDR(PAL_EXPLOSION), WH(16, 16), OPT4);
            spr_pos(s_idx, small_explosions[i].screen_x, small_explosions[i].screen_y);
        } else {
            spr_hide(s_idx);
        }
    }
}
