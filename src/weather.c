#include "game.h"
#include "hud.h"
#include "level.h"
#include "sfx.h"
#include "weather.h"

uint8_t storm;
int8_t wind;
int8_t lift;
volatile uint8_t debug_storm;

enum
{
    W_CALM,
    W_BUILD,
    W_BLOW,
    W_CLEAR
};

#define BUILD_STEP 12      /* frames per step of STORM_MAX while building or clearing */
#define WIND_MAX 7         /* subpixels per frame at full strength, between gusts */
#define LIFT_MAX 16        /* subpixels per frame of up- or downdraft at full strength:
                            * holding up still climbs (20 - 16), letting go drops fast */

static uint8_t phase;
static uint16_t timer;
static int8_t wind_dir;
static uint8_t peak; /* how strong this sector's storms get */
static uint8_t gust;
static uint8_t draft;

static uint16_t frames_between(uint16_t lo, uint16_t span)
{
    return lo + rng_next() % span;
}

void weather_init(void)
{
    storm = 0;
    wind = 0;
    lift = 0;
    phase = W_CALM;
    timer = frames_between(60 * 60, 30 * 60); /* the first one after a minute or more */
    /* Milder in the first sectors. */
    peak = level->storm_peak;
}

void weather_update(void)
{
    if (debug_storm) {
        peak = debug_storm;
        debug_storm = 0;
        phase = W_CALM;
        timer = 1;
    }
    switch (phase) {
    case W_CALM:
        if (--timer == 0) {
            phase = W_BUILD;
            timer = BUILD_STEP;
            wind_dir = rng_coin() ? 1 : -1;
            msg_flash(wind_dir > 0 ? "BLIZZARD! WIND FROM THE WEST" : "BLIZZARD! WIND FROM THE EAST", C_CYAN, 150);
            sfx_enemy(SFX_WARNING, SFX_PRI_EVENT);
        }
        break;
    case W_BUILD:
        if (--timer == 0) {
            timer = BUILD_STEP;
            if (++storm >= peak) {
                phase = W_BLOW;
                timer = frames_between(15 * 60, 10 * 60);
            }
        }
        break;
    case W_BLOW:
        if (--timer == 0) {
            phase = W_CLEAR;
            timer = BUILD_STEP;
        }
        break;
    case W_CLEAR:
        if (--timer == 0) {
            timer = BUILD_STEP;
            if (storm)
                storm--;
            if (!storm) {
                phase = W_CALM;
                timer = frames_between(45 * 60, 45 * 60);
            }
        }
        break;
    }

    /* Gusts: the wind swells and drops over about two seconds. */
    gust++;
    uint8_t g = (gust & 0x40) ? 0x3F - (gust & 0x3F) : (gust & 0x3F); /* 0..63..0 */
    /* At full strength 7 subpixels a frame, gusting to 14: about a quarter
     * of the chopper's top speed at worst. */
    int16_t w = (int16_t)storm * WIND_MAX * (64 + g) / (64 * STORM_MAX);
    wind = (int8_t)(wind_dir * w);

    /* Up- and downdrafts swing on a different beat, about every 3 s, and
     * jolt: the swing is squared so it lingers near the top and bottom.
     * A downdraft is a little stronger than gravity and the climb together
     * is weak, so in the worst of it the chopper fights to hold height. */
    draft += 3;
    int8_t tri = (int8_t)((draft & 0x80) ? 0xFF - draft : draft) - 64; /* -64..63 */
    int16_t sq = (int16_t)tri * (tri < 0 ? -tri : tri) / 64;            /* -64..63, squared */
    lift = (int8_t)((int16_t)storm * LIFT_MAX * sq / (64 * STORM_MAX));
}
