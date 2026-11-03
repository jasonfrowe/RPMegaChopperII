#include "fx.h"
#include "game.h"
#include "sprites.h"
#include "weather.h"
#include "xram.h"

/* Each flake drifts down and sideways on the wind, and slides against the
 * camera by its depth, so near flakes rush past and far ones barely move.
 * In a storm more of them fall, faster, blown along by the wind, and the
 * near ones become streaks. */
typedef struct
{
    int16_t x, y; /* screen, 1/16 px */
    int8_t vx;
    uint8_t vy;
    uint8_t depth; /* 1 far .. 4 near */
    uint8_t frame;
    uint8_t phase;
} flake_t;

#define CALM_FLAKES 12
#define SNOW_STREAK 3 /* frame */

static flake_t flakes[SPR_SNOW_COUNT];

static void respawn(flake_t *f, bool anywhere)
{
    f->depth = rng_range8(1, 4);
    f->vy = (uint8_t)(4 + f->depth * 3 + (rng_next() & 3));
    f->vx = (int8_t)(-2 - (rng_next() & 3));
    f->frame = f->depth >= 3 ? 0 : (f->depth == 2 ? 2 : 1);
    f->phase = (uint8_t)rng_next();
    f->x = (int16_t)(rng_next() % (SCREEN_W << 4));
    if (anywhere)
        f->y = (int16_t)(HUD_H * 16 + rng_next() % ((SCREEN_H - HUD_H) << 4));
    else if (storm > 4 && rng_coin()) {
        /* Blown in from the side the wind comes from. */
        f->x = wind > 0 ? -64 : (SCREEN_W << 4) - 1;
        f->y = (int16_t)(HUD_H * 16 + rng_next() % ((GROUND_LINE - HUD_H) << 4));
    } else
        f->y = (int16_t)(HUD_H * 16 - 64);
}

void snow_init(void)
{
    for (uint8_t i = 0; i < SPR_SNOW_COUNT; i++)
        respawn(&flakes[i], true);
}

static uint8_t active; /* how many flakes are falling: more in a storm */

void snow_update(int16_t camera_dx)
{
    active = CALM_FLAKES + (uint8_t)((SPR_SNOW_COUNT - CALM_FLAKES) * storm / STORM_MAX);
    /* How far a flake of each depth moves across this frame: the wind blows
     * near ones hardest, and they slide against the camera by their depth. */
    int16_t across[5];
    for (uint8_t d = 1; d <= 4; d++)
        across[d] = wind * (2 + d) - camera_dx * d * 4;
    uint8_t fall = storm >> 1;
    for (uint8_t i = 0; i < active; i++) {
        flake_t *f = &flakes[i];
        f->phase++;
        f->x += f->vx + ((f->phase & 64) ? 1 : -1) + across[f->depth];
        f->y += f->vy + fall;
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
        if (i >= active) {
            spr_hide(SPR_SNOW_START + i);
            continue;
        }
        uint8_t opt = wind < 0 ? OPT4_FLIP : OPT4;
        if (storm > 6 && f->depth >= 3) {
            /* Near the eye in a storm: a whole cluster of driven snow. */
            spr_place(SPR_SNOW_START + i, XRAM_IMG_GUST + (i & 1) * GUST_FRAME_BYTES, PAL_SNOW, WH(16, 8), opt,
                      f->x >> 4, f->y >> 4);
            continue;
        }
        uint8_t frame = storm > 6 ? SNOW_STREAK : f->frame;
        spr_place(SPR_SNOW_START + i, XRAM_IMG_SNOW + frame * SNOW_FRAME_BYTES, PAL_SNOW, WH(4, 4),
                  storm > 6 ? opt : OPT4, f->x >> 4, f->y >> 4);
    }
}
