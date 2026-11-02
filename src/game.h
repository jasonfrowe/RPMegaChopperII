#ifndef GAME_H
#define GAME_H

#include <stdbool.h>
#include <stdint.h>
#include "gen/assets.h"

#define SCREEN_W 320
#define SCREEN_H 240
#define HUD_H 16

#define SUBPIXEL_BITS 4
#define ONE_PIXEL (1 << SUBPIXEL_BITS)
#define TO_SUB(px) ((int32_t)(px) << SUBPIXEL_BITS)
#define FROM_SUB(sub) ((int16_t)((sub) >> SUBPIXEL_BITS))

#define WORLD_MAX_X (WORLD_W_PX - SCREEN_W)
#define CAMERA_MAX_X TO_SUB(WORLD_MAX_X)

/* The chopper's box is CHOPPER_W x CHOPPER_H; its skids are its bottom row.
 * Landed, the skids rest on the snow's surface. */
#define GROUND_Y (GROUND_LINE - CHOPPER_H + 1)
#define GROUND_Y_SUB TO_SUB(GROUND_Y)
#define CEILING_Y (HUD_H + 10)
#define CEILING_Y_SUB TO_SUB(CEILING_Y)

/* Where things stand: the top row of their sprite. */
#define HOSTAGE_Y (GROUND_LINE - 14)
#define TANK_Y (GROUND_LINE - TANK_H + 2)

/* Home base. The chopper starts and unloads on the helipad. */
#define CHOPPER_START_X ((HOME_PAD_X0 + HOME_PAD_X1 - CHOPPER_W) / 2)
#define HOME_PAD_MIN_X (HOME_PAD_X0 - 8)
#define HOME_PAD_MAX_X (HOME_PAD_X1 - CHOPPER_W + 8)

/* A compound's door, in world pixels. */
#define DOOR_X(i) ((int16_t)(compound_cols[i] + DOOR_COL) * 16)
#define DOOR_TOP (GROUND_LINE - DOOR_H * 16)
/* Its concrete block, which stops shots. */
#define BUNKER_X0(i) ((int16_t)(compound_cols[i] + 2) * 16)
#define BUNKER_X1(i) ((int16_t)(compound_cols[i] + 9) * 16)
#define BUNKER_TOP (GROUND_LINE - 58)

/* Tank flak: the arc tops out around screen row FLAK_CEILING, so flying
 * above that is safe from the tanks (but the jets come for you). */
#define FLAK_GRAVITY 2
#define FLAK_CEILING 80

/* East of this nothing attacks: the home base is safe, as in Choplifter.
 * Halfway between the last prison and the helipad. */
#define SAFE_LINE ((DOOR_X(NUM_COMPOUNDS - 1) + HOME_PAD_X0) / 2)

/* Near home the camera slides all the way east, so the hangar is in view. */
#define HOME_VIEW_X (HOME_PAD_X0 - 140)

/* Camera dead zone, as screen x of the chopper's left edge. */
#define SCROLL_LEFT_EDGE 110
#define SCROLL_RIGHT_EDGE (210 - CHOPPER_W)

/* Flight */
#define TURN_DURATION 12
#define MAX_SPEED (2 * ONE_PIXEL + 8) /* 2.5 px/frame */
#define ACCEL_RATE 1
#define FRICTION_RATE 1
#define GRAVITY_SPEED 6
#define CLIMB_SPEED 20
#define DIVE_SPEED 28

#define MAX_CARGO 16
#define HOSTAGES_PER_COMPOUND 16
#define TOTAL_HOSTAGES (NUM_COMPOUNDS * HOSTAGES_PER_COMPOUND)
#define STARTING_LIVES 3

typedef enum
{
    GS_TITLE,
    GS_PLAY,
    GS_PAUSE,
    GS_LEVEL_CLEAR,
    GS_GAMEOVER
} game_state_t;

typedef enum
{
    FACING_LEFT = -1,
    FACING_FRONT = 0,
    FACING_RIGHT = 1
} chopper_heading_t;

extern game_state_t gstate;
extern uint32_t score;
extern uint32_t hiscore;
extern uint8_t lives;
extern uint8_t current_level;
extern uint8_t saved_count;
extern uint8_t lost_count;
extern uint8_t cargo_count;
extern int32_t camera_x; /* subpixels */
extern uint16_t game_timer;
extern uint8_t frame_count;

void rng_seed(uint16_t seed);
uint16_t rng_next(void);
uint8_t rng_range8(uint8_t min, uint8_t max);

void add_score(uint16_t pts);
void hiscore_load(void);
void hiscore_save(void);

/* World x to screen x. */
static inline int16_t screen_x(int16_t wx)
{
    return wx - FROM_SUB(camera_x);
}

#endif /* GAME_H */
