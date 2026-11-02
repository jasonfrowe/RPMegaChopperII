#ifndef COMPOUNDS_H
#define COMPOUNDS_H

#include <stdint.h>
#include <stdbool.h>

#define NUM_COMPOUNDS 4

typedef struct
{
    uint8_t col;
    int16_t door_x;
    int16_t door_y;
    bool breached;
    uint8_t hostages_remaining;
    uint8_t spawn_timer;
} compound_t;

extern compound_t compounds[NUM_COMPOUNDS];

void compounds_init(void);
void compounds_update(void);
void compounds_render(void);
bool compounds_check_hit(int16_t hit_x, int16_t hit_y);

#endif /* COMPOUNDS_H */
