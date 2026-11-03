#include <rp6502.h>
#include <stdlib.h>
#include "compounds.h"
#include "enemies.h"
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "input.h"
#include "level.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "weather.h"
#include "xram.h"

/* The rules are the original game's: see docs/ORIGINAL_GAMEPLAY.md.
 * Heights "above landed height" are measured up from GROUND_Y.
 *
 * Level 2 (the lakes) swaps the enemies: jeeps for tanks (the same zones
 * and patrols, faster, firing machine-gun bursts, and the cannon kills
 * them), rocket turrets for the balloon, and worms for the jet. */

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
#define TANK_FIRST_SHOT 60    /* frames a tank holds fire after coming into view (20 in the original) */
#define TANK_FIRE_RANGE 120   /* px: it only fires at a chopper this close */
#define TANK_SHELLS 3         /* in the air at once (2 in the original) */
#define TANK_FIRE_CHANCE 4    /* percent a frame, once reloaded (2 in the original) */
#define TANK_RELOAD_MIN 24    /* frames (30-59 in the original) */
#define TANK_RELOAD_SPREAD 24

/* --- Jeeps (level 2), where they differ from tanks ------------------------ */
#define JEEP_Y (GROUND_LINE - JEEP_H + 2)
#define JEEP_SPEED 24         /* subpixels per frame, chasing: 1.5 px */
#define JEEP_PATROL_SPEED 16  /* driving to its post */
#define JEEP_POST 140         /* px either side of its prison it waits, parked */
#define JEEP_FIRE_RANGE 100    /* px across from the chopper */
#define JEEP_REACH 100         /* px up to the chopper's middle: its rounds (MG_LIFE) go no further */
#define JEEP_BURST 3          /* rounds a burst */
#define JEEP_BURST_GAP 5      /* frames between them */
#define JEEP_ROUND_SPEED 64   /* subpixels per frame */
#define JEEP_RELOAD_MIN 50
#define JEEP_RELOAD_SPREAD 40

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
    uint8_t burst; /* a jeep's rounds still to fire in this burst */
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

/* Tanks, or jeeps on level 2: their size and pace. */
static bool boreal;
static uint8_t vw;       /* width */
static int16_t veh_y;    /* top */
static int8_t veh_speed, veh_patrol;
static balloon_t balloon;
static jet_t jet;
static uint16_t loiter_ground, loiter_air;
static bool radar_warned;

static void turrets_init(void);
static void worm_init(void);

