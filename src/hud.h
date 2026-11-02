#ifndef HUD_H
#define HUD_H

#include <stdint.h>
#include <stdbool.h>

void hud_init(void);
void hud_clear(void);
void hud_text(uint8_t col, uint8_t row, const char *str, uint8_t fg, uint8_t bg);
void hud_u16(uint8_t col, uint8_t row, uint16_t val, uint8_t width, uint8_t fg, uint8_t bg);
void hud_u32(uint8_t col, uint8_t row, uint32_t val, uint8_t width, uint8_t fg, uint8_t bg);
void hud_update(void);
void hud_commit(void);

#endif /* HUD_H */
