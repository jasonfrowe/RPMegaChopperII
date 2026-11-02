#ifndef GAME_HOSTAGES_H
#define GAME_HOSTAGES_H

#include <stdint.h>
#include <stdbool.h>

#define MAX_ACTIVE_HOSTAGES 16

typedef enum
{
    H_INACTIVE,
    H_RUN_TO_CHOPPER,
    H_WAVING,
    H_BOARDING,
    H_RUN_TO_BASE,
    H_DEAD
} hostage_state_t;

typedef struct
{
    hostage_state_t state;
    int32_t world_x; // Subpixels
    int16_t y;       // Pixels (ground Y is ~188)
    int8_t dir;      // -1 = Left, 1 = Right
    uint8_t anim_frame;
    uint8_t timer;
} hostage_t;

extern hostage_t hostages[MAX_ACTIVE_HOSTAGES];

void hostages_init(void);
bool hostages_spawn(int16_t x, int16_t y);
void hostages_update(void);
void hostages_render(void);
void hostages_disembark_all(void);
bool hostages_check_hit(int16_t hit_x, int16_t hit_y);

#endif /* GAME_HOSTAGES_H */
