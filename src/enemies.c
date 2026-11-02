#include <rp6502.h>
#include <stdlib.h>
#include "compounds.h"
#include "enemies.h"
#include "game.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

/*
 * The enemy follows the rules of Choplifter (and RPMegaChopper):
 *  - Tanks only turn up once the rescue is under way. Each prison keeps two
 *    in its garage; they roll in from off screen at the prison nearest the
 *    chopper, stay close to it, and chase along underneath. Only bombs
 *    destroy them. Their flak arcs and falls back, so it cannot reach high.
 *  - A mine balloon drifts after the chopper once enough hostages are out.
 *  - Jets come later still: sit on the ground too long and one bombs you,
 *    hang about up high and one strafes you.
 *  - Nothing attacks east of SAFE_LINE, around the home base.
 */

#define TANKS_ACTIVE 2
#define TANKS_PER_BASE 2
#define TANK_TRIGGER 4        /* hostages aboard or saved before tanks appear */
#define TANK_LEASH 100        /* px either side of the prison */
#define TANK_SPAWN_DIST 240   /* px from the prison they roll in from */
#define TANK_SPACING 46

#define BALLOON_TRIGGER 16    /* hostages out of the prisons */
#define BALLOON_RESPAWN 300
#define BALLOON_FLOOR (GROUND_LINE - 72) /* lowest it comes, top of sprite */

#define JET_GROUND_WAIT 120   /* frames landed before a bomber comes */
#define JET_AIR_WAIT 240      /* frames up high before a fighter comes */
#define JET_AIR_ZONE 75       /* "up high": chopper above this screen row */

typedef struct
{
    bool active;
    int32_t x; /* subpixels, left edge */
    int8_t dir;
    int8_t move;
    uint8_t base;
    uint8_t cooldown;
    uint8_t anim;
    uint8_t aim; /* 0 raised forward, 1 straight up */
} tank_t;

typedef struct
{
    bool active, falling;
    int32_t x, y; /* subpixels */
    int16_t vy;
    uint16_t respawn;
} balloon_t;

enum
{
    JET_OFF,
    JET_ATTACK,
    JET_LEAVE
};

typedef struct
{
    uint8_t state;
    bool bomber;
    int32_t x;
    int16_t y;
    int8_t dir;
} jet_t;

static tank_t tanks[TANKS_ACTIVE];
static uint8_t garage[NUM_COMPOUNDS];
static bool tanks_triggered;
static uint8_t tank_spawn_timer;
static balloon_t balloon;
static jet_t jet;
static uint16_t loiter_ground, loiter_air;

void enemies_init(void)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++)
        tanks[i].active = false;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
        garage[i] = 0;
    tanks_triggered = false;
    tank_spawn_timer = 0;
    balloon.active = false;
    balloon.respawn = 0;
    jet.state = JET_OFF;
    loiter_ground = loiter_air = 0;
}

/* Later sectors are harder: thresholds and waits shrink. */
static uint8_t level_scale(uint8_t base)
{
    uint8_t lv = current_level > 4 ? 4 : current_level;
    return (uint8_t)(base - base * (lv - 1) / 6);
}

static int16_t base_x(uint8_t b)
{
    return DOOR_X(b) + DOOR_W * 8;
}

static uint8_t nearest_base(int16_t x)
{
    uint8_t best = 0;
    for (uint8_t i = 1; i < NUM_COMPOUNDS; i++)
        if (abs(base_x(i) - x) < abs(base_x(best) - x))
            best = i;
    return best;
}

static bool offscreen(int16_t x, int16_t w)
{
    int16_t sx = screen_x(x);
    return sx < -w - 16 || sx > SCREEN_W + 16;
}

/* --- Tanks ---------------------------------------------------------------- */

/* Flak aim, by how steep the shot must be: straight up to almost level.
 * With FLAK_GRAVITY these top out a little above FLAK_CEILING. */
static const int8_t aim_vx[5] = {0, 30, 58, 74, 84};
static const int8_t aim_vy[5] = {-84, -78, -60, -36, -14};

