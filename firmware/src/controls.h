#ifndef CONTROLS_H
#define CONTROLS_H

#include <stdbool.h>
#include <stdint.h>

#define PRESETS_PER_BANK 4
#define NUM_BANKS        32   // 32 x 4 = 128 MIDI programs
#define MIDI_CHANNEL     0    // 0 = MIDI channel 1
#define MIDI_CC_EXPRESSION 11

void controls_init(void);

// True if Bank - and Bank + are both held (checked at power-up to enter
// the UF2 bootloader).
bool controls_bootloader_requested(void);

// Call as often as possible from the main loop.
void controls_task(void);

uint8_t controls_bank(void);
uint8_t controls_slot(void);

#endif
