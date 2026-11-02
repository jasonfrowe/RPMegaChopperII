#ifndef GAME_HOSTAGES_H
#define GAME_HOSTAGES_H

#include <stdint.h>
#include <stdbool.h>

#define MAX_ACTIVE_HOSTAGES 16

typedef enum
{
    H_INACTIVE,
    H_WAIT,     /* out of the prison, milling about near it */
    H_TO_CHOPPER,
    H_TO_BASE,  /* dropped off, running for the hangar */
    H_CHEER,    /* at the hangar door, about to go in */
} hostage_state_t;

typedef struct
{
    hostage_state_t state;
    int32_t world_x; /* subpixels, left edge of the 16-pixel sprite */
    int16_t target;  /* world x the hostage is heading for */
    uint8_t home;    /* compound it came from */
    uint8_t spot;    /* where it waits outside: the order it came out in */
    uint8_t anim;
    uint8_t timer;
    int8_t move;     /* -1, 0 or 1: how it moved last frame */
    bool left;       /* facing left */
} hostage_t;

extern hostage_t hostages[MAX_ACTIVE_HOSTAGES];

void hostages_init(void);
/* A hostage steps out of compound `home`'s door at world x. */
bool hostages_spawn(uint8_t home, int16_t x);
void hostages_update(void);
void hostages_render(void);
/* A shot at world (x, y): kills a hostage there. */
bool hostages_check_hit(int16_t x, int16_t y);
/* The chopper went down: anyone running to it goes back to waiting. */
void hostages_scatter(void);

#endif /* GAME_HOSTAGES_H */
