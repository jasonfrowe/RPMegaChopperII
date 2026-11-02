#ifndef ENEMIES_H
#define ENEMIES_H

#include <stdint.h>
#include <stdbool.h>

void enemies_init(void);
void enemies_reset(void);
void enemies_update(void);
void enemies_render(void);

bool tanks_check_hit(int16_t hit_x, int16_t hit_y);
bool jets_check_hit(int16_t hit_x, int16_t hit_y);
bool balloons_check_hit(int16_t hit_x, int16_t hit_y);

#endif /* ENEMIES_H */
