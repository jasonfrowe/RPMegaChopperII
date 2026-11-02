#ifndef MUSIC_H
#define MUSIC_H

/* Stream a VGM track from the ROM, e.g. "ROM:Stage1.vgm". NULL stops. */
void music_init(void);
void music_play(const char *path);
/* Play a track through once, then stop (a jingle). */
void music_play_once(const char *path);
void music_stop(void);
void music_update(void);

#endif
