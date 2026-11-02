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

extern int32_t chopper_world_x;
extern int32_t chopper_y;
extern int16_t chopper_vel_x;
extern int16_t chopper_vel_y;
extern chopper_heading_t chopper_heading;
extern player_status_t player_status;
extern bool chopper_is_landed;

void player_init(void);
void player_reset(void);
void player_update(void);
void player_render(void);
void player_kill(void);

#endif /* PLAYER_H */
