#ifndef ENEMIES_H
#define ENEMIES_H

#include <stdint.h>
#include <stdbool.h>

void enemies_init(void);
void enemies_update(void);
void enemies_render(void);
/* A bomb bursting at tank depth at world x: destroys a tank there. */
void tanks_bomb(int16_t x);
/* A cannon shot at world (x, y). True if it hit. */
bool jets_check_hit(int16_t x, int16_t y);
bool balloons_check_hit(int16_t x, int16_t y);

#endif /* ENEMIES_H */
