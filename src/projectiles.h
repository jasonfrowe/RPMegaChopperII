#ifndef PROJECTILES_H
#define PROJECTILES_H

#include <stdint.h>
#include <stdbool.h>

void projectiles_init(void);
void projectiles_update(void);
void projectiles_render(void);

/* Positions are world pixels; velocities subpixels per frame. */
void bullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy);
void bomb_spawn(int16_t x, int16_t y, int16_t vx);
/* Enemy fire: tank flak arcs under gravity and can come down on
 * hostages; a jet's shot flies straight; a jet's bomb falls. */
enum { EB_FLAK, EB_SHOT, EB_BOMB };
void ebullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy, uint8_t kind);
/* Explosions are centered on a world point. */
void explosion_spawn(int16_t cx, int16_t cy, bool big);
void small_explosion_spawn(int16_t cx, int16_t cy);

#endif /* PROJECTILES_H */
