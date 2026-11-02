#include <rp6502.h>
#include <stdlib.h>
#include "compounds.h"
#include "enemies.h"
#include "game.h"
#include "input.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

/* The rules are the original game's: see docs/ORIGINAL_GAMEPLAY.md.
 * Heights "above landed height" are measured up from GROUND_Y. */

/* --- Tanks ---------------------------------------------------------------- */
#define TANKS_ACTIVE 2
#define TANKS_PER_BASE 2
#define TANK_TRIGGER 4        /* hostages aboard or saved before any tanks */
#define TANK_SPAWN_DIST 320   /* px from the prison they roll out at */
#define TANK_OFFSCREEN 32     /* px off screen the spawn point must be */
#define TANK_SPAWN_GAP 60     /* frames between tanks rolling out */
#define TANK_LEASH 100        /* px from the prison */
#define TANK_SPACING 45       /* px behind another tank */
#define TANK_SPEED ONE_PIXEL
#define TANK_REBUILD 300      /* frames a prison waits after losing a tank */
#define TANK_FIRST_SHOT 20
#define TANK_SHELLS 2         /* in the air at once */

/* --- Balloon -------------------------------------------------------------- */
#define BALLOON_TRIGGER 16    /* hostages out of the prisons */
#define BALLOON_RESPAWN 300
#define BALLOON_START 60      /* px above landed height, its middle */
#define BALLOON_FLOOR 32      /* lowest it comes, px above landed height */
#define BALLOON_SPEED_X ONE_PIXEL
#define BALLOON_SPEED_Y 8

/* --- Jet ------------------------------------------------------------------ */
#define JET_TRIGGER 24        /* hostages out of the prisons */
#define JET_GROUND_WAIT 120   /* frames landed before a bomber may come */
#define JET_AIR_WAIT 240      /* frames up high before a fighter may come */
#define JET_AIR_ZONE 75       /* "up high": chopper's top above this screen row */
#define JET_SPEED TO_SUB(4)
#define JET_CLIMB 2           /* px per frame, leaving */
#define JET_BOMBER_HEIGHT 80  /* px above landed height */
#define JET_DROP_LEAD 68      /* px ahead of the jet's middle, +-10 */
#define JET_BOMB_SPEED TO_SUB(2)
#define JET_SHOT_RANGE 100
#define JET_SHOT_SPEED TO_SUB(6)

typedef struct
{
    bool active;
    int32_t x; /* subpixels, left edge */
    int8_t dir;
    bool moving;
    uint8_t base;
    uint8_t cooldown;
    uint8_t anim;
    int8_t turret; /* -1 up-left, 0 up, 1 up-right */
} tank_t;

typedef struct
{
    bool active, falling;
    int32_t x, y; /* subpixels: left edge, and its middle */
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
    int32_t x; /* subpixels, left edge */
    int16_t y;
    int8_t dir;
} jet_t;

static tank_t tanks[TANKS_ACTIVE];
static uint8_t garage[NUM_COMPOUNDS];
static uint16_t rebuild[NUM_COMPOUNDS];
static bool tanks_triggered;
static uint8_t tank_spawn_timer;
static balloon_t balloon;
static jet_t jet;
static uint16_t loiter_ground, loiter_air;

void enemies_init(void)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++)
        tanks[i].active = false;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        garage[i] = 0;
        rebuild[i] = 0;
    }
    tanks_triggered = false;
    tank_spawn_timer = 0;
    balloon.active = false;
    balloon.respawn = 0;
    jet.state = JET_OFF;
    loiter_ground = loiter_air = 0;
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

/* Is world x (an object w wide) at least `margin` px off screen? */
static bool offscreen(int16_t x, int16_t w, int16_t margin)
{
    int16_t sx = screen_x(x);
    return sx < -w - margin || sx > SCREEN_W + margin;
}

/* --- Tanks ---------------------------------------------------------------- */

/* Shell speeds in subpixels, from straight up to almost level: the
 * original's table, times three. */
static const int8_t aim_vx[5] = {0, 33, 69, 87, 96};
static const int8_t aim_vy[5] = {-96, -90, -69, -39, -15};

static void tank_fire(tank_t *t, int16_t ccx)
{
    int16_t ox = FROM_SUB(t->x) + TANK_W / 2;
    int16_t oy = TANK_Y + 4;
    /* Aim 32 px above the chopper's top: the shell drops on the way. */
    int16_t dx = abs(ccx - ox);
    int16_t dy = oy - (FROM_SUB(chopper_y) - 32);
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
    ebullet_spawn(ox - 4, oy - 2, ccx > ox ? aim_vx[a] : -aim_vx[a], aim_vy[a], EB_FLAK);
    sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
}

