#include <rp6502.h>
#include "game.h"
#include "input.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

int32_t chopper_world_x;
int32_t chopper_y;
int16_t chopper_vel_x;
int16_t chopper_vel_y;
chopper_heading_t chopper_heading;
player_status_t player_status;
bool chopper_is_landed;

static uint8_t blade_anim;
static uint8_t rotor_sound_timer;
static uint8_t fire_cooldown;
static int8_t last_side_facing;
static uint8_t turn_anim_timer;
static uint8_t crash_timer;

#define MAX_SPEED_X TO_SUB(4)
#define ACCEL_X TO_SUB(1) / 3
#define DECEL_X TO_SUB(1) / 4
#define VERTICAL_SPEED TO_SUB(2)

void player_init(void)
{
    player_reset();
}

void player_reset(void)
{
    chopper_world_x = TO_SUB(HOME_BASE_X);
    chopper_y = TO_SUB(GROUND_Y);
    chopper_vel_x = 0;
    chopper_vel_y = 0;
    chopper_heading = FACING_LEFT;
    last_side_facing = -1;
    player_status = PL_LANDED;
    chopper_is_landed = true;
    blade_anim = 0;
    rotor_sound_timer = 0;
    fire_cooldown = 0;
    turn_anim_timer = 0;
    crash_timer = 0;

    /* Center camera around chopper */
    camera_x = chopper_world_x - TO_SUB(SCREEN_W / 2 - 16);
    if (camera_x < 0) camera_x = 0;
    if (camera_x > TO_SUB(WORLD_MAX_X)) camera_x = TO_SUB(WORLD_MAX_X);
}

void player_kill(void)
{
    if (player_status == PL_CRASHING || player_status == PL_RESPAWN_WAIT)
        return;

    player_status = PL_CRASHING;
    crash_timer = 0;
    sfx_player(SFX_PLAYER_DIE, SFX_PRI_TOP);

    int16_t screen_x = FROM_SUB(chopper_world_x - camera_x);
    int16_t screen_y = FROM_SUB(chopper_y);
    explosion_spawn(screen_x + 8, screen_y, true);

    if (lives > 0)
        lives--;
}

