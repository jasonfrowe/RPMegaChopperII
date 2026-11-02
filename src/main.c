#include <rp6502.h>
#include <fcntl.h>
#include <stdbool.h>
#include <unistd.h>
#include "bg.h"
#include "compounds.h"
#include "enemies.h"
#include "fx.h"
#include "game.h"
#include "hostages.h"
#include "hud.h"
#include "input.h"
#include "music.h"
#include "player.h"
#include "projectiles.h"
#include "sfx.h"
#include "sprites.h"
#include "weather.h"
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

/* A copy of the game's numbers for test scripts to read. The game keeps
 * the real ones in registers between frames, so memory can be stale. */
volatile struct
{
    uint8_t state, cargo, saved, lost, lives, breached;
    uint16_t score;
    uint8_t storm;
    uint8_t inside; /* hostages still in the prisons */
} test_stats;

static uint32_t next_extend = 20000;
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
        next_extend += 20000;
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

/* The logo, on the hostage sprites (there are none on the title): for each
 * 64-pixel piece a shadow, a light rim and the face, back to front. */
#define LOGO_X ((SCREEN_W - LOGO_W) / 2)
#define LOGO_Y 42

static void logo_show(void)
{
    static const int8_t off[3][2] = {{2, 2}, {-1, -1}, {0, 0}};
    for (uint8_t pass = 0; pass < 3; pass++)
        for (uint8_t p = 0; p < LOGO_PIECES; p++)
            spr_place(SPR_HOSTAGE_START + pass * LOGO_PIECES + p, XRAM_IMG_LOGO + p * LOGO_PIECE_BYTES, PAL_LOGO,
                      WH(LOGO_PIECE_W, LOGO_H), MODE5_1BPP, LOGO_X + p * LOGO_PIECE_W + off[pass][0],
                      LOGO_Y + off[pass][1]);
    /* Point each pass at its own two colors. */
    for (uint8_t pass = 0; pass < 3; pass++)
        for (uint8_t p = 0; p < LOGO_PIECES; p++)
            spr[SPR_HOSTAGE_START + pass * LOGO_PIECES + p].palette_ptr = PAL_ADDR(PAL_LOGO) + pass * 4;
}

_Static_assert(3 * LOGO_PIECES <= SPR_HOSTAGE_COUNT, "the logo borrows the hostage sprites");

static void enter_title(void)
{
    gstate = GS_TITLE;
    weather_init();
    game_timer = 0;
    spr_hide_all();
    music_play("ROM:Title.vgm");
    compounds_init();
    hostages_init();
    projectiles_init();

    hud_clear();
    hud_text(12, 0, "HIGH SCORE", C_GOLD);
    hud_num(23, 0, hiscore, 6, C_WHITE);
    hud_text(1, 1, "ARROWS FLY   Z FIRE/BOMB   X TURN", C_GREY);
    msg_clear();
    logo_show();
    msg_band(4, "OPERATION  NORTHERN  LIGHTS", C_AURORA);
}

static void start_level(uint8_t lvl)
{
    gstate = GS_PLAY;
    game_timer = 0;
    saved_count = 0;
    lost_count = 0;
    cargo_count = 0;
    current_level = lvl;

    spr_hide_all();
    player_init();
    compounds_init();
    hostages_init();
    enemies_init();
    projectiles_init();
    weather_init();

    hud_clear();
    hud_update();
    msg_flash("SHOOT OR BOMB THE PRISON DOORS OPEN", C_AURORA, 180);
    msg_center(0, "SECTOR  ", C_WHITE);
    msg_num(23, 0, lvl, 1, C_GOLD);

    music_play("ROM:Stage1.vgm");
}

static void enter_play(void)
{
    score = 0;
    lives = STARTING_LIVES;
    next_extend = 20000;
    start_level(1);
}

static void enter_level_clear(void)
{
    gstate = GS_LEVEL_CLEAR;
    game_timer = 0;
    music_play_once("ROM:Victory.vgm");

    clear_bonus = (uint32_t)saved_count * 200;
    add_score(clear_bonus);
    hud_update(); /* the last rescue and the bonus, now play has stopped */
    if (score > hiscore) {
        hiscore = score;
        hiscore_save();
    }
    msg_clear();
    msg_band(0, "SECTOR CLEAR!", C_GOLD);
    msg_center(2, "HOSTAGES SAVED    / 64", C_LGREEN);
    msg_num(24, 2, saved_count, 2, C_WHITE);
    msg_center(3, "RESCUE BONUS       PTS", C_CYAN);
    msg_num(23, 3, clear_bonus, 5, C_WHITE);
}

