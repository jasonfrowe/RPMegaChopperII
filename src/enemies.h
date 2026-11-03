#ifndef ENEMIES_H
#define ENEMIES_H

#include <stdint.h>
#include <stdbool.h>

void enemies_init(void);
void enemies_update(void);
void enemies_render(void);
/* A bomb bursting at world x, at tank depth if deep: destroys what is
 * there (a tank or jeep only if deep; a turret or a tunnelling worm
 * either way). */
void enemies_bomb(int16_t x, bool deep);
/* A bomb still falling, its tip at world (x, y): true if it hit something
 * on the way down (a launcher on a roof), and burst there. */
bool enemies_bomb_falling(int16_t x, int16_t y);
/* A cannon shot at world (x, y): the jet, the balloon, a jeep, a turret
 * or a worm out of the ground. True if it hit. */
bool enemies_check_hit(int16_t x, int16_t y);

#endif /* ENEMIES_H */