void player_update(void)
{
    if (player_status == PL_RESPAWN_WAIT) {
        if (lives > 0) {
            player_reset();
        } else {
            gstate = GS_GAMEOVER;
        }
        return;
    }

    if (player_status == PL_CRASHING) {
        crash_timer++;
        /* Chopper tumbles down with gravity if airborne */
        if (chopper_y < TO_SUB(GROUND_Y)) {
            chopper_y += TO_SUB(3);
        } else {
            chopper_y = TO_SUB(GROUND_Y);
        }
        if (crash_timer > 90) {
            player_status = PL_RESPAWN_WAIT;
        }
        return;
    }

    /* Blade rotor animation */
    blade_anim = (blade_anim + 1) & 1;

    /* Periodic rotor thumping SFX */
    if (++rotor_sound_timer >= 12) {
        rotor_sound_timer = 0;
        sfx_player(SFX_ROTOR, SFX_PRI_FIRE);
    }

    if (fire_cooldown > 0)
        fire_cooldown--;

    /* Rotate Control (Button 2) */
    if (in_pressed & IN_ROTATE) {
        turn_anim_timer = 6;
        if (chopper_heading == FACING_LEFT) {
            chopper_heading = FACING_FRONT;
            last_side_facing = -1;
        } else if (chopper_heading == FACING_RIGHT) {
            chopper_heading = FACING_FRONT;
            last_side_facing = 1;
        } else {
            /* Currently facing front: turn to opposite side of where we came */
            if (last_side_facing == -1) {
                chopper_heading = FACING_RIGHT;
                last_side_facing = 1;
            } else {
                chopper_heading = FACING_LEFT;
                last_side_facing = -1;
            }
        }
    }
    if (turn_anim_timer > 0)
        turn_anim_timer--;

    /* Altitude Control */
    if (in_held & IN_UP) {
        chopper_y -= VERTICAL_SPEED;
        if (chopper_y < TO_SUB(CEILING_Y))
            chopper_y = TO_SUB(CEILING_Y);
        chopper_is_landed = false;
        player_status = PL_ALIVE;
    } else if (in_held & IN_DOWN) {
        chopper_y += VERTICAL_SPEED;
        if (chopper_y >= TO_SUB(GROUND_Y)) {
            chopper_y = TO_SUB(GROUND_Y);
            if (chopper_vel_x == 0) {
                chopper_is_landed = true;
                player_status = PL_LANDED;
            }
        }
    }

    /* Horizontal Control */
    if (in_held & IN_LEFT) {
        chopper_vel_x -= ACCEL_X;
        if (chopper_vel_x < -MAX_SPEED_X)
            chopper_vel_x = -MAX_SPEED_X;
        chopper_is_landed = false;
        player_status = PL_ALIVE;
    } else if (in_held & IN_RIGHT) {
        chopper_vel_x += ACCEL_X;
        if (chopper_vel_x > MAX_SPEED_X)
            chopper_vel_x = MAX_SPEED_X;
        chopper_is_landed = false;
        player_status = PL_ALIVE;
    } else {
        /* Natural deceleration / momentum */
        if (chopper_vel_x > 0) {
            chopper_vel_x -= DECEL_X;
            if (chopper_vel_x < 0) chopper_vel_x = 0;
        } else if (chopper_vel_x < 0) {
            chopper_vel_x += DECEL_X;
            if (chopper_vel_x > 0) chopper_vel_x = 0;
        }
    }

    /* Update Position */
    chopper_world_x += chopper_vel_x;
    if (chopper_world_x < TO_SUB(16)) {
        chopper_world_x = TO_SUB(16);
        chopper_vel_x = 0;
    }
    if (chopper_world_x > TO_SUB(WORLD_W_PX - 32)) {
        chopper_world_x = TO_SUB(WORLD_W_PX - 32);
        chopper_vel_x = 0;
    }

    /* Check landing status when on the ground */
    if (chopper_y >= TO_SUB(GROUND_Y)) {
        chopper_y = TO_SUB(GROUND_Y);
        if (chopper_vel_x == 0) {
            chopper_is_landed = true;
            player_status = PL_LANDED;
        }
    }

    /* Weapons Firing (Button 1) */
    if ((in_held & IN_FIRE) && fire_cooldown == 0) {
        int16_t px = FROM_SUB(chopper_world_x);
        int16_t py = FROM_SUB(chopper_y);

        if (chopper_heading == FACING_LEFT) {
            bullet_spawn(px - 4, py + 8, -TO_SUB(7), 0);
            sfx_player(SFX_VULCAN, SFX_PRI_EVENT);
            fire_cooldown = 8;
        } else if (chopper_heading == FACING_RIGHT) {
            bullet_spawn(px + 28, py + 8, TO_SUB(7), 0);
            sfx_player(SFX_VULCAN, SFX_PRI_EVENT);
            fire_cooldown = 8;
        } else {
            /* Facing Front: Drop Bomb! */
            bomb_spawn(px + 12, py + 12, chopper_vel_x >> 1);
            sfx_player(SFX_BOMB_DROP, SFX_PRI_EVENT);
            fire_cooldown = 16;
        }
    }

    /* Smooth Camera Tracking */
    int32_t target_cam = chopper_world_x - TO_SUB(SCREEN_W / 2 - 16);
    if (target_cam < 0) target_cam = 0;
    if (target_cam > TO_SUB(WORLD_MAX_X)) target_cam = TO_SUB(WORLD_MAX_X);

    /* Camera follows smoothly */
    camera_x += (target_cam - camera_x) >> 3;
    if (camera_x < 0) camera_x = 0;
    if (camera_x > TO_SUB(WORLD_MAX_X)) camera_x = TO_SUB(WORLD_MAX_X);
}

void player_render(void)
{
    if (player_status == PL_CRASHING) {
        spr_hide(SPR_CHOPPER);
        return;
    }

    uint8_t base_frame;
    if (turn_anim_timer > 0) {
        base_frame = (chopper_heading == FACING_RIGHT) ? 6 : 2;
    } else if (chopper_heading == FACING_FRONT) {
        if (chopper_vel_x < -TO_SUB(1))
            base_frame = 14; /* Bank Left */
        else if (chopper_vel_x > TO_SUB(1))
            base_frame = 16; /* Bank Right */
        else
            base_frame = 4;  /* Center Hover */
    } else if (chopper_heading == FACING_LEFT) {
        if (chopper_vel_x < -TO_SUB(1))
            base_frame = 10; /* Accelerate Left */
        else if (chopper_vel_x > TO_SUB(1))
            base_frame = 12; /* Brake Left */
        else
            base_frame = 0;  /* Idle Left */
    } else {
        /* FACING_RIGHT */
        if (chopper_vel_x > TO_SUB(1))
            base_frame = 20; /* Accelerate Right */
        else if (chopper_vel_x < -TO_SUB(1))
            base_frame = 18; /* Brake Right */
        else
            base_frame = 8;  /* Idle Right */
    }

    uint8_t final_frame = base_frame + blade_anim;
    uint16_t sprite_addr = XRAM_IMG_CHOPPER + (uint16_t)final_frame * CHOPPER_FRAME_BYTES;

    int16_t screen_x = FROM_SUB(chopper_world_x - camera_x);
    int16_t screen_y = FROM_SUB(chopper_y);

    spr_setup(SPR_CHOPPER, sprite_addr, PAL_ADDR(PAL_CHOPPER), WH(32, 16), OPT4);
    spr_pos(SPR_CHOPPER, screen_x, screen_y);
}
