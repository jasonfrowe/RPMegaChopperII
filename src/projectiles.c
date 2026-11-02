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
    int32_t x, y; /* subpixels */
    int16_t vx, vy;
    uint8_t age;
    uint8_t kind; /* enemy fire only: EB_* */
} shot_t;

typedef struct
{
    bool active;
    int16_t x, y; /* world, top left */
    uint8_t frame, timer;
} boom_t;

static shot_t bullets[SPR_BULLET_COUNT];
static shot_t bombs[SPR_BOMB_COUNT];
static shot_t ebullets[SPR_EBULLET_COUNT];
static boom_t booms[SPR_EXPLOSION_COUNT];
static boom_t pops[SPR_SMALLEXP_COUNT];

void projectiles_init(void)
{
    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) bullets[i].active = false;
    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) bombs[i].active = false;
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) ebullets[i].active = false;
    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) booms[i].active = false;
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) pops[i].active = false;
}

static void spawn(shot_t *pool, uint8_t n, int16_t x, int16_t y, int16_t vx, int16_t vy)
{
    for (uint8_t i = 0; i < n; i++) {
        if (!pool[i].active) {
            pool[i].active = true;
            pool[i].x = TO_SUB(x);
            pool[i].y = TO_SUB(y);
            pool[i].vx = vx;
            pool[i].vy = vy;
            pool[i].age = 0;
            return;
        }
    }
}

void bullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy)
{
    spawn(bullets, SPR_BULLET_COUNT, x, y, vx, vy);
}

void bomb_spawn(int16_t x, int16_t y, int16_t vx)
{
    spawn(bombs, SPR_BOMB_COUNT, x, y, vx, ONE_PIXEL / 2);
}

void ebullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy, uint8_t kind)
{
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) {
        if (!ebullets[i].active) {
            spawn(&ebullets[i], 1, x, y, vx, vy);
            ebullets[i].kind = kind;
            return;
        }
    }
}

static void boom(boom_t *pool, uint8_t n, int16_t x, int16_t y)
{
    uint8_t oldest = 0;
    for (uint8_t i = 0; i < n; i++) {
        if (!pool[i].active) {
            oldest = i;
            break;
        }
        if (pool[i].frame > pool[oldest].frame)
            oldest = i;
    }
    pool[oldest].active = true;
    pool[oldest].x = x;
    pool[oldest].y = y;
    pool[oldest].frame = 0;
    pool[oldest].timer = 0;
}

void explosion_spawn(int16_t cx, int16_t cy, bool big)
{
    if (big) {
        boom(booms, SPR_EXPLOSION_COUNT, cx - 16, cy - 20);
        sfx_enemy(SFX_BIG_EXPLODE, SFX_PRI_DESTROY);
    } else {
        small_explosion_spawn(cx, cy);
        sfx_enemy(SFX_EXPLODE, SFX_PRI_DESTROY);
    }
}

void small_explosion_spawn(int16_t cx, int16_t cy)
{
    boom(pops, SPR_SMALLEXP_COUNT, cx - 8, cy - 8);
}

/* A bomb's blast: everything near where it went off. */
static void blast(int16_t x, int16_t y)
{
    explosion_spawn(x, y, true);
    compounds_check_hit(x, y, true);
    for (int8_t dx = -12; dx <= 12; dx += 12) {
        tanks_check_hit(x + dx, y, true);
        hostages_check_hit(x + dx, y);
    }
}