static void enter_gameover(void)
{
    gstate = GS_GAMEOVER;
    game_timer = 0;
    hud_update();
    if (score > hiscore) {
        hiscore = score;
        hiscore_save();
    }
    music_play_once("ROM:Gameover.vgm");
    msg_clear();
    msg_band(1, "M I S S I O N   F A I L E D", C_RED);
    msg_center(3, "SAVED    / 64", C_GREY);
    msg_num(19, 3, saved_count, 2, C_WHITE);
}

/* Things that keep moving in every state: the sky and the snow. */
static void ambience(int16_t cam_dx)
{
    bg_animate(storm);
    snow_update(cam_dx);
    snow_render();
}

int main(void)
{
    xreg_vga_canvas(CANVAS_320X240);
    input_init();
    bg_init();
    bg_palettes_init();
    hud_init();
    spr_init();
    music_init();
    sfx_init();
    hiscore_load();
    rng_seed(ria_vsync());
    snow_init();

    enter_title();

    int16_t last_cam = 0;
    int8_t pan = 1;
    uint8_t vs = ria_vsync();
    while (1) {
        uint8_t now;
        while ((now = ria_vsync()) == vs)
            ;
        if ((uint8_t)(now - vs) > 1)
            lag_frames++;
        vs = now;

        /* What the last frame computed goes to the VGA right after vsync. */
        spr_commit();
        bg_commit();
        hud_commit();

        music_update();
        sfx_update();
        input_update();
        frame_count++;
        msg_tick();

        switch (gstate) {
        case GS_TITLE:
            /* Drift over the battlefield while the title is up. */
            game_timer++;
            camera_x += pan * 6;
            if (camera_x <= 0 || camera_x >= CAMERA_MAX_X)
                pan = -pan;
            msg_center(5, (game_timer & 32) ? "PRESS FIRE TO START" : "", C_LGREEN);
            enemies_render();
            compounds_render();
            if (in_pressed & (IN_FIRE | IN_START))
                enter_play();
            break;

        case GS_PLAY:
            if (in_pressed & IN_START) {
                gstate = GS_PAUSE;
                msg_center(2, "PAUSED", C_WHITE);
                break;
            }
            game_timer++;
            weather_update();
            player_update();
            compounds_update();
            hostages_update();
            enemies_update();
            projectiles_update();

            player_render();
            compounds_render();
            hostages_render();
            enemies_render();
            projectiles_render();
            if ((frame_count & 3) == 0)
                hud_update();

            if (player_status == PL_RESPAWN_WAIT && lives == 0)
                enter_gameover();
            else if (saved_count + lost_count >= TOTAL_HOSTAGES && cargo_count == 0)
                enter_level_clear();
            break;

        case GS_PAUSE:
            if (in_pressed & IN_START) {
                gstate = GS_PLAY;
                msg_center(2, "", C_WHITE);
            }
            break;

        case GS_LEVEL_CLEAR:
            game_timer++;
            hostages_update();
            hostages_render();
            projectiles_update();
            projectiles_render();
            msg_center(5, (game_timer > 90 && (game_timer & 32)) ? "PRESS FIRE FOR THE NEXT SECTOR" : "", C_WHITE);
            if (game_timer > 90 && (in_pressed & (IN_FIRE | IN_START)))
                start_level(current_level + 1);
            break;

        case GS_GAMEOVER:
            game_timer++;
            projectiles_update();
            projectiles_render();
            msg_center(5, (game_timer > 90 && (game_timer & 32)) ? "PRESS FIRE" : "", C_WHITE);
            if (game_timer > 90 && (in_pressed & (IN_FIRE | IN_START)))
                enter_title();
            break;
        }

        test_stats.state = gstate;
        test_stats.cargo = cargo_count;
        test_stats.saved = saved_count;
        test_stats.lost = lost_count;
        test_stats.lives = lives;
        test_stats.score = (uint16_t)score;
        test_stats.storm = storm;
        test_stats.inside = TOTAL_HOSTAGES - compounds_freed();
        {
            uint8_t b = 0;
            for (uint8_t i = 0; i < NUM_COMPOUNDS; i++)
                b |= compounds[i].breached << i;
            test_stats.breached = b;
        }

        int16_t cam = FROM_SUB(camera_x);
        if (gstate != GS_PAUSE) {
            ambience(cam - last_cam);
            bg_update(cam);
        }
        last_cam = cam;
    }
}
