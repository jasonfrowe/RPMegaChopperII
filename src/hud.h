#ifndef CHOPPER_HUD_H
#define CHOPPER_HUD_H

#include <stdint.h>
#include <stdbool.h>

/* HUD palette colors */
#define C_PANEL 1
#define C_FRAME 3
#define C_DIM 4
#define C_GREEN 5
#define C_ORANGE 6
#define C_WHITE 7
#define C_GOLD 8
#define C_RED 9
#define C_LGREEN 10
#define C_CYAN 11
#define C_GREY 12
#define C_LAVENDER 13
#define C_AURORA 14
#define C_PINK 15

void hud_init(void);
void hud_clear(void);
void hud_text(uint8_t col, uint8_t row, const char *str, uint8_t fg);
void hud_num(uint8_t col, uint8_t row, uint32_t val, uint8_t width, uint8_t fg);
void hud_update(void);
void hud_commit(void);

/* The message box over the sky: MSG_ROWS lines, transparent behind. */
void msg_clear(void);
void msg_text(uint8_t col, uint8_t row, const char *str, uint8_t fg);
void msg_center(uint8_t row, const char *str, uint8_t fg);
/* A centered line on a dark band the width of the screen. */
void msg_band(uint8_t row, const char *str, uint8_t fg);
void msg_num(uint8_t col, uint8_t row, uint32_t val, uint8_t width, uint8_t fg);
/* A line for a moment; when the time is up the whole box clears. */
void msg_flash(const char *str, uint8_t fg, uint8_t frames);
void msg_tick(void);

#endif /* CHOPPER_HUD_H */
