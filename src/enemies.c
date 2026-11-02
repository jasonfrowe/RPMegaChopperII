#include <rp6502.h>
#include <stdlib.h>
#include "enemies.h"
#include "game.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

typedef struct
{
    bool active;
    int32_t world_x; // Subpixels
    int8_t dir;      // -1 or 1
    int16_t min_x;
    int16_t max_x;
    uint8_t turret_angle; // 0 = UP_LEFT, 1 = UP, 2 = UP_RIGHT
    uint8_t tread_anim;
    uint8_t fire_cooldown;
} tank_t;

typedef struct
{
    bool active;
    int32_t world_x;
    int16_t y;
    int16_t vx;
    uint8_t fire_timer;
} jet_t;

typedef struct
{
    bool active;
    int32_t world_x;
    int16_t base_y;
    int16_t y;
    int8_t bob_phase;
    uint8_t anim;
} balloon_t;

static tank_t tanks[SPR_TANK_COUNT];
static jet_t jets[SPR_JET_COUNT];
static balloon_t balloons[SPR_BALLOON_COUNT];

static uint16_t jet_spawn_timer;

void enemies_init(void)
{
    enemies_reset();
}

void enemies_reset(void)
{
    /* Initialize 4 Tanks patrolling near the 4 compounds */
    static const int16_t tank_bases[SPR_TANK_COUNT] = {520, 1320, 2200, 3000};
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        tanks[i].active = true;
        tanks[i].world_x = TO_SUB(tank_bases[i]);
        tanks[i].dir = (i & 1) ? 1 : -1;
        tanks[i].min_x = tank_bases[i] - 120;
        tanks[i].max_x = tank_bases[i] + 120;
        tanks[i].turret_angle = 1;
        tanks[i].tread_anim = 0;
        tanks[i].fire_cooldown = 60 + (i * 25);
    }

    /* Initialize 4 Drone Balloons patrolling airspace */
    static const int16_t balloon_x[SPR_BALLOON_COUNT] = {850, 1750, 2600, 3400};
    static const int16_t balloon_y[SPR_BALLOON_COUNT] = {80, 110, 70, 95};
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        balloons[i].active = true;
        balloons[i].world_x = TO_SUB(balloon_x[i]);
        balloons[i].base_y = balloon_y[i];
        balloons[i].y = balloon_y[i];
        balloons[i].bob_phase = i * 40;
        balloons[i].anim = 0;
    }

    for (uint8_t i = 0; i < SPR_JET_COUNT; i++) {
        jets[i].active = false;
    }
    jet_spawn_timer = 200;
}

