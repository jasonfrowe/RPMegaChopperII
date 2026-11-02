#ifndef COMPOUNDS_H
#define COMPOUNDS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"

typedef struct
{
    bool breached;
    uint8_t hostages_remaining; /* still inside */
    uint8_t spawn_timer;
} compound_t;

extern compound_t compounds[NUM_COMPOUNDS];

void compounds_init(void);
void compounds_update(void);
void compounds_render(void);
/* How many hostages have come out of the prisons so far. */
uint8_t compounds_freed(void);
/* A shot or bomb at world (x, y). A hit on the door blows it open; a bomb
 * on the roof above the door does too. True if the shot stops there. */
bool compounds_check_hit(int16_t x, int16_t y, bool bomb);

#endif /* COMPOUNDS_H */
