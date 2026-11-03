#include <rp6502.h>
#include <stdlib.h>
#include "compounds.h"
#include "enemies.h"
#include "game.h"
#include "hud.h"
#include "input.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "weather.h"
#include "xram.h"

/* The rules are the original game's: see docs/ORIGINAL_GAMEPLAY.md.
 * Heights "above landed height" are measured up from GROUND_Y. */

/* --- Tanks ---------------------------------------------------------------- */
#define TANKS_ACTIVE 2        /* moving and shown at once, out of all the zones' */
#define TANKS_PER_BASE 2      /* each prison's zone has two */
#define TANK_SPAWN_DIST 300   /* px from the prison they roll out at, just out of sight */
#define TANK_SPAWN_GAP 180    /* frames between a prison's tanks rolling out (60 in the original) */
#define TANK_TRAVEL 90        /* frames from rolling out to coming into view (measured) */
#define TANK_OFFSCREEN 16     /* px off screen to roll out, wake or go dormant */
#define TANK_RANGE 520        /* px from the chopper within which a rolled-out tank is awake */
#define TANK_ZONE 200         /* px either side of its prison: a tank never leaves this */
#define TANK_PATROL 140       /* px either side of its prison it patrols */
#define TANK_SPOT 180         /* px: how near the chopper must be for a tank to see it */
#define TANK_LOSE 120         /* frames out of sight before a tank gives up the chase */
#define TANK_RESUME 12        /* px the chopper must move off before a parked tank follows */
#define TANK_SPACING 45       /* px behind another tank */
#define TANK_SPEED ONE_PIXEL  /* chasing, or driving back into its zone */
#define TANK_PATROL_SPEED 8   /* subpixels per frame */
#define TANK_REBUILD 300      /* frames before a prison can roll out a replacement */
#define TANK_FIRST_SHOT 40    /* frames a tank holds fire after coming into view (20 in the original) */
#define TANK_FIRE_RANGE 120   /* px: it only fires at a chopper this close */
#define TANK_SHELLS 3         /* in the air at once (2 in the original) */
#define TANK_FIRE_CHANCE 4    /* percent a frame, once reloaded (2 in the original) */
#define TANK_RELOAD_MIN 24    /* frames (30-59 in the original) */
#define TANK_RELOAD_SPREAD 24

/* --- Balloon -------------------------------------------------------------- */
#define BALLOON_TRIGGER 24    /* hostages out of the prisons (16 in the original) */
#define BALLOON_OFFSCREEN 128 /* px off screen it appears (64 in the original) */
#define BALLOON_BACKOFF 80    /* px it backs off west from the border before coming back */
#define BALLOON_RESPAWN 300
#define BALLOON_START 60      /* px above landed height, its middle */
#define BALLOON_FLOOR 32      /* lowest it comes, px above landed height */
#define BALLOON_SPEED_X ONE_PIXEL
#define BALLOON_SPEED_Y 8

/* --- Jet ------------------------------------------------------------------ */
#define JET_TRIGGER 3         /* prisons opened (the original: 24 hostages out) */
#define JET_WARN_TIME 90      /* frames of warning before a jet arrives */
#define JET_GROUND_WAIT 120   /* frames landed before a bomber may come */
#define JET_AIR_WAIT 180      /* frames up high before a fighter may come */
#define JET_AIR_ZONE 85       /* "up high": chopper's top above this screen row */
#define JET_SPEED TO_SUB(4)
#define JET_CLIMB 2           /* px per frame, leaving */
#define JET_BOMBER_HEIGHT 80  /* px above landed height */
#define JET_STICK 3           /* bombs in a stick, JET_STICK_GAP frames apart */
#define JET_STICK_GAP 4
#define JET_BOMB_SPEED TO_SUB(2)
#define JET_SHOT_RANGE 100
#define JET_SHOT_SPEED TO_SUB(6)

/* Every prison's tanks, all the time. A tank is in its prison's garage,
 * out in its zone, or a wreck waiting to be rebuilt. Out in its zone it
 * patrols until it sees the chopper, chases it (never out of the zone),
 * and goes back to patrolling once it loses it. */
enum
{
    T_GARAGE,
    T_OUT,
    T_WRECK
};
enum
{
    M_PATROL,
    M_CHASE,
    M_RETURN /* outside its zone, as when it has just rolled out: drive back in */
};

