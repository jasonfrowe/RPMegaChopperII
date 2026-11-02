#ifndef SFX_H
#define SFX_H

#include <stdint.h>
#include "gen/sfx_ids.h"

/* Priorities within a channel: a lower one never cuts off a higher one. */
#define SFX_PRI_FIRE 1
#define SFX_PRI_DESTROY 2
#define SFX_PRI_EVENT 3
#define SFX_PRI_TOP 4

void sfx_init(void);
void sfx_player(uint8_t id, uint8_t priority); /* OPL2 channel 7 */
void sfx_enemy(uint8_t id, uint8_t priority);  /* OPL2 channel 8 */
void sfx_update(void);

#endif
