#ifndef INPUT_H
#define INPUT_H

#include <stdint.h>

#define IN_UP 0x0001
#define IN_DOWN 0x0002
#define IN_LEFT 0x0004
#define IN_RIGHT 0x0008
#define IN_FIRE 0x0010
#define IN_ROTATE 0x0020
#define IN_START 0x0040

extern uint16_t in_held;
extern uint16_t in_pressed; /* Went down this frame */

void input_init(void);
void input_update(void);

#endif /* INPUT_H */