typedef struct
{
    uint8_t state;
    uint8_t mode;
    bool awake;    /* one of the active tanks just now */
    int16_t x;     /* left edge, while dormant */
    int8_t dir;
    int8_t patrol; /* which way its patrol is heading */
    uint8_t lost;  /* frames since it last saw the chopper */
    uint16_t rebuild;
} zone_tank_t;

/* The tanks moving and shown: TANKS_ACTIVE of them, picked from the zones. */
typedef struct
{
    bool active;
    int32_t x; /* subpixels, left edge */
    bool moving;
    uint8_t base, slot; /* whose: zone[base][slot] */
    uint8_t cooldown;
    uint8_t anim;
    int8_t turret; /* -1 up-left, 0 up, 1 up-right */
    bool in_view;  /* on screen: its hold on firing starts when it comes in */
} tank_t;

typedef struct
{
    bool active, falling;
    int32_t x, y; /* subpixels: left edge, and its middle */
    int16_t vy;
    int8_t dir;   /* which way it is pushing: the sprite faces that way */
    bool retreat; /* backing off from the border */
    uint16_t respawn;
} balloon_t;

enum
{
    JET_OFF,
    JET_WARN,   /* on its way: a marker blinks at the edge it will come from */
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
    uint8_t timer;
    uint8_t bombs; /* dropped so far in this run's stick */
} jet_t;

static tank_t tanks[TANKS_ACTIVE];
static zone_tank_t zone[NUM_COMPOUNDS][TANKS_PER_BASE];
static uint16_t roll_timer[NUM_COMPOUNDS];
static bool opened[NUM_COMPOUNDS]; /* seen breached, so its tanks are due */

/* How long after each prison is opened, in order, its first tank comes into
 * view: longest at the first prison, quicker later on. */
static const uint16_t first_tank[NUM_COMPOUNDS] = {8 * 60, 6 * 60, 5 * 60, 5 * 60};
static balloon_t balloon;
static jet_t jet;
static uint16_t loiter_ground, loiter_air;
static bool radar_warned;

void enemies_init(void)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++)
        tanks[i].active = false;
    for (uint8_t b = 0; b < NUM_COMPOUNDS; b++) {
        roll_timer[b] = 0;
        opened[b] = false;
        for (uint8_t k = 0; k < TANKS_PER_BASE; k++) {
            zone[b][k].state = T_GARAGE;
            zone[b][k].awake = false;
        }
    }

    balloon.active = false;
    balloon.respawn = 0;
    jet.state = JET_OFF;
    loiter_ground = loiter_air = 0;
    radar_warned = false;
}

static int16_t base_x(uint8_t b)
{
    return DOOR_X(b) + DOOR_W * 8;
}

/* Is world x (an object w wide) at least `margin` px off screen? */
static bool offscreen(int16_t x, int16_t w, int16_t margin)
{
    int16_t sx = screen_x(x);
    return sx < -w - margin || sx > SCREEN_W + margin;
}

/* --- Tanks ---------------------------------------------------------------- */

/* Shell launches in subpixels, from straight up down to 20 degrees, all at
 * the same speed: the steepest climbs about 110 px (v * v / (2 *
 * FLAK_GRAVITY) subpixels). (The original's five were faster and climbed
 * 144 px, too high for this game's sky.) */
#define AIMS 8
static const int8_t aim_vx[AIMS] = {0, 15, 29, 42, 54, 64, 73, 79};
static const int8_t aim_vy[AIMS] = {-84, -83, -79, -73, -64, -54, -42, -29};

/* Fire at the chopper: try each launch, flying it until it climbs to the
 * chopper's height, and pick the one that gets there closest to where the
 * chopper will be by then (going the way it is going, wind and all). If none can climb that high, lob the steepest
 * anyway; it falls short. */
