#ifndef PROJECTILES_H
#define PROJECTILES_H

#include <stdint.h>
#include <stdbool.h>

void projectiles_init(void);
void projectiles_update(void);
void projectiles_render(void);

/* Positions are world pixels; velocities subpixels per frame. */
void bullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy);
/* A bomb falls straight down; dropped from high enough (BOMB_DEEP_HEIGHT
 * above landed height) it reaches tank depth, otherwise it bursts on the
 * ground short of the tanks. One at a time. */
bool bomb_in_air(void);
void bomb_spawn(int16_t x, int16_t y, bool deep);
/* Enemy fire: tank flak arcs under gravity and can come down on
 * hostages; a jet's shot flies straight; a jet's bomb falls; a jeep's
 * machine-gun rounds fly straight and not far; a turret's rocket homes
 * on the chopper for a moment, then flies straight. */
enum { EB_FLAK, EB_SHOT, EB_BOMB, EB_MG, EB_ROCKET };
#define MG_LIFE 36        /* frames a machine-gun round flies */
#define ROCKET_HOME 60    /* frames a rocket steers */
#define ROCKET_TURN 2     /* subpixels per frame it can change speed each frame, steering */
#define ROCKET_MAX 40     /* subpixels per frame, across and up or down */
#define ROCKET_LIFE 150   /* frames before it burns out */
#define JET_BOMB_GRAVITY 2 /* subpixels per frame, each frame */
#define JET_BOMB_BLAST 18  /* px: a landed chopper this close to a burst is lost */
/* Enemy shells in the air of a kind. */
uint8_t ebullets_of(uint8_t kind);
void ebullet_spawn(int16_t x, int16_t y, int16_t vx, int16_t vy, uint8_t kind);
/* Explosions are centered on a world point. */
void explosion_spawn(int16_t cx, int16_t cy, bool big);
void small_explosion_spawn(int16_t cx, int16_t cy);

#endif /* PROJECTILES_H */
