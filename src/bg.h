#ifndef BG_H
#define BG_H

#include <stdint.h>
#include <stdbool.h>

void bg_init(void);
void bg_update(int16_t camera_x_px);
void bg_animate(void);
void bg_commit(void);
void bg_breach_door(uint8_t compound);
void bg_reset_doors(void);

#endif /* BG_H */