static void tank_fire(tank_t *t, int16_t ccx)
{
    int16_t ox = FROM_SUB(t->x) + TANK_W / 2;
    int16_t oy = TANK_Y + 4;
    ccx += (int16_t)(rng_next() % 13) - 6; /* not quite dead on */
    int8_t side = ccx >= ox ? 1 : -1;
    /* Everything in subpixels from the muzzle, small enough for 16 bits:
     * the target starts where the chopper's middle is and moves as it does. */
    int16_t tx0 = (ccx - ox) * ONE_PIXEL;
    int16_t ty0 = (int16_t)(chopper_y - TO_SUB(oy)) + TO_SUB(CHOPPER_H / 2);
    int8_t cvx = (int8_t)(chopper_vel_x + (chopper_is_landed ? 0 : wind));
    int8_t cvy = (int8_t)(chopper_vel_y + (chopper_is_landed ? 0 : lift));
    uint8_t best = 1;
    int16_t best_err = 0x7FFF;
    for (uint8_t a = 0; a < AIMS; a++) {
        int16_t x = 0, y = 0, tx = tx0, ty = ty0;
        int16_t vy = aim_vy[a];
        int16_t vx = side * aim_vx[a];
        while (vy < 0) { /* until it tops out */
            x += vx;
            y += vy;
            vy += FLAK_GRAVITY;
            tx += cvx;
            ty += cvy;
            if (y <= ty) {
                int16_t err = abs(x - tx);
                if (err < best_err) {
                    best_err = err;
                    best = a;
                }
                break;
            }
        }
    }
    ebullet_spawn(ox - 4, oy - 2, side * aim_vx[best], aim_vy[best], EB_FLAK);
    sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
}

static uint8_t nearest_base(int16_t x)
{
    uint8_t best = 0;
    for (uint8_t i = 1; i < NUM_COMPOUNDS; i++)
        if (abs(base_x(i) - x) < abs(base_x(best) - x))
            best = i;
    return best;
}

/* An active tank's zone tank goes back to waiting where it is. */
static void tank_sleep(tank_t *t)
{
    zone_tank_t *z = &zone[t->base][t->slot];
    z->x = FROM_SUB(t->x);
    z->awake = false;
    t->active = false;
}

/* Prisons roll their tanks out of the garage once they have been opened,
 * on a schedule: the first tank comes into view first_tank[] after the
 * prison is opened, the second TANK_SPAWN_GAP later. They come from just
 * out of sight, on whichever side has none yet, and only from the prison
 * nearest the chopper. A rebuilt tank rolls out the same way. */
static void roll_out(int16_t ccx, bool safe)
{
    for (uint8_t b = 0; b < NUM_COMPOUNDS; b++) {
        if (!opened[b] && compounds[b].breached) {
            opened[b] = true;
            roll_timer[b] = first_tank[compounds_breached() - 1] - TANK_TRAVEL;
        }
        if (roll_timer[b])
            roll_timer[b]--;
        for (uint8_t k = 0; k < TANKS_PER_BASE; k++) {
            zone_tank_t *z = &zone[b][k];
            if (z->state == T_WRECK && !--z->rebuild)
                z->state = T_GARAGE;
        }
    }
    uint8_t b = nearest_base(ccx);
    if (safe || !opened[b] || roll_timer[b])
        return;
    bool west = false;
    zone_tank_t *z = 0;
    for (uint8_t k = 0; k < TANKS_PER_BASE; k++) {
        zone_tank_t *t = &zone[b][k];
        if (t->state == T_GARAGE) {
            if (!z)
                z = t;
        } else if (t->state == T_OUT && t->x + TANK_W / 2 < base_x(b)) {
            west = true;
        }
    }
    if (!z)
        return;
    /* On the side the chopper isn't looking at, if it can. */
    int16_t x = (!west ? base_x(b) - TANK_SPAWN_DIST : base_x(b) + TANK_SPAWN_DIST) - TANK_W / 2;
    if (x < 0)
        x = 0;
    if (x > SAFE_LINE - TANK_W - 8)
        x = SAFE_LINE - TANK_W - 8; /* never on the home side of the border */
    if (!offscreen(x, TANK_W, TANK_OFFSCREEN))
        return;
    z->state = T_OUT;
    z->mode = M_RETURN;
    z->awake = false;
    z->x = x;
    z->dir = x < base_x(b) ? 1 : -1;
    z->patrol = z->dir;
    z->lost = 0;
    roll_timer[b] = TANK_SPAWN_GAP;
}

/* Wake the nearest dormant tanks out in their zones, put far ones to
 * sleep; only ever out of sight, so none pops in or out of view. */
