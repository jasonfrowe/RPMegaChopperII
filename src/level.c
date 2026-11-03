#include <rp6502.h>
#include <fcntl.h>
#include <unistd.h>
#include "bg.h"
#include "game.h"
#include "level.h"
#include "sprites.h"
#include "xram.h"

/* Each level, then the same again harder each time round. */
static const level_t levels[LEVEL_BANKS][2] = {
    {
        {"ROM:level1.bin", "ROM:Stage1.vgm", "THE TUNDRA", {8 * 60, 6 * 60, 5 * 60, 5 * 60}, 3, 10},
        {"ROM:level1.bin", "ROM:Stage1.vgm", "THE TUNDRA", {6 * 60, 5 * 60, 4 * 60, 4 * 60}, 2, 16},
    },
    {
        {"ROM:level2.bin", "ROM:Stage2.vgm", "THE LAKES", {7 * 60, 5 * 60, 4 * 60, 4 * 60}, 2, 13},
        {"ROM:level2.bin", "ROM:Stage2.vgm", "THE LAKES", {6 * 60, 4 * 60, 3 * 60, 3 * 60}, 1, 16},
    },
};

uint8_t level_theme;
uint8_t level_lap;
const level_t *level = &levels[0][0];

static uint8_t loaded = 0xFF; /* the bank in XRAM */

static void read_run(int fd, uint16_t addr, uint16_t n)
{
    while (n) {
        uint16_t k = n > 0x1000 ? 0x1000 : n;
        if (read_xram(addr, k, fd) <= 0)
            return;
        addr += k;
        n -= k;
    }
}

static void load_bank(uint8_t b)
{
    /* Nothing shows while the tiles change: no sprites, and the three
     * layers' palettes cleared to transparent, so the screen is black
     * behind the text. */
    spr_hide_all();
    spr_commit();
    static const palette_t clear = {{0}};
    xram0_write(PAL_ADDR(PAL_FAR), &clear, sizeof(clear));
    xram0_write(PAL_ADDR(PAL_MID), &clear, sizeof(clear));
    xram0_write(PAL_ADDR(PAL_FG), &clear, sizeof(clear));

    int fd = open(levels[b][0].bank, O_RDONLY);
    if (fd < 0)
        return;
    read_run(fd, XRAM_IMG_ENEMY, ENEMY_IMG_BYTES);
    read_run(fd, XRAM_TILES_FAR, XRAM_LEVEL_TILES_BYTES);
    read_run(fd, XRAM_PALETTES, PAL_COUNT * sizeof(palette_t));
    close(fd);
    loaded = b;
    bg_palettes_init();
}

void level_enter(uint8_t sector)
{
    uint8_t n = sector - 1;
    level_theme = n % LEVEL_BANKS;
    level_lap = n / LEVEL_BANKS;
    level = &levels[level_theme][level_lap ? 1 : 0];
    if (loaded != level_theme)
        load_bank(level_theme);
    bg_reset_doors();
}
