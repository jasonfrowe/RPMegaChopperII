#include <rp6502.h>
#include <stddef.h>
#include <string.h>
#include "music.h"
#include "opl.h"
#include "vgm.h"
#include "xram.h"

/* Adapted from RPDemo's music.c. */

static vgm_player_t player;
static const char *current;
static bool once; /* stop at the end instead of looping */

void music_init(void)
{
    memset(&player, 0, sizeof(player));
    player.fd = -1;
    current = NULL;
    xreg_ria_opl(XRAM_OPL);
    opl_init();
}

void music_stop(void)
{
    if (player.fd >= 0)
        vgm_close(&player);
    player.fd = -1;
    current = NULL;
    /* Key off the seven music channels; 7 and 8 belong to the SFX. */
    for (uint8_t ch = 0; ch < 7; ch++)
        opl_write((uint8_t)(0xB0 + ch), 0);
}

void music_play(const char *path)
{
    if (path && current && strcmp(path, current) == 0)
        return;
    music_stop();
    once = false;
    if (!path)
        return;
    if (vgm_open(&player, path))
        current = path;
}

void music_play_once(const char *path)
{
    music_play(path);
    once = true;
}

void music_update(void)
{
    bool ended = false;
    if (player.fd < 0)
        return;
    vgm_update(&player, 735u, &ended);
    if (ended && (once || !vgm_restart(&player)))
        music_stop();
}