static void wake_and_sleep(int16_t ccx)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        int16_t tx = FROM_SUB(t->x);
        if (t->active && abs(tx + TANK_W / 2 - ccx) > TANK_RANGE + 64 && offscreen(tx, TANK_W, TANK_OFFSCREEN))
            tank_sleep(t);
    }
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (t->active)
            continue;
        zone_tank_t *best = 0;
        uint8_t bb = 0, bk = 0;
        int16_t bd = TANK_RANGE;
        for (uint8_t b = 0; b < NUM_COMPOUNDS; b++)
            for (uint8_t k = 0; k < TANKS_PER_BASE; k++) {
                zone_tank_t *z = &zone[b][k];
                if (z->state != T_OUT || z->awake)
                    continue;
                int16_t d = abs(z->x + TANK_W / 2 - ccx);
                if (d < bd && offscreen(z->x, TANK_W, TANK_OFFSCREEN)) {
                    best = z;
                    bd = d;
                    bb = b;
                    bk = k;
                }
            }
        if (!best)
            return;
        best->awake = true;
        t->active = true;
        t->base = bb;
        t->slot = bk;
        t->x = TO_SUB(best->x);
        t->moving = true;
        t->in_view = false;
        t->cooldown = TANK_FIRST_SHOT;
        t->anim = 0;
        t->turret = 0;
    }
}

static void update_tanks(int16_t ccx, bool safe)
{
    /* Nothing to do until a prison has been opened. */
    if (!compounds_breached())
        return;
    roll_out(ccx, safe);
    wake_and_sleep(ccx);

    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active)
            continue;
        zone_tank_t *z = &zone[t->base][t->slot];
        int16_t tx = FROM_SUB(t->x);
        int16_t tcx = tx + TANK_W / 2;
        int16_t home = base_x(t->base);
        int16_t from_base = tcx - home;
        int16_t to_chopper = ccx - tcx;

        /* What it is doing: back into its zone, chasing, or patrolling. */
        bool sees = player_alive() && !safe && abs(to_chopper) < TANK_SPOT && abs(ccx - home) < TANK_ZONE + TANK_SPOT;
        if (z->mode == M_RETURN) {
            if (abs(from_base) <= TANK_ZONE)
                z->mode = sees ? M_CHASE : M_PATROL;
        } else if (sees) {
            z->mode = M_CHASE;
            z->lost = 0;
        } else if (z->mode == M_CHASE && ++z->lost > TANK_LOSE) {
            z->mode = M_PATROL; /* lost it: back to patrolling */
        }

        int16_t target;
        int8_t speed = TANK_SPEED;
        if (z->mode == M_RETURN) {
            target = home;
        } else if (z->mode == M_CHASE) {
            /* Under the chopper, but no further than the edge of its zone. */
            target = ccx;
            if (target > home + TANK_ZONE)
                target = home + TANK_ZONE;
            if (target < home - TANK_ZONE)
                target = home - TANK_ZONE;
        } else {
            /* Back and forth across the middle of its zone, slowly. */
            speed = TANK_PATROL_SPEED;
            if (from_base >= TANK_PATROL)
                z->patrol = -1;
            else if (from_base <= -TANK_PATROL)
                z->patrol = 1;
            target = home + z->patrol * (TANK_PATROL + 8);
        }
        int16_t to_target = target - tcx;
        /* Parked under the chopper until it is a good way off again. */
        int8_t want = to_target > 0 ? 1 : -1;
        if (abs(to_target) < (t->moving ? 4 : (z->mode == M_CHASE ? TANK_RESUME : 4)))
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
            z->dir = want;
            t->x += want * speed;
            t->anim++;
        }
        /* The turret follows the chopper while it chases, with some slack. */
        if (z->mode != M_CHASE)
            t->turret = 0;
        else if (to_chopper > 24)
            t->turret = 1;
        else if (to_chopper < -24)
            t->turret = -1;
        else if (abs(to_chopper) < 16)
            t->turret = 0;

        /* It holds fire for a while each time it comes into view, so the
         * player sees it coming, and then only fires when it is close. */
        bool view = screen_x(tx) > -TANK_W / 2 && screen_x(tx) < SCREEN_W - TANK_W / 2;
        if (view && !t->in_view)
            t->cooldown = TANK_FIRST_SHOT;
        t->in_view = view;
        if (t->cooldown) {
            t->cooldown--;
        } else if (z->mode == M_CHASE && view && abs(to_chopper) < TANK_FIRE_RANGE &&
                   rng_range8(0, 99) < TANK_FIRE_CHANCE && ebullets_of(EB_FLAK) < TANK_SHELLS) {
            tank_fire(t, ccx);
            t->cooldown = TANK_RELOAD_MIN + rng_range8(0, TANK_RELOAD_SPREAD);
        }
    }
}