static void tank_fire(tank_t *t, int16_t ccx, int16_t cy)
{
    int16_t ox = FROM_SUB(t->x) + TANK_W / 2;
    int16_t oy = TANK_Y + 2;
    int16_t dx = abs(ccx - ox);
    int16_t dy = oy - (cy - 32); /* aim above it: the shell drops */
    if (dy < 16)
        dy = 16;
    uint8_t a;
    if (dx < dy / 4)
        a = 0;
    else if (dx < dy - dy / 4)
        a = 1;
    else if (dx < dy + dy / 2)
        a = 2;
    else if (dx < dy * 3)
        a = 3;
    else
        a = 4;
    int16_t vx = ccx > ox ? aim_vx[a] : -aim_vx[a];
    ebullet_spawn(ox - 4, oy - 2, vx, aim_vy[a], EB_FLAK);
    sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
}

static void update_tanks(int16_t ccx, int16_t cy, bool safe)
{
    if (!tanks_triggered && saved_count + cargo_count >= TANK_TRIGGER) {
        tanks_triggered = true;
        for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
            garage[i] = TANKS_PER_BASE;
    }
    uint8_t b = nearest_base(ccx);

    /* Roll one out, from whichever side of the prison has none, out of sight. */
    if (tank_spawn_timer)
        tank_spawn_timer--;
    if (tanks_triggered && !safe && garage[b] && !tank_spawn_timer) {
        bool left = false, right = false;
        tank_t *slot = 0;
        for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
            if (!tanks[i].active) {
                if (!slot)
                    slot = &tanks[i];
            } else if (tanks[i].base == b) {
                if (FROM_SUB(tanks[i].x) < base_x(b))
                    left = true;
                else
                    right = true;
            }
        }
        if (slot && (!left || !right)) {
            int16_t x = !left ? base_x(b) - TANK_SPAWN_DIST : base_x(b) + TANK_SPAWN_DIST;
            if (offscreen(x, TANK_W) && x > 0 && x < WORLD_W_PX - TANK_W) {
                slot->active = true;
                slot->base = b;
                slot->x = TO_SUB(x);
                slot->dir = !left ? 1 : -1;
                slot->cooldown = 40;
                slot->anim = 0;
                garage[b]--;
                tank_spawn_timer = 60;
            }
        }
    }

    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active)
            continue;
        /* The chopper has moved on to another prison: back to the garage. */
        if (t->base != b && offscreen(FROM_SUB(t->x), TANK_W)) {
            t->active = false;
            garage[t->base]++;
            continue;
        }
        int16_t tx = FROM_SUB(t->x);
        int16_t from_base = tx + TANK_W / 2 - base_x(t->base);
        int16_t to_chopper = ccx - (tx + TANK_W / 2);
        int8_t want = to_chopper > 0 ? 1 : -1;
        if (from_base > TANK_LEASH)
            want = -1;
        else if (from_base < -TANK_LEASH)
            want = 1;
        if (abs(to_chopper) < 4)
            want = 0;
        for (uint8_t j = 0; j < TANKS_ACTIVE && want; j++) {
            if (j == i || !tanks[j].active)
                continue;
            int16_t sep = FROM_SUB(tanks[j].x) - tx;
            if ((want > 0 && sep > 0 && sep < TANK_SPACING) || (want < 0 && sep < 0 && sep > -TANK_SPACING))
                want = 0;
        }
        t->move = want;
        if (want) {
            t->dir = want;
            t->x += want * 12;
            t->anim++;
        }
        t->aim = abs(to_chopper) < 24 || (to_chopper < 0) != (t->dir < 0);

        if (t->cooldown) {
            t->cooldown--;
        } else if (!safe && player_alive() && !offscreen(tx, TANK_W) && (rng_next() & 63) < 2 + current_level) {
            tank_fire(t, ccx, cy);
            t->cooldown = (uint8_t)(level_scale(30) + (rng_next() & 31));
        }
    }
}

bool tanks_check_hit(int16_t x, int16_t y, bool bomb)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active)
            continue;
        int16_t tx = FROM_SUB(t->x);
        if (x < tx + 2 || x >= tx + TANK_W - 2 || y < TANK_Y + 4 || y > GROUND_LINE)
            continue;
        if (!bomb)
            return true; /* the shot glances off the armor */
        t->active = false; /* gone for good: it doesn't go back to the garage */
        add_score(200);
        explosion_spawn(tx + TANK_W / 2, TANK_Y + 8, true);
        return true;
    }
    return false;
}

