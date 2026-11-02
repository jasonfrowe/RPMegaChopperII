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
    int32_t x;        /* subpixels, left edge */
    int8_t dir;       /* -1 left, 1 right */
    int16_t home;     /* patrols around here */
    uint8_t cooldown;
    uint16_t respawn; /* frames until a destroyed tank rolls out again */
    bool aim_up;
} tank_t;

typedef struct
{
    bool active;
    int32_t x;
    int16_t y;
    int16_t vx;
    uint8_t fire_timer;
} jet_t;

typedef struct
{
    bool active;
    int16_t x, base_y, y;
    uint8_t phase;
} balloon_t;

static tank_t tanks[SPR_TANK_COUNT];
static jet_t jets[SPR_JET_COUNT];
static balloon_t balloons[SPR_BALLOON_COUNT];
static uint16_t jet_timer;

/* Tanks patrol between the compounds, the balloons hang over them. */
static const int16_t tank_home[SPR_TANK_COUNT] = {700, 1700, 2650, 3450};
static const int16_t balloon_x[SPR_BALLOON_COUNT] = {560, 1520, 2480, 3300};
static const int16_t balloon_y[SPR_BALLOON_COUNT] = {70, 100, 60, 90};

static void tank_reset(uint8_t i)
{
    tank_t *t = &tanks[i];
    t->active = true;
    t->home = tank_home[i];
    t->x = TO_SUB(tank_home[i]);
    t->dir = (i & 1) ? 1 : -1;
    t->cooldown = 90 + i * 20;
    t->aim_up = false;
}

void enemies_init(void)
{
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++)
        tank_reset(i);
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        balloons[i].active = true;
        balloons[i].x = balloon_x[i];
        balloons[i].base_y = balloon_y[i];
        balloons[i].y = balloon_y[i];
        balloons[i].phase = i * 60;
    }
    for (uint8_t j = 0; j < SPR_JET_COUNT; j++)
        jets[j].active = false;
    jet_timer = 400;
}

static uint8_t difficulty(uint8_t easy, uint8_t hard)
{
    /* Later sectors fire faster. */
    uint8_t lv = current_level > 4 ? 4 : current_level;
    return (uint8_t)(easy - (easy - hard) * (lv - 1) / 3);
}

static void update_tanks(int16_t ccx, int16_t cy, int16_t cam)
{
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        tank_t *t = &tanks[i];
        if (!t->active) {
            /* Roll back in from off screen after a while. */
            if (t->respawn && --t->respawn == 0) {
                if (abs(tank_home[i] - (cam + SCREEN_W / 2)) < SCREEN_W)
                    t->respawn = 60; /* not where the player can see */
                else
                    tank_reset(i);
            }
            continue;
        }
        if ((frame_count & 1) == 0)
            t->x += t->dir * 9;
        int16_t tx = FROM_SUB(t->x);
        if (tx < t->home - 160)
            t->dir = 1;
        else if (tx > t->home + 160)
            t->dir = -1;

        /* Turn to face the chopper when it is near. */
        int16_t dx = ccx - (tx + TANK_W / 2);
        if (abs(dx) < 140 && (frame_count & 63) == 0)
            t->dir = dx < 0 ? -1 : 1;
        t->aim_up = abs(dx) < 36 || (dx < 0) != (t->dir < 0);

        if (t->cooldown) {
            t->cooldown--;
        } else if (player_alive() && !chopper_is_landed && abs(dx) < 200 && tx > cam - 20 &&
                   tx < cam + SCREEN_W) {
            t->cooldown = difficulty(110, 50) + (rng_next() & 31);
            /* Lead the shot toward where the chopper is. */
            int16_t vx = 0;
            if (!t->aim_up)
                vx = dx / 5 > 40 ? 40 : (dx / 5 < -40 ? -40 : dx / 5);
            int16_t muzzle = t->aim_up ? tx + 18 : (t->dir < 0 ? tx + 2 : tx + TANK_W - 10);
            int16_t vy = -(int16_t)(48 + (GROUND_LINE - cy) / 3); /* enough to reach that high */
            ebullet_spawn(muzzle, TANK_Y - (t->aim_up ? 2 : -4), vx, vy);
            sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
        }
    }
}

static void update_jets(int16_t ccx, int16_t cy)
{
    /* Fly high and the interceptors come for you. */
    if (player_alive() && cy < 110) {
        uint8_t step = cy < 70 ? 2 : 1;
        jet_timer = jet_timer > step ? jet_timer - step : 0;
    }
    if (jet_timer == 0) {
        jet_timer = (uint16_t)difficulty(240, 120) + (rng_next() & 127);
        for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
            jet_t *e = &jets[j];
            if (e->active)
                continue;
            e->active = true;
            if (rng_next() & 1) {
                e->x = camera_x + TO_SUB(SCREEN_W + 40);
                e->vx = -TO_SUB(5);
            } else {
                e->x = camera_x - TO_SUB(80);
                e->vx = TO_SUB(5);
            }
            e->y = cy - 8 + (int16_t)(rng_next() & 15);
            if (e->y < CEILING_Y)
                e->y = CEILING_Y;
            e->fire_timer = 20;
            sfx_enemy(SFX_JET_FLYBY, SFX_PRI_EVENT);
            break;
        }
    }
    for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
        jet_t *e = &jets[j];
        if (!e->active)
            continue;
        e->x += e->vx;
        int16_t jx = FROM_SUB(e->x);
        int16_t sx = screen_x(jx);
        if ((e->vx < 0 && sx < -60) || (e->vx > 0 && sx > SCREEN_W + 60)) {
            e->active = false;
            continue;
        }
        if (e->fire_timer && --e->fire_timer == 0) {
            /* One burst, when the chopper is ahead. */
            int16_t ahead = (e->vx < 0) ? jx - ccx : ccx - jx;
            if (ahead > 40 && ahead < 220) {
                int16_t nose = e->vx < 0 ? jx : jx + JET_W;
                ebullet_spawn(nose, e->y + 8, e->vx + (e->vx < 0 ? -TO_SUB(2) : TO_SUB(2)), -6);
            } else {
                e->fire_timer = 6;
            }
        }
        if (player_alive() && abs(ccx - (jx + JET_W / 2)) < 22 && abs(cy - (e->y + 8)) < 12) {
            e->active = false;
            explosion_spawn(jx + JET_W / 2, e->y + 8, true);
            player_kill();
        }
    }
}