void projectiles_update(void)
{
    int16_t cam = FROM_SUB(camera_x);

    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) {
        shot_t *b = &bullets[i];
        if (!b->active)
            continue;
        b->x += b->vx;
        b->y += b->vy;
        int16_t x = FROM_SUB(b->x) + 4, y = FROM_SUB(b->y) + 2;
        if (x < cam - 8 || x > cam + SCREEN_W + 8 || y < CEILING_Y || ++b->age > 70) {
            b->active = false;
            continue;
        }
        if (y >= GROUND_LINE) {
            b->active = false;
            small_explosion_spawn(x, GROUND_LINE - 2);
            continue;
        }
        if (compounds_check_hit(x, y, false) || tanks_check_hit(x, y, false) || balloons_check_hit(x, y) ||
            jets_check_hit(x, y) || hostages_check_hit(x, y)) {
            b->active = false;
            small_explosion_spawn(x, y);
        }
    }

    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) {
        shot_t *b = &bombs[i];
        if (!b->active)
            continue;
        b->x += b->vx;
        b->vy += 3; /* gravity */
        b->y += b->vy;
        int16_t x = FROM_SUB(b->x) + 4, y = FROM_SUB(b->y) + 7;
        if (y >= GROUND_LINE) {
            b->active = false;
            blast(x, GROUND_LINE - 4);
        } else if (compounds_check_hit(x, y, true) || tanks_check_hit(x, y, true)) {
            b->active = false;
            explosion_spawn(x, y, true);
        }
    }

    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) {
        shot_t *b = &ebullets[i];
        if (!b->active)
            continue;
        b->x += b->vx;
        b->y += b->vy;
        if (b->kind == EB_FLAK)
            b->vy += FLAK_GRAVITY;
        else if (b->kind == EB_BOMB)
            b->vy += 2;
        int16_t x = FROM_SUB(b->x) + 4, y = FROM_SUB(b->y) + (b->kind == EB_BOMB ? 6 : 2);
        if (x < cam - 32 || x > cam + SCREEN_W + 32 || y < HUD_H - 8) {
            b->active = false;
            continue;
        }
        if (y >= GROUND_LINE) {
            b->active = false;
            small_explosion_spawn(x, GROUND_LINE - 4);
            if (b->kind == EB_BOMB)
                sfx_enemy(SFX_EXPLODE, SFX_PRI_DESTROY);
            continue;
        }
        if (player_alive() && abs(x - chopper_cx()) < (b->kind == EB_BOMB ? 14 : 13) &&
            abs(y - (FROM_SUB(chopper_y) + 11)) < 9) {
            b->active = false;
            explosion_spawn(x, y, b->kind == EB_BOMB);
            player_kill();
            continue;
        }
        /* Flak coming back down can land on the hostages. */
        if (b->kind == EB_FLAK && b->vy > 0 && hostages_check_hit(x, y)) {
            b->active = false;
            continue;
        }
    }

    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) {
        boom_t *e = &booms[i];
        if (e->active && ++e->timer >= 4) {
            e->timer = 0;
            if (++e->frame >= EXPLOSION_FRAMES)
                e->active = false;
        }
    }
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) {
        boom_t *e = &pops[i];
        if (e->active && ++e->timer >= 3) {
            e->timer = 0;
            if (++e->frame >= SMALLEXPLOSION_FRAMES)
                e->active = false;
        }
    }
}

void projectiles_render(void)
{
    int16_t cam = FROM_SUB(camera_x);
    for (uint8_t i = 0; i < SPR_BULLET_COUNT; i++) {
        shot_t *b = &bullets[i];
        if (b->active)
            spr_place(SPR_BULLET_START + i, XRAM_IMG_BULLET, PAL_FX, WH(8, 4), b->vx < 0 ? OPT4_FLIP : OPT4,
                      FROM_SUB(b->x) - cam, FROM_SUB(b->y));
        else
            spr_hide(SPR_BULLET_START + i);
    }
    for (uint8_t i = 0; i < SPR_BOMB_COUNT; i++) {
        shot_t *b = &bombs[i];
        if (b->active)
            spr_place(SPR_BOMB_START + i, XRAM_IMG_BOMB + ((frame_count >> 2) & 1) * BOMB_FRAME_BYTES, PAL_FX,
                      WH(8, 8), OPT4, FROM_SUB(b->x) - cam, FROM_SUB(b->y));
        else
            spr_hide(SPR_BOMB_START + i);
    }
    for (uint8_t i = 0; i < SPR_EBULLET_COUNT; i++) {
        shot_t *b = &ebullets[i];
        if (b->active && b->kind == EB_BOMB)
            spr_place(SPR_EBULLET_START + i, XRAM_IMG_BOMB + ((frame_count >> 2) & 1) * BOMB_FRAME_BYTES, PAL_FX,
                      WH(8, 8), OPT4, FROM_SUB(b->x) - cam, FROM_SUB(b->y));
        else if (b->active)
            spr_place(SPR_EBULLET_START + i, XRAM_IMG_BULLET + BULLET_FRAME_BYTES, PAL_FX, WH(8, 4), OPT4,
                      FROM_SUB(b->x) - cam, FROM_SUB(b->y));
        else
            spr_hide(SPR_EBULLET_START + i);
    }
    for (uint8_t i = 0; i < SPR_EXPLOSION_COUNT; i++) {
        boom_t *e = &booms[i];
        if (e->active)
            spr_place(SPR_EXPLOSION_START + i, XRAM_IMG_EXPLOSION + (uint16_t)e->frame * EXPLOSION_FRAME_BYTES,
                      PAL_FX, WH(32, 32), OPT4, e->x - cam, e->y);
        else
            spr_hide(SPR_EXPLOSION_START + i);
    }
    for (uint8_t i = 0; i < SPR_SMALLEXP_COUNT; i++) {
        boom_t *e = &pops[i];
        if (e->active)
            spr_place(SPR_SMALLEXP_START + i, XRAM_IMG_SMALLEXPLOSION + (uint16_t)e->frame * SMALLEXPLOSION_FRAME_BYTES,
                      PAL_FX, WH(16, 16), OPT4, e->x - cam, e->y);
        else
            spr_hide(SPR_SMALLEXP_START + i);
    }
}
