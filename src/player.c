#include <rp6502.h>
#include <stdlib.h>
#include "game.h"
#include "input.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "weather.h"
#include "xram.h"

int32_t chopper_world_x;
int32_t chopper_y;
int16_t chopper_vel_x;
int16_t chopper_vel_y;
chopper_heading_t chopper_heading;
player_status_t player_status;
bool chopper_is_landed;
volatile bool chopper_invulnerable;
volatile int16_t debug_warp_x, debug_warp_y;

static chopper_heading_t next_heading;
static int8_t last_side; /* the side faced before turning to the front */
static bool is_turning;
static uint8_t turn_timer;
static uint8_t fire_cooldown;
static uint8_t respawn_timer;
static uint8_t blink; /* frames of flicker after respawning */

/* Frame pairs in chopper.png; +1 is the other rotor phase. */
enum
{
    F_SIDE = 0,
    F_NOSE_DOWN = 2,
    F_NOSE_UP = 4,
    F_QUARTER = 6,
    F_FRONT = 8,
    F_BANK = 10,
};
static uint8_t frame;
static bool flip; /* drawn facing right */

void player_init(void)
{
    player_status = PL_LANDED;
    chopper_world_x = TO_SUB(CHOPPER_START_X);
    chopper_y = GROUND_Y_SUB;
    chopper_vel_x = 0;
    chopper_vel_y = 0;
    chopper_heading = FACING_LEFT;
    next_heading = FACING_LEFT;
    last_side = -1;
    is_turning = false;
    turn_timer = 0;
    chopper_is_landed = true;
    fire_cooldown = 0;
    respawn_timer = 0;
    blink = 90;
    frame = F_SIDE;
    flip = false;

    /* Home is the last screen of the world, so this is the camera's end stop. */
    camera_x = chopper_world_x - TO_SUB(SCREEN_W / 2 - CHOPPER_W / 2);
    if (camera_x > CAMERA_MAX_X)
        camera_x = CAMERA_MAX_X;
}

void player_kill(void)
{
    if (!player_alive() || blink || chopper_invulnerable)
        return;
    player_status = PL_CRASHING;
    respawn_timer = 75;
    sfx_player(SFX_PLAYER_DIE, SFX_PRI_TOP);
    explosion_spawn(FROM_SUB(chopper_world_x) + CHOPPER_W / 2, FROM_SUB(chopper_y) + CHOPPER_H / 2, true);
    if (lives > 0)
        lives--;
    /* Everyone aboard is lost with the chopper. */
    lost_count += cargo_count;
    cargo_count = 0;
}

static void friction(void)
{
    if (chopper_vel_x > 0)
        chopper_vel_x -= FRICTION_RATE;
    else if (chopper_vel_x < 0)
        chopper_vel_x += FRICTION_RATE;
}

static void accel(int8_t dir, int16_t limit)
{
    if (dir < 0 && chopper_vel_x > -limit)
        chopper_vel_x -= ACCEL_RATE;
    else if (dir > 0 && chopper_vel_x < limit)
        chopper_vel_x += ACCEL_RATE;
}

static void fire(void)
{
    int16_t px = FROM_SUB(chopper_world_x);
    int16_t py = FROM_SUB(chopper_y);
    if (chopper_heading == FACING_FRONT) {
        /* One bomb at a time, one per press. */
        if (!(in_pressed & IN_FIRE) || bomb_in_air())
            return;
        bomb_spawn(px + CHOPPER_W / 2 - 4, py + CHOPPER_H - 8, chopper_y < GROUND_Y_SUB - TO_SUB(BOMB_DEEP_HEIGHT));
        sfx_player(SFX_BOMB_DROP, SFX_PRI_EVENT);
        return;
    }
    /* The cannon points where the nose does: down while speeding up,
     * up while braking. */
    int8_t d = (int8_t)chopper_heading;
    int16_t vy = frame == F_NOSE_DOWN ? TO_SUB(2) : (frame == F_NOSE_UP ? -TO_SUB(1) : 0);
    int16_t nose = d < 0 ? px - 4 : px + CHOPPER_W - 4;
    bullet_spawn(nose, py + 12 + (vy > 0 ? 2 : 0), d * TO_SUB(6) + chopper_vel_x, vy);
    sfx_player(SFX_VULCAN, SFX_PRI_FIRE);
    fire_cooldown = 7;
}