void enemies_init(void)
{
    boreal = level_theme == THEME_BOREAL;
    vw = boreal ? JEEP_W : TANK_W;
    veh_y = boreal ? JEEP_Y : TANK_Y;
    veh_speed = boreal ? JEEP_SPEED : TANK_SPEED;
    veh_patrol = boreal ? JEEP_PATROL_SPEED : TANK_PATROL_SPEED;
    turrets_init();
    worm_init();
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
    int16_t ox = FROM_SUB(t->x) + vw / 2;
    int16_t oy = veh_y + 4;
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

/* A jeep fires bursts from its machine gun, straight at the chopper, but
 * its rounds don't carry far: a chopper well up is out of reach. */
static void jeep_fire(tank_t *t, bool view, bool chasing, int16_t to_chopper, int16_t ccx)
{
    if (t->burst) {
        if (--t->cooldown)
            return;
        int16_t ox = FROM_SUB(t->x) + vw / 2;
        int16_t oy = JEEP_Y;
        int16_t dx = ccx + (int16_t)(rng_next() % 9) - 4 - ox;
        int16_t dy = FROM_SUB(chopper_y) + CHOPPER_H / 2 - oy;
        int16_t ax = abs(dx), ay = abs(dy);
        int16_t len = (ax > ay ? ax + ay / 2 : ay + ax / 2) + 1; /* about the distance */
        ebullet_spawn(ox - 4, oy - 2, dx * JEEP_ROUND_SPEED / len, dy * JEEP_ROUND_SPEED / len, EB_MG);
        sfx_enemy(SFX_VULCAN, SFX_PRI_FIRE);
        if (--t->burst)
            t->cooldown = JEEP_BURST_GAP;
        else
            t->cooldown = JEEP_RELOAD_MIN + rng_range8(0, JEEP_RELOAD_SPREAD);
        return;
    }
    if (t->cooldown) {
        t->cooldown--;
        return;
    }
    int16_t dy = veh_y - (FROM_SUB(chopper_y) + CHOPPER_H / 2);
    if (chasing && view && abs(to_chopper) < JEEP_FIRE_RANGE && dy < JEEP_REACH &&
        rng_range8(0, 99) < TANK_FIRE_CHANCE) {
        t->burst = JEEP_BURST;
        t->cooldown = 1;
    }
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

/* Where prison b rolls a tank out, west or east of it, just out of sight. */
static int16_t spawn_x(uint8_t b, bool west)
{
    int16_t x = (west ? base_x(b) - TANK_SPAWN_DIST : base_x(b) + TANK_SPAWN_DIST) - vw / 2;
    if (x < 0)
        x = 0;
    if (x > SAFE_LINE - vw - 8)
        x = SAFE_LINE - vw - 8; /* never on the home side of the border */
    return x;
}

/* Prisons roll their tanks out of the garage once they have been opened,
 * on a schedule: the first tank comes into view level->first_vehicle[] after the
 * prison is opened, the second TANK_SPAWN_GAP later. They come from just
 * out of sight, on whichever side has none yet, and only from the prison
 * nearest the chopper. A rebuilt tank rolls out the same way. */
static void roll_out(int16_t ccx, bool safe)
{
    for (uint8_t b = 0; b < NUM_COMPOUNDS; b++) {
        if (!opened[b] && compounds[b].breached) {
            opened[b] = true;
            roll_timer[b] = level->first_vehicle[compounds_breached() - 1] - TANK_TRAVEL;
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
        } else if (t->state == T_OUT && t->x + vw / 2 < base_x(b)) {
            west = true;
        }
    }
    if (!z)
        return;
    /* West of the prison if none of its tanks is there yet, else east;
     * and east if the spot in the west is in view. */
    int16_t x = spawn_x(b, !west);
    if (!offscreen(x, vw, TANK_OFFSCREEN)) {
        x = spawn_x(b, false);
        if (west || !offscreen(x, vw, TANK_OFFSCREEN))
            return;
    }
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
        if (t->active && abs(tx + vw / 2 - ccx) > TANK_RANGE + 64 && offscreen(tx, vw, TANK_OFFSCREEN))
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
                int16_t d = abs(z->x + vw / 2 - ccx);
                if (d < bd && offscreen(z->x, vw, TANK_OFFSCREEN)) {
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
        t->burst = 0;
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
        int16_t tcx = tx + vw / 2;
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
        int8_t speed = veh_speed;
        if (z->mode == M_RETURN) {
            target = home;
        } else if (z->mode == M_CHASE) {
            /* Under the chopper, but no further than the edge of its zone. */
            target = ccx;
            if (target > home + TANK_ZONE)
                target = home + TANK_ZONE;
            if (target < home - TANK_ZONE)
                target = home - TANK_ZONE;
        } else if (boreal) {
            /* A jeep waits parked at its post, on its side of the prison,
             * until it sees the chopper. */
            speed = veh_patrol;
            target = home + (from_base < 0 ? -JEEP_POST : JEEP_POST);
        } else {
            /* Back and forth across the middle of its zone, slowly. */
            speed = veh_patrol;
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
        bool view = screen_x(tx) > -vw / 2 && screen_x(tx) < SCREEN_W - vw / 2;
        if (view && !t->in_view)
            t->cooldown = TANK_FIRST_SHOT;
        t->in_view = view;
        if (boreal) {
            jeep_fire(t, view, z->mode == M_CHASE, to_chopper, ccx);
        } else if (t->cooldown) {
            t->cooldown--;
        } else if (z->mode == M_CHASE && view && abs(to_chopper) < TANK_FIRE_RANGE &&
                   rng_range8(0, 99) < TANK_FIRE_CHANCE && ebullets_of(EB_FLAK) < TANK_SHELLS) {
            tank_fire(t, ccx);
            t->cooldown = TANK_RELOAD_MIN + rng_range8(0, TANK_RELOAD_SPREAD);
        }
    }
}

/* A tank or jeep at world x (within `reach`) is wrecked. */
static bool vehicles_hit(int16_t x, uint8_t reach)
{
    for (uint8_t i = 0; i < TANKS_ACTIVE; i++) {
        tank_t *t = &tanks[i];
        if (!t->active || abs(x - (FROM_SUB(t->x) + vw / 2)) >= reach)
            continue;
        /* A wreck; its prison rebuilds it in a while, and rolls it out
         * again when it is the nearest. */
        zone_tank_t *z = &zone[t->base][t->slot];
        z->state = T_WRECK;
        z->awake = false;
        z->rebuild = TANK_REBUILD;
        t->active = false;
        add_score(boreal ? 150 : 200);
        explosion_spawn(FROM_SUB(t->x) + vw / 2, veh_y + 8, true);
        return true;
    }
    return false;
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

static bool balloon_hit(int16_t x, int16_t y)
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
        if (compounds_breached() < level->air_trigger)
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

static bool jet_hit(int16_t x, int16_t y)
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

/* --- Rocket turrets (level 2) --------------------------------------------- */
/* One stands east of each prison, on the way home, and is manned once
 * that prison is opened. It turns its launcher to the chopper, holds fire
 * for a while each time it comes into view, and only fires at a chopper
 * flying above the jeeps' reach, as level 1's jets do: after a while up
 * there a warning, and then the launchers in range warm up (the beacon
 * blinks fast) and fire a slow rocket that homes on the chopper for a
 * while. Dropping low before it fires calls it off. The cannon or a bomb
 * wrecks a launcher, and it is rebuilt after a while. */
#define TURRET_FROM_BASE 260  /* px east of its prison's door */
#define TURRET_Y (GROUND_LINE - TURRET_H + 2)
#define TURRET_WRECK 2        /* frame */
#define TURRET_RANGE 200      /* px across to the chopper */
#define TURRET_FIRST_SHOT 90  /* frames it holds fire after coming into view */
#define TURRET_WARN 40        /* frames its light blinks before it fires */
#define TURRET_RELOAD 150
#define TURRET_RELOAD_SPREAD 90
#define TURRET_REBUILD (15 * 60)
#define ROCKETS 2             /* in the air at once, from all of them */
#define TURRET_AIR_WAIT 120   /* frames up high before they fire; the warning at half that */
#define TURRET_OVERLAP 24     /* px of the jeeps' reach the launchers cover too */
#define TURRET_HIGH (JEEP_Y - JEEP_REACH + TURRET_OVERLAP) /* "up high": the chopper's middle above this row */

typedef struct
{
    bool wreck;
    bool in_view;
    uint8_t aim;      /* frame: 0 low, 1 steep */
    int8_t dir;       /* which way it faces */
    uint8_t cooldown;
    uint8_t warn;     /* frames until it fires, blinking */
    uint16_t rebuild;
} turret_t;

static turret_t turrets[NUM_COMPOUNDS];
static bool light_on = true;
static uint16_t loiter_high; /* frames the chopper has been up high */

static int16_t turret_x(uint8_t i) /* left edge */
{
    return base_x(i) + TURRET_FROM_BASE - TURRET_W / 2;
}

static void turrets_init(void)
{
    loiter_high = 0;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        turrets[i].wreck = false;
        turrets[i].in_view = false;
        turrets[i].aim = 0;
        turrets[i].dir = -1;
        turrets[i].warn = 0;
    }
    light_on = true; /* as the bank's palette has it */
}

/* Each aim (35 and 65 degrees): launch speeds, and where the tubes' mouths
 * are from the launcher's pivot, at (TURRET_W / 2 + 1, 13) in the sprite. */
static const int8_t launch_vx[2] = {14, 7};
static const int8_t launch_vy[2] = {-10, -15};
static const int8_t mouth_dx[2] = {14, 7};
static const int8_t mouth_dy[2] = {-9, -14};

/* Is turret i on screen? */
static bool turret_in_view(uint8_t i)
{
    int16_t sx = screen_x(turret_x(i));
    return sx > -TURRET_W / 2 && sx < SCREEN_W - TURRET_W / 2;
}

static void update_turrets(int16_t ccx, int16_t ccy, bool safe)
{
    /* The clock only runs, and the warning only comes, while a manned,
     * standing launcher on screen has the chopper in range. */
    bool threat = false;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
        if (opened[i] && !turrets[i].wreck && turret_in_view(i) &&
            abs(ccx - (turret_x(i) + TURRET_W / 2)) < TURRET_RANGE)
            threat = true;
    bool high = threat && !safe && player_alive() && !chopper_is_landed && ccy < TURRET_HIGH;
    if (!high) {
        loiter_high = 0;
        radar_warned = false;
    } else if (++loiter_high > TURRET_AIR_WAIT / 2 && !radar_warned) {
        radar_warned = true;
        msg_flash("MISSILE SITES HAVE YOU - GET LOW!", C_ORANGE, 120);
    }
    bool armed = loiter_high > TURRET_AIR_WAIT;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        turret_t *t = &turrets[i];
        if (t->wreck) {
            if (!--t->rebuild)
                t->wreck = false;
            continue;
        }
        int16_t tx = turret_x(i);
        int16_t tcx = tx + TURRET_W / 2;
        bool view = turret_in_view(i);
        if (view && !t->in_view)
            t->cooldown = TURRET_FIRST_SHOT;
        t->in_view = view;
        if (!opened[i] || !view)
            continue;
        /* Point at the chopper. */
        int16_t dx = ccx - tcx, up = TURRET_Y - ccy;
        int16_t ax = abs(dx);
        t->dir = dx > 0 ? 1 : -1;
        t->aim = up < ax ? 0 : 1;
        if (t->warn) {
            if (!high) { /* got low in time */
                t->warn = 0;
                t->cooldown = 30;
                continue;
            }
            if (--t->warn)
                continue;
            int16_t mx = tcx + 1 + t->dir * mouth_dx[t->aim];
            ebullet_spawn(mx, TURRET_Y + 13 + mouth_dy[t->aim], t->dir * launch_vx[t->aim], launch_vy[t->aim],
                          EB_ROCKET);
            sfx_enemy(SFX_TANK_FIRE, SFX_PRI_FIRE);
            t->cooldown = TURRET_RELOAD + rng_range8(0, TURRET_RELOAD_SPREAD);
            continue;
        }
        if (t->cooldown) {
            t->cooldown--;
            continue;
        }
        if (armed && ax < TURRET_RANGE && up > 0 && ebullets_of(EB_ROCKET) < ROCKETS)
            t->warn = TURRET_WARN;
    }
}

static bool turret_hit(int16_t x, int16_t y, bool bomb)
{
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        turret_t *t = &turrets[i];
        int16_t tcx = turret_x(i) + TURRET_W / 2;
        if (t->wreck || abs(x - tcx) >= (bomb ? 20 : 14) || (!bomb && y < TURRET_Y + 2))
            continue;
        t->wreck = true;
        t->warn = 0;
        t->rebuild = TURRET_REBUILD;
        add_score(250);
        explosion_spawn(tcx, TURRET_Y + 8, true);
        return true;
    }
    return false;
}

/* --- Worms (level 2) ------------------------------------------------------ */
/* Sit on the ground too long, away from home, once enough prisons are
 * open, and a worm comes for the chopper: a ridge of earth tunnels toward
 * it, and when it gets there the worm bursts up and swallows whatever is
 * there. Lifting off in time is the answer; a bomb on the ridge kills it,
 * and so does the cannon while it is out of the ground. */
#define WORM_GROUND_WAIT 90  /* frames landed before one may come */
#define WORM_START 150       /* px from the chopper it starts tunnelling */
#define WORM_SPEED 20        /* subpixels per frame */
#define WORM_GIVE_UP 240     /* frames it hunts before going deep again */
#define WORM_BITE 16         /* px either side of its middle */
#define WORM_TOP (GROUND_LINE - WORM_H + 4)

enum
{
    WORM_OFF,
    WORM_TUNNEL,
    WORM_LUNGE
};

static struct
{
    uint8_t state;
    int32_t x;  /* subpixels, its middle */
    uint16_t timer;
} worm;

/* The lunge, by frames since it began: which frame shows, and whether it
 * is up high enough to bite. */
#define LUNGE_TIME 56
static uint8_t lunge_frame(uint16_t t)
{
    return t < 6 ? 0 : (t < 12 ? 1 : (t < 40 ? 2 : (t < 48 ? 1 : 0)));
}

static void worm_init(void)
{
    worm.state = WORM_OFF;
}

static void update_worm(int16_t ccx, bool safe)
{
    if (worm.state == WORM_OFF) {
        if (compounds_breached() < level->air_trigger || safe || !chopper_is_landed || !player_alive()) {
            loiter_ground = 0;
            return;
        }
        if (++loiter_ground <= WORM_GROUND_WAIT || rng_range8(0, 99) >= 2)
            return;
        loiter_ground = 0;
        int16_t x = ccx + (rng_coin() ? WORM_START : -WORM_START);
        if (x < 16 || x > SAFE_LINE)
            x = 2 * ccx - x; /* the other side */
        worm.state = WORM_TUNNEL;
        worm.x = TO_SUB(x);
        worm.timer = 0;
        msg_flash("SOMETHING IS TUNNELLING TOWARD YOU!", C_ORANGE, 120);
        sfx_enemy(SFX_WARNING, SFX_PRI_EVENT);
        return;
    }
    int16_t wx = FROM_SUB(worm.x);
    if (worm.state == WORM_TUNNEL) {
        if (++worm.timer > WORM_GIVE_UP) {
            worm.state = WORM_OFF;
            return;
        }
        int16_t d = ccx - wx;
        if (abs(d) <= 2) {
            worm.state = WORM_LUNGE;
            worm.timer = 0;
            sfx_enemy(SFX_BIG_EXPLODE, SFX_PRI_EVENT);
            return;
        }
        worm.x += d > 0 ? WORM_SPEED : -WORM_SPEED;
        return;
    }
    /* Out of the ground: what is over it, low enough, is swallowed. */
    uint16_t t = worm.timer++;
    if (t >= LUNGE_TIME) {
        worm.state = WORM_OFF;
        return;
    }
    if (lunge_frame(t) == 2 && hostages_eaten(wx, WORM_BITE))
        msg_flash("A WORM GOT A HOSTAGE!", C_RED, 90);
    if (lunge_frame(t) == 2 && player_alive() && abs(ccx - wx) < WORM_BITE &&
        FROM_SUB(chopper_y) + CHOPPER_H > WORM_TOP + 6) {
        explosion_spawn(ccx, FROM_SUB(chopper_y) + CHOPPER_H / 2, true);
        player_kill();
    }
}

static bool worm_hit(int16_t x, int16_t y, bool bomb)
{
    int16_t wx = FROM_SUB(worm.x);
    bool hit;
    if (worm.state == WORM_TUNNEL)
        hit = bomb && abs(x - wx) < 18;
    else if (worm.state == WORM_LUNGE)
        hit = lunge_frame(worm.timer) == 2 && abs(x - wx) < 10 && (bomb || y > WORM_TOP);
    else
        hit = false;
    if (!hit)
        return false;
    worm.state = WORM_OFF;
    add_score(300);
    explosion_spawn(wx, GROUND_LINE - 10, true);
    return true;
}

/* --------------------------------------------------------------------------- */

void enemies_update(void)
{
    int16_t ccx = chopper_cx();
    int16_t ccy = FROM_SUB(chopper_y) + CHOPPER_H / 2;
    bool safe = ccx > SAFE_LINE;
    update_tanks(ccx, safe);
    if (boreal) {
        update_turrets(ccx, ccy, safe);
        update_worm(ccx, safe);
    } else {
        update_balloon(ccx, ccy);
        update_jet(ccx, safe);
    }
}

void enemies_bomb(int16_t x, bool deep)
{
    if (deep && vehicles_hit(x, 20))
        return;
    if (boreal && !turret_hit(x, 0, true))
        worm_hit(x, 0, true);
}

bool enemies_check_hit(int16_t x, int16_t y)
{
    if (!boreal)
        return balloon_hit(x, y) || jet_hit(x, y);
    /* The cannon kills a jeep, low over the ground. */
    if (y >= JEEP_Y + 2 && y < GROUND_LINE && vehicles_hit(x, JEEP_W / 2))
        return true;
    return turret_hit(x, y, false) || worm_hit(x, y, false);
}

/* Level 2's turrets and worm. The turrets' warning light is a palette
 * entry: it blinks while any of them is about to fire. */
#define TURRET_LIGHT 10
static void boreal_render(int16_t cam)
{
    bool warn = false;
    for (uint8_t i = 0; i < NUM_COMPOUNDS; i++) {
        turret_t *t = &turrets[i];
        warn |= t->warn != 0;
        uint8_t f = t->wreck ? TURRET_WRECK : t->aim;
        spr_place(SPR_BALLOON_START + i, XRAM_IMG_TURRET + f * TURRET_FRAME_BYTES, PAL_TURRET,
                  WH(TURRET_W, TURRET_H), t->dir > 0 ? OPT4_FLIP : OPT4, turret_x(i) - cam, TURRET_Y);
    }
    /* A slow blink to catch the eye; fast just before it fires. */
    bool on = warn ? (frame_count & 4) != 0 : (frame_count & 31) < 10;
    if (on != light_on) {
        light_on = on;
        uint16_t c = (on ? COLOR_FROM_RGB8(255, 60, 50) : COLOR_FROM_RGB8(90, 12, 14)) | COLOR_ALPHA_MASK;
        xram0_write(PAL_ADDR(PAL_TURRET) + TURRET_LIGHT * 2, &c, 2);
    }

    spr_hide(SPR_JET_START + 1);
    int16_t wx = FROM_SUB(worm.x);
    if (worm.state == WORM_TUNNEL)
        spr_place(SPR_JET_START, XRAM_IMG_MOUND + ((frame_count >> 3) & 1) * MOUND_FRAME_BYTES, PAL_WORM,
                  WH(MOUND_W, MOUND_H), (wx & 8) ? OPT4_FLIP : OPT4, wx - MOUND_W / 2 - cam, GROUND_LINE - MOUND_H + 3);
    else if (worm.state == WORM_LUNGE)
        spr_place(SPR_JET_START, XRAM_IMG_WORM + lunge_frame(worm.timer) * WORM_FRAME_BYTES, PAL_WORM,
                  WH(WORM_W, WORM_H), OPT4, wx - WORM_W / 2 - cam, WORM_TOP);
    else
        spr_hide(SPR_JET_START);
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
        if (boreal) {
            uint8_t f = (t->turret ? 0 : 2) + ((t->anim >> 2) & 1);
            spr_place(SPR_TANK_START + i, XRAM_IMG_JEEP + f * JEEP_FRAME_BYTES, PAL_JEEP, WH(JEEP_W, JEEP_H),
                      right ? OPT4_FLIP : OPT4, FROM_SUB(t->x) - cam, JEEP_Y);
            continue;
        }
        uint8_t f = (t->turret ? 0 : 2) + ((t->anim >> 3) & 1);
        spr_place(SPR_TANK_START + i, XRAM_IMG_TANK + f * TANK_FRAME_BYTES, PAL_TANK, WH(TANK_W, TANK_H),
                  right ? OPT4_FLIP : OPT4, FROM_SUB(t->x) - cam, TANK_Y);
    }

    if (boreal) {
        boreal_render(cam);
        return;
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