void tanks_bomb(int16_t x)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active || abs(x - (FROM_SUB(t->x) + TANK_W / 2)) >= 20)
            continue;
        /* A wreck; its prison rebuilds it in a while, and rolls it out
         * again when it is the nearest. */
        zone_tank_t *z = &zone[t->base][t->slot];
        z->state = T_WRECK;
        z->awake = false;
        z->rebuild = TANK_REBUILD;
        t->active = false;
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
        int16_t left = cam - BALLOON_OFFSCREEN - BALLOON_W, right = cam + SCREEN_W + BALLOON_OFFSCREEN;
        int16_t x;
        if (rng_coin())
            x = right < SAFE_LINE ? right : left;
        else
            x = left > 0 ? left : right;
        if (x < 0 || x >= SAFE_LINE)
            return;
        b->active = true;
        b->falling = false;
        b->x = TO_SUB(x);
        b->y = GROUND_Y_SUB - TO_SUB(BALLOON_START);
        b->dir = x < ccx ? 1 : -1;
        b->retreat = false;
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
    /* At the border it backs well off before coming back, so it patrols
     * along it instead of hanging there. */
    if (bx >= SAFE_LINE - BALLOON_W / 2)
        b->retreat = true;
    else if (bx < SAFE_LINE - BALLOON_BACKOFF)
        b->retreat = false;
    if (b->retreat)
        b->dir = -1;
    else if (abs(bx - ccx) > 2)
        b->dir = bx < ccx ? 1 : -1;
    b->x += b->dir * BALLOON_SPEED_X;
    b->y += FROM_SUB(b->y) < ccy ? BALLOON_SPEED_Y : -BALLOON_SPEED_Y;
    if (b->y > floor_y)
        b->y = floor_y;

    int16_t by = FROM_SUB(b->y);
    if (player_alive() && abs(bx - ccx) < 22 && abs(by - ccy) < 18) {
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
    if (abs(x - (FROM_SUB(b->x) + BALLOON_W / 2)) >= 14 || abs(y - FROM_SUB(b->y)) >= 18)
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
        if (compounds_breached() < JET_TRIGGER)
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
            /* Halfway there, a first warning to get low. */
            if (++loiter_air > JET_AIR_WAIT / 2 && !radar_warned) {
                radar_warned = true;
                msg_flash("ENEMY RADAR HAS YOU - GET LOW!", C_ORANGE, 120);
            }
            if (loiter_air > JET_AIR_WAIT && rng_range8(0, 99) < 2) {
                go = true;
                j->bomber = false;
            }
        } else {
            loiter_air = 0;
            radar_warned = false;
        }
        if (!go)
            return;
        loiter_ground = loiter_air = 0;
        radar_warned = false;
        /* It locks onto the chopper's height now and keeps it, so getting
         * out of the way is the answer to the warning. */
        j->state = JET_WARN;
        j->timer = JET_WARN_TIME;
        j->bombs = 0;
        j->dir = rng_coin() ? 1 : -1;
        j->y = j->bomber ? GROUND_Y - JET_BOMBER_HEIGHT : FROM_SUB(chopper_y) + CHOPPER_H / 2 - JET_H / 2;
        msg_flash("JET INBOUND!", C_RED, JET_WARN_TIME);
        sfx_enemy(SFX_WARNING, SFX_PRI_EVENT);
        return;
    }
    if (j->state == JET_WARN) {
        if (--j->timer)
            return;
        j->state = JET_ATTACK;
        j->x = j->dir > 0 ? camera_x - TO_SUB(JET_W) : camera_x + TO_SUB(SCREEN_W);
        sfx_enemy(SFX_JET_FLYBY, SFX_PRI_EVENT);
        return;
    }

    j->x += j->dir * JET_SPEED;
    int16_t jx = FROM_SUB(j->x);
    int16_t jcx = jx + JET_W / 2;
    int16_t ahead = (ccx - jcx) * j->dir; /* how far the chopper is in front */

    if (j->state == JET_ATTACK) {
        if (j->bomber) {
            /* It works out how long a bomb takes to fall to the chopper and
             * how far it carries meanwhile, and lets go of a stick of bombs
             * spread either side of where the chopper will be. */
            if (!j->bombs) {
                int32_t drop = (chopper_y + TO_SUB(CHOPPER_H / 2)) - TO_SUB(j->y + JET_H / 2 + 6);
                int32_t fall = 0;
                int16_t v = 0;
                uint8_t n = 0;
                while (fall < drop && n < 120) {
                    fall += v;
                    v += JET_BOMB_GRAVITY;
                    n++;
                }
                int16_t carry = FROM_SUB((int32_t)JET_BOMB_SPEED * n);
                int16_t lead = (FROM_SUB((int32_t)chopper_vel_x * n)) * j->dir;
                /* Each bomb lands where the jet was when it let go, plus
                 * the carry, so the stick is spaced by how far the jet
                 * flies between them: the first lands one gap short of the
                 * chopper, the middle one on it, the last one gap past. */
                int16_t gap = FROM_SUB(JET_SPEED) * JET_STICK_GAP;
                if (ahead + lead <= carry + gap)
                    j->timer = 0, j->bombs = 1;
            } else {
                j->timer++;
            }
            if (j->bombs && j->timer % JET_STICK_GAP == 0) {
                ebullet_spawn(jcx - 4, j->y + JET_H / 2, j->dir * JET_BOMB_SPEED, 0, EB_BOMB);
                if (j->bombs == 1)
                    sfx_enemy(SFX_BOMB_DROP, SFX_PRI_EVENT);
                if (++j->bombs > JET_STICK)
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
    if (j->state == JET_OFF || j->state == JET_WARN)
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
    uint16_t flag = XRAM_IMG_FLAGS + ((frame_count >> 3) & 3) * FLAGS_FRAME_BYTES;
    spr_place(SPR_FLAG, flag, PAL_FLAG, WH(24, 16), OPT4, FLAG_X - cam, FLAG_Y);
    /* The border flag ripples a beat behind the one at home. */
    flag = XRAM_IMG_FLAGS + (((frame_count >> 3) + 2) & 3) * FLAGS_FRAME_BYTES;
    spr_place(SPR_BORDER_FLAG, flag, PAL_FLAG, WH(24, 16), OPT4, BORDER_FLAG_X - cam, FLAG_Y);

    for (uint8_t i = 0; i < SPR_TANK_COUNT; i++) {
        tank_t *t = &tanks[i];
        if (i >= TANKS_ACTIVE || !t->active) {
            spr_hide(SPR_TANK_START + i);
            continue;
        }
        /* The sprite faces left with its gun raised forward; flip it to
         * aim right. Straight up uses the raised-gun frames. */
        bool right = t->turret ? t->turret > 0 : zone[t->base][t->slot].dir > 0;
        uint8_t f = (t->turret ? 0 : 2) + ((t->anim >> 3) & 1);
        spr_place(SPR_TANK_START + i, XRAM_IMG_TANK + f * TANK_FRAME_BYTES, PAL_TANK, WH(TANK_W, TANK_H),
                  right ? OPT4_FLIP : OPT4, FROM_SUB(t->x) - cam, TANK_Y);
    }

    for (uint8_t i = 0; i < SPR_BALLOON_COUNT; i++) {
        if (i || !balloon.active) {
            spr_hide(SPR_BALLOON_START + i);
            continue;
        }
        uint8_t f = balloon.falling ? 1 : (frame_count >> 2) % 3; /* a dead one's engine stops */
        spr_place(SPR_BALLOON_START, XRAM_IMG_BALLOON + f * BALLOON_FRAME_BYTES, PAL_BALLOON,
                  WH(BALLOON_W, BALLOON_H), balloon.dir > 0 ? OPT4_FLIP : OPT4, FROM_SUB(balloon.x) - cam,
                  FROM_SUB(balloon.y) - BALLOON_H / 2);
    }

    /* The warning: a reticle blinking at the screen edge the jet will come
     * from, at the height it will fly. */
    if (jet.state == JET_WARN && (frame_count & 8))
        spr_place(SPR_JET_START + 1, XRAM_IMG_TARGET + ((frame_count >> 2) & 1) * TARGET_FRAME_BYTES, PAL_TARGET,
                  WH(16, 16), OPT4, jet.dir > 0 ? 2 : SCREEN_W - 18, jet.y + JET_H / 2 - 8);
    else
        spr_hide(SPR_JET_START + 1);
    for (uint8_t i = 0; i < SPR_JET_COUNT; i++) {
        if (i)
            continue;
        if (jet.state == JET_OFF || jet.state == JET_WARN) {
            spr_hide(SPR_JET_START + i);
            continue;
        }
        spr_place(SPR_JET_START, XRAM_IMG_JET + ((frame_count >> 1) & 1) * JET_FRAME_BYTES, PAL_JET,
                  WH(JET_W, JET_H), jet.dir > 0 ? OPT4_FLIP : OPT4, FROM_SUB(jet.x) - cam, jet.y);
    }
}