/* --- The balloon ---------------------------------------------------------- */

static void update_balloon(int16_t ccx, int16_t cy, bool safe)
{
    balloon_t *b = &balloon;
    if (!b->active) {
        if (b->respawn) {
            b->respawn--;
            return;
        }
        if (safe || compounds_freed() < level_scale(BALLOON_TRIGGER))
            return;
        /* Float in from just off one side of the screen, never from home. */
        int16_t cam = FROM_SUB(camera_x);
        int16_t x = (rng_next() & 1) && cam + SCREEN_W + 48 < SAFE_LINE ? cam + SCREEN_W + 48 : cam - 64;
        if (x < 0)
            x = cam + SCREEN_W + 48;
        if (x >= SAFE_LINE)
            return;
        b->active = true;
        b->falling = false;
        b->x = TO_SUB(x);
        b->y = TO_SUB(BALLOON_FLOOR - 40);
        return;
    }

    if (b->falling) {
        /* Shot down: it drops and goes off on the ground. */
        b->vy += 2;
        b->y += b->vy;
        if (FROM_SUB(b->y) + BALLOON_H >= GROUND_LINE) {
            explosion_spawn(FROM_SUB(b->x) + 8, GROUND_LINE - 8, true);
            b->active = false;
            b->respawn = BALLOON_RESPAWN;
        }
        return;
    }

    /* Drift slowly after the chopper, but not below its floor, and back
     * off from the home base. */
    int16_t bx = FROM_SUB(b->x) + 8;
    int16_t by = FROM_SUB(b->y) + 14;
    if (safe || bx > SAFE_LINE)
        b->x -= 12;
    else if (abs(bx - ccx) > 2)
        b->x += bx < ccx ? 12 : -12;
    if (by < cy)
        b->y += 6;
    else
        b->y -= 6;
    if (FROM_SUB(b->y) > BALLOON_FLOOR)
        b->y = TO_SUB(BALLOON_FLOOR);
    if (FROM_SUB(b->y) < CEILING_Y)
        b->y = TO_SUB(CEILING_Y);

    if (player_alive() && abs(ccx - bx) < 18 && abs(cy - by) < 18) {
        explosion_spawn(bx, by, true);
        b->active = false;
        b->respawn = BALLOON_RESPAWN;
        player_kill();
    }
}

bool balloons_check_hit(int16_t x, int16_t y)
{
    balloon_t *b = &balloon;
    if (!b->active || b->falling)
        return false;
    int16_t bx = FROM_SUB(b->x), by = FROM_SUB(b->y);
    if (x < bx || x >= bx + 16 || y < by || y >= by + 32)
        return false;
    b->falling = true;
    b->vy = 0;
    add_score(150);
    small_explosion_spawn(x, y);
    sfx_enemy(SFX_EXPLODE, SFX_PRI_DESTROY);
    return true;
}

/* --- The jet -------------------------------------------------------------- */

static void update_jet(int16_t ccx, int16_t cy, bool safe)
{
    jet_t *j = &jet;
    if (j->state == JET_OFF) {
        if (safe || !player_alive() || compounds_freed() < level_scale(24)) {
            loiter_ground = loiter_air = 0;
            return;
        }
        bool go = false;
        if (chopper_is_landed) {
            if (++loiter_ground > JET_GROUND_WAIT && (rng_next() & 63) == 0) {
                go = true;
                j->bomber = true;
            }
        } else {
            loiter_ground = 0;
        }
        if (FROM_SUB(chopper_y) < JET_AIR_ZONE) {
            if (++loiter_air > JET_AIR_WAIT && (rng_next() & 63) == 0) {
                go = true;
                j->bomber = false;
            }
        } else {
            loiter_air = 0;
        }
        if (!go)
            return;
        loiter_ground = loiter_air = 0;
        j->state = JET_ATTACK;
        j->dir = (rng_next() & 1) ? 1 : -1;
        j->x = j->dir > 0 ? camera_x - TO_SUB(JET_W + 8) : camera_x + TO_SUB(SCREEN_W + 8);
        j->y = j->bomber ? GROUND_LINE - 96 : cy - 2;
        sfx_enemy(SFX_JET_FLYBY, SFX_PRI_EVENT);
        return;
    }

    j->x += j->dir * TO_SUB(4);
    int16_t jx = FROM_SUB(j->x);
    int16_t nose = j->dir > 0 ? jx + JET_W : jx;
    int16_t ahead = (ccx - nose) * j->dir; /* how far the chopper is in front */

    if (j->state == JET_ATTACK) {
        if (j->bomber) {
            /* Let go with enough lead that the bomb falls onto the chopper. */
            if (ahead > 42 && ahead < 60) {
                ebullet_spawn(jx + JET_W / 2 - 4, j->y + 10, j->dir * TO_SUB(2), 0, EB_BOMB);
                sfx_enemy(SFX_BOMB_DROP, SFX_PRI_EVENT);
                j->state = JET_LEAVE;
            }
        } else if (ahead > 0 && ahead < 100) {
            ebullet_spawn(nose - 4, j->y + 7, j->dir * TO_SUB(6), 0, EB_SHOT);
            sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
            j->state = JET_LEAVE;
        }
    } else {
        j->y -= 2; /* pull up and away */
    }
    if (offscreen(jx, JET_W) && ahead < 0)
        j->state = JET_OFF;
    else if (j->y < HUD_H - JET_H)
        j->state = JET_OFF;

    if (player_alive() && abs(ccx - (jx + JET_W / 2)) < 22 && abs(cy - (j->y + 8)) < 12) {
        j->state = JET_OFF;
        explosion_spawn(jx + JET_W / 2, j->y + 8, true);
        player_kill();
    }
}

