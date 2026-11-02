#include <rp6502.h>
#include "hidkeys.h"
#include "input.h"
#include "xram.h"

uint16_t in_held;
uint16_t in_pressed;

static keyboard_t kb;

typedef struct
{
    uint8_t key;
    uint16_t bits;
} keymap_t;

static const keymap_t keymap[] = {
    {HID_KEY_ARROW_UP, IN_UP},
    {HID_KEY_ARROW_DOWN, IN_DOWN},
    {HID_KEY_ARROW_LEFT, IN_LEFT},
    {HID_KEY_ARROW_RIGHT, IN_RIGHT},
    {HID_KEY_W, IN_UP},
    {HID_KEY_S, IN_DOWN},
    {HID_KEY_A, IN_LEFT},
    {HID_KEY_D, IN_RIGHT},
    {HID_KEY_Z, IN_FIRE},
    {HID_KEY_J, IN_FIRE},
    {HID_KEY_SPACE, IN_FIRE},
    {HID_KEY_X, IN_ROTATE},
    {HID_KEY_K, IN_ROTATE},
    {HID_KEY_C, IN_ROTATE},
    {HID_KEY_ENTER, IN_START},
    {HID_KEY_P, IN_START},
};

static const struct
{
    uint8_t field; /* 2 = BTN0, 3 = BTN1 */
    uint8_t mask;
    uint16_t bits;
} padmap[] = {
    {2, GAMEPAD_BTN0_A, IN_FIRE},
    {2, GAMEPAD_BTN0_R1, IN_FIRE},
    {2, GAMEPAD_BTN0_B, IN_ROTATE},
    {2, GAMEPAD_BTN0_C, IN_ROTATE},
    {2, GAMEPAD_BTN0_X, IN_ROTATE},
    {2, GAMEPAD_BTN0_L1, IN_ROTATE},
    {3, GAMEPAD_BTN1_START, IN_START},
    {3, GAMEPAD_BTN1_SELECT, IN_START},
};

void input_init(void)
{
    xreg_ria_keyboard(XRAM_KEYBOARD);
    xreg_ria_gamepad(XRAM_GAMEPAD);
    in_held = 0;
    in_pressed = 0;
}

void input_update(void)
{
    uint16_t held = 0;

    xram0_read(&kb, XRAM_KEYBOARD, sizeof(kb));
    if (!KEYBOARD_PRESSED(kb.keys, KEYBOARD_NO_KEY)) {
        for (uint8_t i = 0; i < sizeof(keymap) / sizeof(keymap[0]); i++) {
            if (KEYBOARD_PRESSED(kb.keys, keymap[i].key))
                held |= keymap[i].bits;
        }
    }

    uint8_t pad[4];
    xram0_read(pad, XRAM_GAMEPAD, 4);
    if (pad[0] & GAMEPAD_FEAT_CONNECTED) {
        held |= (uint8_t)((pad[0] | pad[1]) & 0x0F);
        for (uint8_t i = 0; i < sizeof(padmap) / sizeof(padmap[0]); i++) {
            if (pad[padmap[i].field] & padmap[i].mask)
                held |= padmap[i].bits;
        }
    }

    in_pressed = (uint16_t)(held & ~in_held);
    in_held = held;
}
