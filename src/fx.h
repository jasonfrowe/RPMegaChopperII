#ifndef FX_H
#define FX_H

#include <stdint.h>

/* Falling snow, drawn in front of everything. */
void snow_init(void);
void snow_update(int16_t camera_dx);
void snow_render(void);

#endif /* FX_H */