bool jets_check_hit(int16_t x, int16_t y)
{
    jet_t *j = &jet;
    if (j->state == JET_OFF)
        return false;
    int16_t jx = FROM_SUB(j->x);
    if (x < jx || x >= jx + JET_W || y < j->y + 2 || y >= j->y + 14)
        return false;
    j->state = JET_OFF;
    add_score(300);
    explosion_spawn(jx + JET_W / 2, j->y + 8, true);
    return true;
}

/* --------------------------------------------------------------------------- */

void enemies_update(void)
{
    int16_t ccx = chopper_cx();
    int16_t cy = FROM_SUB(chopper_y) + CHOPPER_H / 2;
    bool safe = ccx > SAFE_LINE;
    update_tanks(ccx, cy, safe);
    update_balloon(ccx, cy, safe);
    update_jet(ccx, cy, safe);
}

void enemies_render(void)
{
    int16_t cam = FROM_SUB(camera_x);
    spr_place(SPR_FLAG, XRAM_IMG_FLAGS + ((frame_count >> 3) & 3) * FLAGS_FRAME_BYTES, PAL_FLAG, WH(24, 16), OPT4,
              FLAG_X - cam, FLAG_Y);

    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        tank_t *t = &tanks[i];
        if (i >= TANKS_ACTIVE || !t->active) {
            spr_hide(SPR_TANK_START + i);
            continue;
        }
        uint8_t f = (t->aim ? 2 : 0) + ((t->anim >> 3) & 1);
        spr_place(SPR_TANK_START + i, XRAM_IMG_TANK + f * TANK_FRAME_BYTES, PAL_TANK, WH(TANK_W, TANK_H),
                  t->dir > 0 ? OPT4_FLIP : OPT4, FROM_SUB(t->x) - cam, TANK_Y);
    }

    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        if (i || !balloon.active) {
            spr_hide(SPR_BALLOON_START + i);
            continue;
        }
        uint8_t f = balloon.falling ? (frame_count >> 1) % 3 : (frame_count >> 4) % 3;
        spr_place(SPR_BALLOON_START, XRAM_IMG_BALLOON + f * BALLOON_FRAME_BYTES, PAL_BALLOON,
                  WH(BALLOON_W, BALLOON_H), OPT4, FROM_SUB(balloon.x) - cam, FROM_SUB(balloon.y));
    }

    for (uint8_t i = 0; i < SPR_JET_COUNT; i++) {
        if (i || jet.state == JET_OFF) {
            spr_hide(SPR_JET_START + i);
            continue;
        }
        spr_place(SPR_JET_START, XRAM_IMG_JET + ((frame_count >> 1) & 1) * JET_FRAME_BYTES, PAL_JET,
                  WH(JET_W, JET_H), jet.dir > 0 ? OPT4_FLIP : OPT4, FROM_SUB(jet.x) - cam, jet.y);
    }
}
