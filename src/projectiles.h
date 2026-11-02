#ifndef PROJECTILES_H
#define PROJECTILES_H

#include <stdint.h>
#include <stdbool.h>

void projectiles_init(void);
void projectiles_update(void);
void projectiles_render(void);

void bullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy);
void bomb_spawn(int16_t x, int16_t y, int16_t vx);
void ebullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy);

void explosion_spawn(int16_t screen_x, int16_t screen_y, bool is_big);
void small_explosion_spawn(int16_t screen_x, int16_t screen_y);

#endif /* PROJECTILES_H */
