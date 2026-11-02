#ifndef GAME_HOSTAGES_H
#define GAME_HOSTAGES_H

#include <stdint.h>
#include <stdbool.h>

/* Hostages out in the snow. Those aboard are only counted (cargo_count),
 * but out and aboard together never pass MAX_ACTIVE_HOSTAGES, as in the
 * original, where a hostage kept its slot while aboard. */
#define MAX_ACTIVE_HOSTAGES 16

typedef enum
{
    H_INACTIVE,
    H_OUT,     /* out of the prison: waiting, or running for a low chopper */
    H_TO_BASE, /* let off at home, running for the door */
    H_WAVE,    /* the last one off, waving at the door before going in */
} hostage_state_t;

typedef struct
{
    hostage_state_t state;
    int32_t world_x; /* subpixels, left edge of the 16-pixel sprite */
    uint8_t home;    /* prison it came from */
    uint8_t spot;    /* where it waits: the order it came out in */
    uint8_t anim;
    uint8_t timer;
    int8_t move;     /* -1, 0 or 1: how it moved last frame */
    bool left;       /* facing left */
} hostage_t;

extern hostage_t hostages[MAX_ACTIVE_HOSTAGES];

void hostages_init(void);
/* A hostage steps out of prison `home`'s door at world x, if it can. */
bool hostages_spawn(uint8_t home, int16_t x);
void hostages_update(void);
void hostages_render(void);
/* A cannon shot, or a falling shell, at world (x, y): kills a hostage there. */
bool hostages_check_hit(int16_t x, int16_t y);

#endif /* GAME_HOSTAGES_H */
