#include <rp6502.h>
#include <fcntl.h>
#include <stdbool.h>
#include <unistd.h>
#include "bg.h"
#include "compounds.h"
#include "enemies.h"
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "input.h"
#include "music.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "xram.h"

#define HISCORE_FILE "chopper2.dat"

game_state_t gstate;
uint32_t score;
uint32_t hiscore;
uint8_t lives;
uint8_t current_level = 1;
uint8_t saved_count;
uint8_t lost_count;
uint8_t cargo_count;
int32_t camera_x;
uint16_t game_timer;
uint8_t frame_count;
volatile uint16_t lag_frames;

static uint32_t next_extend = 10000;
static uint32_t clear_bonus = 0;
static uint16_t lfsr_state = 0xACE1u;

void rng_seed(uint16_t seed)
{
    if (seed == 0) seed = 0xACE1u;
    lfsr_state = seed;
}

uint16_t rng_next(void)
{
    uint16_t bit = ((lfsr_state >> 0) ^ (lfsr_state >> 2) ^ (lfsr_state >> 3) ^ (lfsr_state >> 5)) & 1u;
    lfsr_state = (lfsr_state >> 1) | (bit << 15);
    return lfsr_state;
}

uint8_t rng_range8(uint8_t min, uint8_t max)
{
    if (max <= min) return min;
    return min + (uint8_t)(rng_next() % (max - min + 1));
}

void add_score(uint16_t pts)
{
    score += pts;
    if (score >= next_extend) {
        if (lives < 9) {
            lives++;
            sfx_player(SFX_EXTEND, SFX_PRI_TOP);
        }
        next_extend += 10000;
    }
}

void hiscore_load(void)
{
    int fd = open(HISCORE_FILE, O_RDONLY);
    if (fd < 0) {
        hiscore = 10000;
        return;
    }
    if (read(fd, &hiscore, sizeof(hiscore)) != (int)sizeof(hiscore)) {
        hiscore = 10000;
    }
    close(fd);
}

void hiscore_save(void)
{
    int fd = open(HISCORE_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        return;
    }
    (void)write(fd, &hiscore, sizeof(hiscore));
    close(fd);
}

static void enter_title(void)
{
    gstate = GS_TITLE;
    game_timer = 0;
    spr_hide_all();
    spr_commit();
    music_play("ROM:Title.vgm");

    hud_clear();
    hud_text(4, 0, "RPMEGACHOPPER II: NORTHERN LIGHTS", 8, 1);
    hud_text(6, 1, "PRESS FIRE OR START TO RESCUE", 10, 1);
    hud_commit();
}

static void start_level(uint8_t lvl)
{
    gstate = GS_PLAY;
    game_timer = 0;
    saved_count = 0;
    lost_count = 0;
    cargo_count = 0;
    current_level = lvl;

    player_init();
    bg_reset_bunkers();
    compounds_init();
    hostages_init();
    enemies_init();
    projectiles_init();

    hud_clear();
    hud_update();
    hud_commit();

    /* Start the fast, driving Airwolf soundtrack! */
    music_play("ROM:Stage1.vgm");
}

static void enter_play(void)
{
    score = 0;
    lives = STARTING_LIVES;
    next_extend = 10000;
    start_level(1);
}

static void enter_level_clear(void)
{
    gstate = GS_LEVEL_CLEAR;
    game_timer = 0;
    music_play_once("ROM:Victory.vgm");

    /* Hostage rescue bonus: 500 pts per saved hostage */
    clear_bonus = (uint32_t)saved_count * 500;
    add_score(clear_bonus);

    if (score > hiscore) {
        hiscore = score;
        hiscore_save();
    }

    hud_clear();
    hud_text(6, 0, "MISSION ACCOMPLISHED! ALL CLEAR", 10, 1);
    hud_text(3, 1, "SAVED:   /64  BONUS:+      PTS", 8, 1);
    hud_u16(10, 1, saved_count, 2, 7, 1);
    hud_u32(22, 1, clear_bonus, 5, 10, 1);
    hud_commit();
}

static void enter_gameover(void)
{
    gstate = GS_GAMEOVER;
    game_timer = 0;
    if (score > hiscore) {
        hiscore = score;
        hiscore_save();
    }
    music_play_once("ROM:Gameover.vgm");

    hud_clear();
    hud_text(11, 0, "M I S S I O N   F A I L E D", 9, 1);
    hud_text(7, 1, "GAME OVER - PRESS FIRE OR START", 7, 1);
    hud_commit();
}

int main(void)
{
    xreg_vga_canvas(CANVAS_320X240);
    input_init();
    spr_init();
    bg_init();
    hud_init();
    music_init();
    sfx_init();
    hiscore_load();
    rng_seed(ria_vsync());

    enter_title();

    uint8_t vs = ria_vsync();
    while (1) {
        uint8_t now;
        while ((now = ria_vsync()) == vs)
            ;
        if ((uint8_t)(now - vs) > 1)
            lag_frames++;
        vs = now;

        /* Hardware commits immediately following VSYNC */
        spr_commit();
        bg_commit();
        hud_commit();

        /* Audio & Input polling */
        music_update();
        sfx_update();
        input_update();
        frame_count++;

        switch (gstate) {
        case GS_TITLE:
            game_timer++;
            if ((game_timer & 128) == 0) {
                if (game_timer & 32) {
                    hud_text(6, 1, "PRESS FIRE OR START TO RESCUE", 10, 1);
                } else {
                    hud_text(6, 1, "                             ", 10, 1);
                }
            } else {
                hud_text(6, 1, "   HIGH SCORE:        PTS    ", 13, 1);
                hud_u32(21, 1, hiscore, 6, 8, 1);
            }
            if (in_pressed & (IN_FIRE | IN_START)) {
                enter_play();
            }
            break;

        case GS_PLAY:
            player_update();
            compounds_update();
            hostages_update();
            enemies_update();
            projectiles_update();

            /* Update dual-layer parallax scroll */
            bg_update(FROM_SUB(camera_x));

            /* Render active actors to sprite RAM mirror */
            player_render();
            compounds_render();
            hostages_render();
            enemies_render();
            projectiles_render();

            /* Update HUD status & radar */
            hud_update();

            /* Check Game Over or Stage Clear */
            if (player_status == PL_RESPAWN_WAIT && lives == 0) {
                enter_gameover();
            } else if (saved_count + lost_count >= TOTAL_HOSTAGES) {
                enter_level_clear();
            }
            break;

        case GS_LEVEL_CLEAR:
            game_timer++;
            if (game_timer > 90) {
                if (game_timer & 32) {
                    hud_text(3, 1, " PRESS FIRE TO ADVANCE SECTOR ", 10, 1);
                } else {
                    hud_text(3, 1, "SAVED:   /64  BONUS:+      PTS", 8, 1);
                    hud_u16(10, 1, saved_count, 2, 7, 1);
                    hud_u32(22, 1, clear_bonus, 5, 10, 1);
                }
            }
            if (game_timer > 60 && (in_pressed & (IN_FIRE | IN_START))) {
                start_level(current_level + 1);
            }
            break;

        case GS_GAMEOVER:
            game_timer++;
            if (game_timer > 90 && (in_pressed & (IN_FIRE | IN_START))) {
                enter_title();
            }
            break;
        }
    }
}
