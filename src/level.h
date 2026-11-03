#ifndef LEVEL_H
#define LEVEL_H

#include <stdbool.h>
#include <stdint.h>

/* The levels, in order. After the last the game goes round again, harder
 * (a "lap"): sector LEVEL_BANKS + 1 is level 1 again. */
enum
{
    THEME_TUNDRA, /* tanks, the balloon, jets */
    THEME_BOREAL  /* jeeps, rocket turrets, worms */
};

/* What changes from level to level and lap to lap. Times in frames. */
typedef struct
{
    const char *bank;  /* its art: enemies, tiles, maps, palettes */
    const char *music;
    const char *name;  /* shown under the sector number */
    uint16_t first_vehicle[4]; /* after each prison is opened, in order, its first tank or jeep shows */
    uint8_t air_trigger;       /* prisons opened before jets or worms come */
    uint8_t storm_peak;        /* how strong the storms get (STORM_MAX at most) */
} level_t;

extern uint8_t level_theme; /* THEME_*: which bank, and which enemies */
extern uint8_t level_lap;   /* 0 the first time round */
extern const level_t *level;

/* Point at current_level's settings and load its bank into XRAM (only if
 * another level's is there). The screen goes dark while it loads. */
void level_enter(uint8_t sector);

#endif /* LEVEL_H */