static void update_tanks(int16_t ccx, bool safe)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
        if (rebuild[i])
            rebuild[i]--;

    /* Once 4 hostages are aboard or saved, every garage gets two. */
    if (!tanks_triggered && saved_count + cargo_count >= TANK_TRIGGER) {
        tanks_triggered = true;
        for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
            garage[i] = TANKS_PER_BASE;
    }
    uint8_t b = nearest_base(ccx);

    /* The nearest prison rolls one out: on its left if it has none there,
     * else on its right, and only out of sight. */
    if (tank_spawn_timer)
        tank_spawn_timer--;
    if (tanks_triggered && !safe && garage[b] && !rebuild[b] && !tank_spawn_timer) {
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
            int16_t x = (!left ? base_x(b) - TANK_SPAWN_DIST : base_x(b) + TANK_SPAWN_DIST) - TANK_W / 2;
            if (x < 0)
                x = 0;
            if (x > WORLD_W_PX - TANK_W)
                x = WORLD_W_PX - TANK_W;
            if (offscreen(x, TANK_W, TANK_OFFSCREEN)) {
                slot->active = true;
                slot->base = b;
                slot->x = TO_SUB(x);
                slot->dir = !left ? 1 : -1;
                slot->cooldown = TANK_FIRST_SHOT;
                slot->anim = 0;
                slot->turret = 0;
                garage[b]--;
                tank_spawn_timer = TANK_SPAWN_GAP;
            }
        }
    }

    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active)
            continue;
        int16_t tx = FROM_SUB(t->x);
        /* Another prison is nearest now: home to the garage (once out of
         * sight, so it doesn't vanish in view). */
        if (t->base != b && offscreen(tx, TANK_W, 0)) {
            t->active = false;
            garage[t->base]++;
            continue;
        }
        int16_t tcx = tx + TANK_W / 2;
        int16_t from_base = tcx - base_x(t->base);
        int16_t to_chopper = ccx - tcx;
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
        t->moving = want != 0;
        if (want) {
            t->dir = want;
            t->x += want * TANK_SPEED;
            t->anim++;
        }
        t->turret = to_chopper > 20 ? 1 : (to_chopper < -20 ? -1 : 0);

        /* On screen, a 2% chance a frame once reloaded; two shells at most. */
        if (t->cooldown) {
            t->cooldown--;
        } else if (!safe && screen_x(tx) > -20 && screen_x(tx) < SCREEN_W + 20 - TANK_W && rng_range8(0, 99) < 2 &&
                   ebullets_of(EB_FLAK) < TANK_SHELLS) {
            tank_fire(t, ccx);
            t->cooldown = rng_range8(30, 59);
        }
    }
}

void tanks_bomb(int16_t x)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active || abs(x - (FROM_SUB(t->x) + TANK_W / 2)) >= 20)
            continue;
        /* Back into its prison's garage; the prison waits a while. */
        t->active = false;
        garage[t->base]++;
        rebuild[t->base] = TANK_REBUILD;
        add_score(200);
        explosion_spawn(FROM_SUB(t->x) + TANK_W / 2, TANK_Y + 8, true);
        return;
    }
}

/* --- The balloon ---------------------------------------------------------- */

