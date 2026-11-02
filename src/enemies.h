#ifndef ENEMIES_H
#define ENEMIES_H

#include <stdint.h>
#include <stdbool.h>

void enemies_init(void);
void enemies_update(void);
void enemies_render(void);
/* A shot at world (x, y). True if it hit something. */
bool tanks_check_hit(int16_t x, int16_t y);
bool jets_check_hit(int16_t x, int16_t y);
bool balloons_check_hit(int16_t x, int16_t y);

#endif /* ENEMIES_H */
