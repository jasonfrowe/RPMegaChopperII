#ifndef BG_H
#define BG_H

#include <stdint.h>
#include <stdbool.h>

void bg_init(void);
void bg_update(int16_t camera_x_px);
/* Read the palettes as built; call once they are in XRAM. */
void bg_palettes_init(void);
/* Animate the palettes, and fade them by the storm (0..STORM_MAX). */
void bg_animate(uint8_t storm_level);
void bg_commit(void);
void bg_breach_door(uint8_t compound);
void bg_reset_doors(void);

#endif /* BG_H */
