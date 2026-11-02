#include <rp6502.h>
#include <stdbool.h>
#include "opl.h"
#include "xram.h"

#define SFX_OFFSETS
#include "sfx.h"

/*
 * Sound effects play from XRAM, where the ROM loads tools/gen_sfx.py's
 * blob. Each is a stream of 0x5A reg val (write), 0x61 lo hi (wait in
 * 44.1 kHz samples) and 0x66 (end). Two channels, each with its own
 * priority, so enemy noise never cuts off the player's own sounds.
 * Adapted from RPDemo's sfx.c.
 */

#define SAMPLES_PER_FRAME 735u

_Static_assert(SFX_BLOB_SIZE <= SFX_DATA_MAX, "Grow SFX_DATA_MAX in xram.h");

typedef struct
{
    uint16_t ptr;
    uint16_t wait;
    uint8_t priority; /* 0 when idle */
    uint8_t key_reg;
    bool triggered; /* already started a sound this frame */
} channel_t;

static channel_t ch_player = {.key_reg = 0xB7};
static channel_t ch_enemy = {.key_reg = 0xB8};

void sfx_init(void)
{
    ch_player.priority = ch_enemy.priority = 0;
}

static void play(channel_t *c, uint8_t id, uint8_t priority)
{
    if (c->priority && priority < c->priority)
        return;
    if (c->triggered && priority <= c->priority)
        return;
    c->triggered = true;
    opl_write(c->key_reg, 0); /* release whatever was sounding */
    c->ptr = XRAM_SFX_DATA + sfx_offsets[id];
    c->wait = 0;
    c->priority = priority;
}

void sfx_player(uint8_t id, uint8_t priority)
{
    play(&ch_player, id, priority);
}

void sfx_enemy(uint8_t id, uint8_t priority)
{
    play(&ch_enemy, id, priority);
}

static void advance(channel_t *c)
{
    c->triggered = false;
    if (!c->priority)
        return;
    uint16_t budget = SAMPLES_PER_FRAME;
    while (budget) {
        if (c->wait) {
            uint16_t step = c->wait > budget ? budget : c->wait;
            c->wait -= step;
            budget -= step;
            continue;
        }
        uint8_t cmd = xram0_peek8(c->ptr);
        uint16_t arg = xram0_peek16(c->ptr + 1);
        if (cmd == 0x5A) {
            opl_write((uint8_t)arg, (uint8_t)(arg >> 8));
            c->ptr += 3;
        } else if (cmd == 0x61) {
            c->wait = arg;
            c->ptr += 3;
        } else {
            c->priority = 0;
            return;
        }
    }
}

void sfx_update(void)
{
    advance(&ch_player);
    advance(&ch_enemy);
}
