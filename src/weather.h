#ifndef WEATHER_H
#define WEATHER_H

#include <stdint.h>

/* Storms: now and then one blows in, rages a while and passes. While it
 * does, the snow thickens and blows sideways, the wind pushes the chopper,
 * and the far scenery fades into the whiteout. */

#define STORM_MAX 16

/* How bad it is now, 0 (calm) to STORM_MAX. */
extern uint8_t storm;
/* The wind's push this frame, subpixels per frame (+ blows east). */
extern int8_t wind;

/* For test scripts: set to a strength (1..STORM_MAX) to start a storm now. */
extern volatile uint8_t debug_storm;

void weather_init(void);   /* calm, with the first storm a while off */
void weather_update(void);

#endif /* WEATHER_H */