void enemies_update(void)
{
    int16_t chop_px = FROM_SUB(chopper_world_x) + 16;
    int16_t chop_py = FROM_SUB(chopper_y) + 8;

    /* Update Tanks */
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        if (!tanks[i].active) continue;

        /* Tank driving patrol */
        tanks[i].world_x += tanks[i].dir * (TO_SUB(1) / 3);
        int16_t tx = FROM_SUB(tanks[i].world_x);
        if (tx < tanks[i].min_x) {
            tanks[i].world_x = TO_SUB(tanks[i].min_x);
            tanks[i].dir = 1;
        } else if (tx > tanks[i].max_x) {
            tanks[i].world_x = TO_SUB(tanks[i].max_x);
            tanks[i].dir = -1;
        }
        tanks[i].tread_anim = (frame_count >> 3) & 1;

        /* Aim turret towards chopper */
        int16_t dx = chop_px - tx;
        if (dx < -30) {
            tanks[i].turret_angle = 0; /* UP_LEFT */
        } else if (dx > 30) {
            tanks[i].turret_angle = 2; /* UP_RIGHT */
        } else {
            tanks[i].turret_angle = 1; /* UP */
        }

        /* Fire flak shells when player is airborne within range */
        if (tanks[i].fire_cooldown > 0) {
            tanks[i].fire_cooldown--;
        } else if (abs(dx) < 220 && chop_py < GROUND_Y) {
            uint8_t min_cd = (current_level >= 3) ? 35 : ((current_level == 2) ? 50 : 75);
            uint8_t max_cd = (current_level >= 3) ? 75 : ((current_level == 2) ? 100 : 130);
            tanks[i].fire_cooldown = rng_range8(min_cd, max_cd);

            int16_t vx = (tanks[i].turret_angle == 0) ? -TO_SUB(3) : (tanks[i].turret_angle == 2 ? TO_SUB(3) : 0);
            int16_t vy = -TO_SUB(4);
            ebullet_spawn(tx + 20, GROUND_Y - 4, vx, vy);
            sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
        }
    }

    /* Update Balloons */
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        if (!balloons[i].active) continue;

        balloons[i].bob_phase += 2;
        /* Gentle sinusoidal floating */
        int8_t dy = ((balloons[i].bob_phase >> 3) & 7) - 4;
        balloons[i].y = balloons[i].base_y + dy;
        balloons[i].anim = (frame_count >> 4) % 3;

        /* Collision with chopper */
        if (player_status == PL_ALIVE) {
            int16_t bx = FROM_SUB(balloons[i].world_x) + 8;
            int16_t by = balloons[i].y + 16;
            if (abs(chop_px - bx) < 18 && abs(chop_py - by) < 18) {
                balloons[i].active = false;
                int16_t sx = bx - FROM_SUB(camera_x);
                explosion_spawn(sx - 8, by - 8, true);
                player_kill();
            }
        }
    }

    /* Update Fighter Jets */
    if (chop_py < 120 && player_status == PL_ALIVE) {
        if (--jet_spawn_timer == 0) {
            uint16_t base = (current_level >= 3) ? 120 : ((current_level == 2) ? 180 : 240);
            jet_spawn_timer = base + rng_range8(0, 120);
            for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
                if (!jets[j].active) {
                    jets[j].active = true;
                    /* Spawn ahead of camera direction */
                    if (rng_next() & 1) {
                        jets[j].world_x = camera_x + TO_SUB(SCREEN_W + 40);
                        jets[j].vx = -TO_SUB(6);
                    } else {
                        jets[j].world_x = camera_x - TO_SUB(40);
                        jets[j].vx = TO_SUB(6);
                    }
                    jets[j].y = 45 + rng_range8(0, 40);
                    jets[j].fire_timer = 30;
                    sfx_enemy(SFX_JET_FLYBY, SFX_PRI_EVENT);
                    break;
                }
            }
        }
    }

    for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
        if (!jets[j].active) continue;

        jets[j].world_x += jets[j].vx;
        int16_t jx = FROM_SUB(jets[j].world_x);
        int16_t sx = jx - FROM_SUB(camera_x);

        if (sx < -80 || sx > SCREEN_W + 80) {
            jets[j].active = false;
            continue;
        }

        /* Fire air-to-air burst when passing chopper */
        if (--jets[j].fire_timer == 0) {
            jets[j].fire_timer = 50;
            int16_t b_vx = (jets[j].vx < 0) ? -TO_SUB(7) : TO_SUB(7);
            ebullet_spawn(jx + 16, jets[j].y + 6, b_vx, TO_SUB(1));
        }

        /* Collision with chopper */
        if (player_status == PL_ALIVE) {
            if (abs(chop_px - (jx + 16)) < 20 && abs(chop_py - (jets[j].y + 8)) < 14) {
                jets[j].active = false;
                explosion_spawn(sx, jets[j].y, true);
                player_kill();
            }
        }
    }
}

bool tanks_check_hit(int16_t hit_x, int16_t hit_y)
{
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        if (tanks[i].active) {
            int16_t tx = FROM_SUB(tanks[i].world_x);
            if (hit_x >= tx && hit_x <= tx + 40 && hit_y >= GROUND_Y - 12 && hit_y <= GROUND_Y + 12) {
                tanks[i].active = false;
                add_score(200);
                sfx_enemy(SFX_BIG_EXPLODE, SFX_PRI_DESTROY);
                int16_t sx = tx - FROM_SUB(camera_x);
                explosion_spawn(sx + 4, GROUND_Y - 8, true);
                return true;
            }
        }
    }
    return false;
}

