#ifndef BG_H
#define BG_H

#include <stdint.h>
#include <stdbool.h>

void bg_init(void);
void bg_update(int16_t camera_x_px);
void bg_commit(void);
void bg_breach_bunker(uint8_t base_col);
void bg_reset_bunkers(void);

#endif /* BG_H */