static void update_balloons(int16_t ccx, int16_t cy)
{
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        balloon_t *b = &balloons[i];
        if (!b->active)
            continue;
        b->phase++;
        uint8_t p = b->phase >> 2;
        int8_t tri = (int8_t)((p & 32) ? 31 - (p & 31) : (p & 31)) - 16;
        b->y = b->base_y + tri / 3;
        if (player_alive() && abs(ccx - (b->x + 8)) < 18 && abs(cy - (b->y + 14)) < 18) {
            b->active = false;
            explosion_spawn(b->x + 8, b->y + 14, true);
            player_kill();
        }
    }
}

void enemies_update(void)
{
    int16_t ccx = chopper_cx();
    int16_t cy = FROM_SUB(chopper_y) + CHOPPER_H / 2;
    int16_t cam = FROM_SUB(camera_x);
    update_tanks(ccx, cy, cam);
    update_jets(ccx, cy);
    update_balloons(ccx, cy);
}

bool tanks_check_hit(int16_t x, int16_t y)
{
    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        tank_t *t = &tanks[i];
        if (!t->active)
            continue;
        int16_t tx = FROM_SUB(t->x);
        if (x >= tx && x < tx + TANK_W && y >= TANK_Y + 4 && y <= GROUND_LINE) {
            t->active = false;
            t->respawn = 900;
            add_score(200);
            explosion_spawn(tx + TANK_W / 2, TANK_Y + 8, true);
            return true;
        }
    }
    return false;
}

bool balloons_check_hit(int16_t x, int16_t y)
{
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        balloon_t *b = &balloons[i];
        if (b->active && x >= b->x && x < b->x + 16 && y >= b->y && y < b->y + 32) {
            b->active = false;
            add_score(100);
            explosion_spawn(b->x + 8, b->y + 14, true);
            return true;
        }
    }
    return false;
}

bool jets_check_hit(int16_t x, int16_t y)
{
    for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
        jet_t *e = &jets[j];
        if (!e->active)
            continue;
        int16_t jx = FROM_SUB(e->x);
        if (x >= jx && x < jx + JET_W && y >= e->y + 2 && y < e->y + 14) {
            e->active = false;
            add_score(300);
            explosion_spawn(jx + JET_W / 2, e->y + 8, true);
            return true;
        }
    }
    return false;
}

void enemies_render(void)
{
    int16_t cam = FROM_SUB(camera_x);
    spr_place(SPR_FLAG, XRAM_IMG_FLAGS + ((frame_count >> 3) & 3) * FLAGS_FRAME_BYTES, PAL_FLAG, WH(24, 16), OPT4,
              FLAG_X - cam, FLAG_Y);

    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        tank_t *t = &tanks[i];
        if (!t->active) {
            spr_hide(SPR_TANK_START + i);
            continue;
        }
        uint8_t f = (t->aim_up ? 2 : 0) + ((FROM_SUB(t->x) >> 2) & 1);
        spr_place(SPR_TANK_START + i, XRAM_IMG_TANK + f * TANK_FRAME_BYTES, PAL_TANK, WH(TANK_W, TANK_H),
                  t->dir > 0 ? OPT4_FLIP : OPT4, FROM_SUB(t->x) - cam, TANK_Y);
    }
    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        balloon_t *b = &balloons[i];
        if (!b->active) {
            spr_hide(SPR_BALLOON_START + i);
            continue;
        }
        uint8_t f = ((frame_count >> 4) % 3);
        spr_place(SPR_BALLOON_START + i, XRAM_IMG_BALLOON + f * BALLOON_FRAME_BYTES, PAL_BALLOON,
                  WH(BALLOON_W, BALLOON_H), OPT4, b->x - cam, b->y);
    }
    for (uint8_t j = 0; j < SPR_JET_COUNT; j++) {
        jet_t *e = &jets[j];
        if (!e->active) {
            spr_hide(SPR_JET_START + j);
            continue;
        }
        spr_place(SPR_JET_START + j, XRAM_IMG_JET + ((frame_count >> 1) & 1) * JET_FRAME_BYTES, PAL_JET,
                  WH(JET_W, JET_H), e->vx > 0 ? OPT4_FLIP : OPT4, FROM_SUB(e->x) - cam, e->y);
    }
}