bool balloons_check_hit(int16_t hit_x, int16_t hit_y)
{
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        if (balloons[i].active) {
            int16_t bx = FROM_SUB(balloons[i].world_x);
            if (hit_x >= bx && hit_x <= bx + 16 && hit_y >= balloons[i].y && hit_y <= balloons[i].y + 32) {
                balloons[i].active = false;
                add_score(100);
                sfx_enemy(SFX_EXPLODE, SFX_PRI_DESTROY);
                int16_t sx = bx - FROM_SUB(camera_x);
                small_explosion_spawn(sx, balloons[i].y + 8);
                return true;
            }
        }
    }
    return false;
}

bool jets_check_hit(int16_t hit_x, int16_t hit_y)
{
    for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
        if (jets[j].active) {
            int16_t jx = FROM_SUB(jets[j].world_x);
            if (hit_x >= jx && hit_x <= jx + 32 && hit_y >= jets[j].y && hit_y <= jets[j].y + 16) {
                jets[j].active = false;
                add_score(300);
                sfx_enemy(SFX_BIG_EXPLODE, SFX_PRI_DESTROY);
                int16_t sx = jx - FROM_SUB(camera_x);
                explosion_spawn(sx, jets[j].y, true);
                return true;
            }
        }
    }
    return false;
}

void enemies_render(void)
{
    /* Render Canadian Flag at Home Base (SPR_FLAG) */
    int16_t flag_sx = 3880 - FROM_SUB(camera_x);
    if (flag_sx > -16 && flag_sx < SCREEN_W) {
        uint8_t f_anim = (frame_count >> 3) & 1;
        uint16_t addr = XRAM_IMG_FLAGS + (uint16_t)f_anim * FLAGS_FRAME_BYTES;
        spr_setup(SPR_FLAG, addr, PAL_ADDR(PAL_FLAGS), WH(16, 16), OPT4);
        spr_pos(SPR_FLAG, flag_sx, 172);
    } else {
        spr_hide(SPR_FLAG);
    }

    /* Render Tanks */
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        uint8_t spr_idx = SPR_TANK_START + i;
        if (tanks[i].active) {
            int16_t sx = FROM_SUB(tanks[i].world_x - camera_x);
            if (sx > -40 && sx < SCREEN_W) {
                /* Frame calculation: 3 turret angles x 2 tread anims */
                uint8_t f = tanks[i].tread_anim * 3 + tanks[i].turret_angle;
                uint16_t addr = XRAM_IMG_TANK + (uint16_t)f * TANK_FRAME_BYTES;
                spr_setup(spr_idx, addr, PAL_ADDR(PAL_TANK), WH(40, 16), OPT4);
                spr_pos(spr_idx, sx, GROUND_Y);
            } else {
                spr_hide(spr_idx);
            }
        } else {
            spr_hide(spr_idx);
        }
    }

    /* Render Balloons */
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        uint8_t spr_idx = SPR_BALLOON_START + i;
        if (balloons[i].active) {
            int16_t sx = FROM_SUB(balloons[i].world_x - camera_x);
            if (sx > -16 && sx < SCREEN_W) {
                uint16_t addr = XRAM_IMG_BALLOON + (uint16_t)balloons[i].anim * BALLOON_FRAME_BYTES;
                spr_setup(spr_idx, addr, PAL_ADDR(PAL_BALLOON), WH(16, 32), OPT4);
                spr_pos(spr_idx, sx, balloons[i].y);
            } else {
                spr_hide(spr_idx);
            }
        } else {
            spr_hide(spr_idx);
        }
    }

    /* Render Jets */
    for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
        uint8_t spr_idx = SPR_JET_START + j;
        if (jets[j].active) {
            int16_t sx = FROM_SUB(jets[j].world_x - camera_x);
            if (sx > -32 && sx < SCREEN_W) {
                uint8_t f = (jets[j].vx < 0) ? 0 : 1;
                uint16_t addr = XRAM_IMG_JET + (uint16_t)f * JET_FRAME_BYTES;
                spr_setup(spr_idx, addr, PAL_ADDR(PAL_JET), WH(32, 16), OPT4);
                spr_pos(spr_idx, sx, jets[j].y);
            } else {
                spr_hide(spr_idx);
            }
        } else {
            spr_hide(spr_idx);
        }
    }
}
