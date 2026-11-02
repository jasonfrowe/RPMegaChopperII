#include "fx.h"
#include "game.h"
#include "sprites.h"
#include "xram.h"

/* Each flake drifts down and sideways on the wind, and slides against the
 * camera by its depth, so near flakes rush past and far ones barely move. */
typedef struct
{
    int16_t x, y; /* screen, 1/16 px */
    int8_t vx;
    uint8_t vy;
    uint8_t depth; /* 1 far .. 4 near */
    uint8_t frame;
    uint8_t phase;
} flake_t;

static flake_t flakes[SPR_SNOW_COUNT];

static void respawn(flake_t *f, bool anywhere)
{
    f->x = (int16_t)(rng_next() % (SCREEN_W << 4));
    f->y = anywhere ? (int16_t)(HUD_H * 16 + rng_next() % ((SCREEN_H - HUD_H) << 4)) : (int16_t)(HUD_H * 16 - 64);
    f->depth = rng_range8(1, 4);
    f->vy = (uint8_t)(4 + f->depth * 3 + (rng_next() & 3));
    f->vx = (int8_t)(-2 - (rng_next() & 3));
    f->frame = f->depth >= 3 ? 0 : (f->depth == 2 ? 2 : 1);
    f->phase = (uint8_t)rng_next();
}

void snow_init(void)
{
    for (uint8_t i = 0; i < SPR_SNOW_COUNT; i++)
        respawn(&flakes[i], true);
}

void snow_update(int16_t camera_dx)
{
    for (uint8_t i = 0; i < SPR_SNOW_COUNT; i++) {
        flake_t *f = &flakes[i];
        f->phase++;
        int8_t sway = (f->phase & 64) ? 1 : -1;
        f->x += f->vx + sway - camera_dx * f->depth * 4;
        f->y += f->vy;
        if (f->x < -64)
            f->x += SCREEN_W << 4;
        else if (f->x >= (SCREEN_W << 4))
            f->x -= SCREEN_W << 4;
        if (f->y >= (GROUND_LINE + 8) << 4)
            respawn(f, false);
    }
}

void snow_render(void)
{
    for (uint8_t i = 0; i < SPR_SNOW_COUNT; i++) {
        flake_t *f = &flakes[i];
        spr_place(SPR_SNOW_START + i, XRAM_IMG_SNOW + f->frame * SNOW_FRAME_BYTES, PAL_SNOW, WH(4, 4), OPT4,
                  f->x >> 4, f->y >> 4);
    }
}