static void update_balloon(int16_t ccx, int16_t ccy)
{
    balloon_t *b = &balloon;
    int32_t floor_y = GROUND_Y_SUB - TO_SUB(BALLOON_FLOOR);
    if (!b->active) {
        if (b->respawn) {
            b->respawn--;
            return;
        }
        if (compounds_freed() < BALLOON_TRIGGER)
            return;
        /* 64 px off screen, left or right, never east of the safety line. */
        int16_t cam = FROM_SUB(camera_x);
        int16_t left = cam - 64 - BALLOON_W, right = cam + SCREEN_W + 64;
        int16_t x;
        if (rng_next() & 1)
            x = right < SAFE_LINE ? right : left;
        else
            x = left > 0 ? left : right;
        if (x < 0 || x >= SAFE_LINE)
            return;
        b->active = true;
        b->falling = false;
        b->x = TO_SUB(x);
        b->y = GROUND_Y_SUB - TO_SUB(BALLOON_START);
        return;
    }

    int16_t bx = FROM_SUB(b->x) + BALLOON_W / 2;
    if (b->falling) {
        b->vy += 2;
        b->y += b->vy;
        if (FROM_SUB(b->y) + BALLOON_H / 2 >= GROUND_LINE) {
            explosion_spawn(bx, GROUND_LINE - 12, true);
            b->active = false;
            b->respawn = BALLOON_RESPAWN;
        }
        return;
    }

    /* After the chopper's middle, but back west of the safety line, and
     * never below its floor. */
    if (bx > SAFE_LINE)
        b->x -= BALLOON_SPEED_X;
    else
        b->x += bx < ccx ? BALLOON_SPEED_X : -BALLOON_SPEED_X;
    b->y += FROM_SUB(b->y) < ccy ? BALLOON_SPEED_Y : -BALLOON_SPEED_Y;
    if (b->y > floor_y)
        b->y = floor_y;

    int16_t by = FROM_SUB(b->y);
    if (player_alive() && abs(bx - ccx) < 18 && abs(by - ccy) < 18) {
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
    if (abs(x - (FROM_SUB(b->x) + BALLOON_W / 2)) >= 10 || abs(y - FROM_SUB(b->y)) >= 18)
        return false;
    b->falling = true;
    b->vy = ONE_PIXEL;
    add_score(150);
    small_explosion_spawn(x, y);
    sfx_enemy(SFX_EXPLODE, SFX_PRI_DESTROY);
    return true;
}

/* --- The jet -------------------------------------------------------------- */

static void update_jet(int16_t ccx, bool safe)
{
    jet_t *j = &jet;
    if (j->state == JET_OFF) {
        if (compounds_freed() < JET_TRIGGER)
            return;
        if (safe) {
            loiter_ground = loiter_air = 0;
            return;
        }
        bool go = false;
        if (chopper_y >= GROUND_Y_SUB) {
            if (++loiter_ground > JET_GROUND_WAIT && rng_range8(0, 99) < 2) {
                go = true;
                j->bomber = true;
            }
        } else {
            loiter_ground = 0;
        }
        if (FROM_SUB(chopper_y) < JET_AIR_ZONE) {
            if (++loiter_air > JET_AIR_WAIT && rng_range8(0, 99) < 2) {
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
        j->x = j->dir > 0 ? camera_x - TO_SUB(JET_W) : camera_x + TO_SUB(SCREEN_W);
        j->y = j->bomber ? GROUND_Y - JET_BOMBER_HEIGHT : FROM_SUB(chopper_y) + CHOPPER_H / 2 - JET_H / 2;
        sfx_enemy(SFX_JET_FLYBY, SFX_PRI_EVENT);
        return;
    }

    j->x += j->dir * JET_SPEED;
    int16_t jx = FROM_SUB(j->x);
    int16_t jcx = jx + JET_W / 2;
    int16_t ahead = (ccx - jcx) * j->dir; /* how far the chopper is in front */

    if (j->state == JET_ATTACK) {
        if (j->bomber) {
            if (ahead > JET_DROP_LEAD - 10 && ahead < JET_DROP_LEAD + 10) {
                ebullet_spawn(jcx - 4, j->y + JET_H / 2, j->dir * JET_BOMB_SPEED, 0, EB_BOMB);
                sfx_enemy(SFX_BOMB_DROP, SFX_PRI_EVENT);
                j->state = JET_LEAVE;
            }
        } else if (abs(ahead) < JET_SHOT_RANGE) {
            ebullet_spawn(j->dir > 0 ? jx + JET_W - 4 : jx - 4, j->y + JET_H / 2 - 2, j->dir * JET_SHOT_SPEED, 0,
                          EB_SHOT);
            sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
            j->state = JET_LEAVE;
        }
    } else {
        j->y -= JET_CLIMB;
    }
    int16_t sx = screen_x(jx);
    if (sx < -JET_W - 8 || sx > SCREEN_W + 8 || j->y < HUD_H - JET_H)
        j->state = JET_OFF;
}

bool jets_check_hit(int16_t x, int16_t y)
{
    jet_t *j = &jet;
    if (j->state == JET_OFF)
        return false;
    int16_t jcx = FROM_SUB(j->x) + JET_W / 2;
    if (abs(x - jcx) >= 12 + (JET_W - 16) / 2 || abs(y - (j->y + JET_H / 2)) >= 8)
        return false;
    j->state = JET_OFF;
    add_score(300);
    explosion_spawn(jcx, j->y + JET_H / 2, true);
    return true;
}

/* --------------------------------------------------------------------------- */

void enemies_update(void)
{
    int16_t ccx = chopper_cx();
    int16_t ccy = FROM_SUB(chopper_y) + CHOPPER_H / 2;
    bool safe = ccx > SAFE_LINE;
    update_tanks(ccx, safe);
    update_balloon(ccx, ccy);
    update_jet(ccx, safe);
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
        /* The sprite faces left with its gun raised forward; flip it to
         * aim right. Straight up uses the raised-gun frames. */
        bool right = t->turret ? t->turret > 0 : t->dir > 0;
        uint8_t f = (t->turret ? 0 : 2) + ((t->anim >> 3) & 1);
        spr_place(SPR_TANK_START + i, XRAM_IMG_TANK + f * TANK_FRAME_BYTES, PAL_TANK, WH(TANK_W, TANK_H),
                  right ? OPT4_FLIP : OPT4, FROM_SUB(t->x) - cam, TANK_Y);
    }

    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        if (i || !balloon.active) {
            spr_hide(SPR_BALLOON_START + i);
            continue;
        }
        uint8_t f = balloon.falling ? (frame_count >> 1) % 3 : (frame_count >> 3) % 3;
        spr_place(SPR_BALLOON_START, XRAM_IMG_BALLOON + f * BALLOON_FRAME_BYTES, PAL_BALLOON,
                  WH(BALLOON_W, BALLOON_H), OPT4, FROM_SUB(balloon.x) - cam, FROM_SUB(balloon.y) - BALLOON_H / 2);
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
