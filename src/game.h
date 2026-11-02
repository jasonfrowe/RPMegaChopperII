#ifndef GAME_H
#define GAME_H

#include <stdbool.h>
#include <stdint.h>

#define SCREEN_W 320
#define SCREEN_H 240

#define SUBPIXEL_BITS 4
#define TO_SUB(px) ((int32_t)(px) << SUBPIXEL_BITS)
#define FROM_SUB(sub) ((int16_t)((sub) >> SUBPIXEL_BITS))

#define WORLD_W_PX 4096
#define WORLD_MAX_X (WORLD_W_PX - SCREEN_W)

#define HOME_BASE_X 3840
#define HOME_PAD_MIN_X 3780
#define HOME_PAD_MAX_X 3960

#define GROUND_Y 186
#define CEILING_Y 24

#define MAX_CARGO 16
#define TOTAL_HOSTAGES 64
#define STARTING_LIVES 3

typedef enum
{
    GS_TITLE,
    GS_PLAY,
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
extern uint8_t saved_count;
extern uint8_t lost_count;
extern uint8_t cargo_count;
extern int32_t camera_x; // In subpixels
extern uint16_t game_timer;
extern uint8_t current_level;
extern uint8_t frame_count;

void add_score(uint16_t pts);
void hiscore_load(void);
void hiscore_save(void);

void rng_seed(uint16_t seed);
uint16_t rng_next(void);
uint8_t rng_range8(uint8_t min, uint8_t max);

#endif /* GAME_H */