void player_update(void)
{
    if (fire_cooldown)
        fire_cooldown--;
    if (blink)
        blink--;

    if (player_status == PL_CRASHING) {
        /* Tumble down, burning. */
        chopper_vel_y += 3;
        chopper_y += chopper_vel_y;
        chopper_world_x += chopper_vel_x;
        if ((frame_count & 7) == 0)
            small_explosion_spawn(chopper_cx(), FROM_SUB(chopper_y) + 6);
        if (chopper_y >= GROUND_Y_SUB) {
            chopper_y = GROUND_Y_SUB;
            chopper_vel_y = 0;
            chopper_vel_x = 0;
            if (respawn_timer > 30) {
                explosion_spawn(chopper_cx(), GROUND_LINE - 12, true);
                respawn_timer = 30;
            }
        }
        if (--respawn_timer == 0) {
            player_status = PL_RESPAWN_WAIT;
            respawn_timer = 60;
        }
        return;
    }
    if (player_status == PL_RESPAWN_WAIT) {
        if (--respawn_timer == 0 && lives > 0)
            player_init();
        return;
    }

    if (debug_warp_x) {
        chopper_world_x = TO_SUB(debug_warp_x);
        chopper_y = TO_SUB(debug_warp_y);
        camera_x = chopper_world_x - TO_SUB(150);
        debug_warp_x = 0;
    }
    chopper_is_landed = chopper_y >= GROUND_Y_SUB;

    /* Turning: left -> front -> right and back, one step per press. */
    if ((in_pressed & IN_ROTATE) && !is_turning) {
        if (chopper_heading != FACING_FRONT) {
            last_side = (int8_t)chopper_heading;
            next_heading = FACING_FRONT;
        } else {
            next_heading = (chopper_heading_t)(-last_side);
        }
        is_turning = true;
        turn_timer = TURN_DURATION;
    }

    int8_t stick = (in_held & IN_LEFT) ? -1 : ((in_held & IN_RIGHT) ? 1 : 0);
    if (chopper_is_landed)
        stick = 0;

    if (is_turning) {
        int8_t side = chopper_heading != FACING_FRONT ? (int8_t)chopper_heading : (int8_t)next_heading;
        frame = F_QUARTER;
        flip = side > 0;
        friction();
        if (--turn_timer == 0) {
            chopper_heading = next_heading;
            is_turning = false;
        }
    } else if (chopper_heading == FACING_FRONT) {
        if (stick) {
            frame = F_BANK;
            flip = stick > 0;
            accel(stick, ONE_PIXEL + 8);
        } else {
            frame = F_FRONT;
            flip = false;
            friction();
        }
    } else {
        int8_t d = (int8_t)chopper_heading;
        flip = d > 0;
        if (stick == d) {
            frame = F_NOSE_DOWN;
            accel(stick, MAX_SPEED);
        } else if (stick == -d) {
            frame = F_NOSE_UP;
            accel(stick, MAX_SPEED / 2);
        } else {
            frame = F_SIDE;
            friction();
        }
    }

    /* Altitude. */
    if (in_held & IN_UP)
        chopper_vel_y = -CLIMB_SPEED;
    else if (in_held & IN_DOWN)
        chopper_vel_y = DIVE_SPEED;
    else
        chopper_vel_y = chopper_is_landed ? 0 : GRAVITY_SPEED;
    chopper_y += chopper_vel_y;
    if (chopper_y < CEILING_Y_SUB)
        chopper_y = CEILING_Y_SUB;
    if (chopper_y >= GROUND_Y_SUB) {
        chopper_y = GROUND_Y_SUB;
        chopper_vel_x = 0;
        chopper_vel_y = 0;
        chopper_is_landed = true;
        player_status = PL_LANDED;
    } else {
        chopper_is_landed = false;
        player_status = PL_ALIVE;
    }

    chopper_world_x += chopper_vel_x;
    if (!chopper_is_landed)
        chopper_world_x += wind; /* a storm pushes it about */
    if (chopper_world_x < TO_SUB(8)) {
        chopper_world_x = TO_SUB(8);
        chopper_vel_x = 0;
    } else if (chopper_world_x > TO_SUB(WORLD_W_PX - CHOPPER_W - 8)) {
        chopper_world_x = TO_SUB(WORLD_W_PX - CHOPPER_W - 8);
        chopper_vel_x = 0;
    }

    if ((in_held & IN_FIRE) && fire_cooldown == 0 && !chopper_is_landed && !is_turning)
        fire();

    /* The camera keeps the chopper inside its dead zone. */
    int32_t sx = chopper_world_x - camera_x;
    if (sx > TO_SUB(SCROLL_RIGHT_EDGE))
        camera_x += sx - TO_SUB(SCROLL_RIGHT_EDGE);
    else if (sx < TO_SUB(SCROLL_LEFT_EDGE))
        camera_x += sx - TO_SUB(SCROLL_LEFT_EDGE);
    if (camera_x < 0)
        camera_x = 0;
    if (camera_x > CAMERA_MAX_X)
        camera_x = CAMERA_MAX_X;
}

void player_render(void)
{
    if (player_status == PL_RESPAWN_WAIT || (blink && (frame_count & 2))) {
        spr_hide(SPR_CHOPPER);
        return;
    }
    uint8_t f = frame + ((frame_count >> 1) & 1);
    if (player_status == PL_CRASHING)
        f = F_BANK + ((frame_count >> 2) & 1);
    spr_place(SPR_CHOPPER, XRAM_IMG_CHOPPER + (uint16_t)f * CHOPPER_FRAME_BYTES, PAL_CHOPPER, WH(CHOPPER_W, CHOPPER_H),
              flip ? OPT4_FLIP : OPT4, FROM_SUB(chopper_world_x - camera_x), FROM_SUB(chopper_y));
}
