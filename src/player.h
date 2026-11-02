#ifndef PLAYER_H
#define PLAYER_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"

typedef enum
{
    PL_ALIVE,
    PL_LANDED,
    PL_CRASHING,
    PL_RESPAWN_WAIT
} player_status_t;

extern int32_t chopper_world_x; /* subpixels, left edge of the sprite */
extern int32_t chopper_y;       /* subpixels, top of the sprite */
extern int16_t chopper_vel_x;
extern int16_t chopper_vel_y;
extern chopper_heading_t chopper_heading;
extern player_status_t player_status;
extern bool chopper_is_landed;
/* For test scripts (tools/playtest.py), which write them from outside:
 * no damage, and a request to move the chopper to (warp_x, warp_y). */
extern volatile bool chopper_invulnerable;
extern volatile int16_t debug_warp_x, debug_warp_y;

void player_init(void);
void player_update(void);
void player_render(void);
void player_kill(void);

/* Is the chopper flying (or sitting) and able to be hit? */
static inline bool player_alive(void)
{
    return player_status == PL_ALIVE || player_status == PL_LANDED;
}

/* World x of the chopper's middle. */
static inline int16_t chopper_cx(void)
{
    return FROM_SUB(chopper_world_x) + CHOPPER_W / 2;
}

#endif /* PLAYER_H */
