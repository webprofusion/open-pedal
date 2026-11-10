// Footswitches and expression pedal -> USB MIDI.
//
// Bank -/+ step the bank without sending anything. A preset switch sends
// Program Change = bank * 4 + slot. Program Change received from the host
// moves the bank and slot to match, so LEDs can follow the app.
#include "controls.h"

#include "hardware/adc.h"
#include "pico/stdlib.h"
#include "pins.h"
#include "tusb.h"

#define NUM_SWITCHES     6
#define SCAN_INTERVAL_US 1000
#define DEBOUNCE_MS      5
#define EXP_INTERVAL_MS  5

enum { SW_BANK_DOWN, SW_BANK_UP, SW_PRESET_A, SW_PRESET_B, SW_PRESET_C, SW_PRESET_D };

static const uint8_t switch_pins[NUM_SWITCHES] = {
    PIN_SW_BANK_DOWN, PIN_SW_BANK_UP,
    PIN_SW_PRESET_A,  PIN_SW_PRESET_B, PIN_SW_PRESET_C, PIN_SW_PRESET_D,
};

static bool    sw_state[NUM_SWITCHES];    // debounced, true = pressed
static uint8_t sw_count[NUM_SWITCHES];    // ms the raw reading has differed

static uint8_t bank;
static uint8_t slot;

// Expression pedal. Defaults suit a wiper-on-tip pedal; the calibration
// values are raw 12-bit ADC counts and will move to flash settings later.
static bool     exp_wiper_on_tip = true;
static uint16_t exp_min = 200;
static uint16_t exp_max = 3800;
static uint32_t exp_filtered_x8;         // IIR filter state, counts * 8
static int32_t  exp_last_sent_raw = -1000;
static int      exp_last_value = -1;

static uint64_t next_scan_us;
static uint8_t  exp_divider;

static void midi_send(uint8_t status, uint8_t d1, int d2) {
    if (!tud_midi_mounted()) return;
    uint8_t msg[3] = { status, d1, (uint8_t)d2 };
    tud_midi_stream_write(0, msg, d2 < 0 ? 2 : 3);
}

static void send_program_change(void) {
    midi_send(0xC0 | MIDI_CHANNEL, (uint8_t)(bank * PRESETS_PER_BANK + slot), -1);
}

static void on_press(int sw) {
    switch (sw) {
    case SW_BANK_DOWN:
        bank = (bank == 0) ? NUM_BANKS - 1 : bank - 1;
        break;
    case SW_BANK_UP:
        bank = (bank + 1) % NUM_BANKS;
        break;
    default:
        slot = (uint8_t)(sw - SW_PRESET_A);
        send_program_change();
        break;
    }
    // TODO: update LEDs and OLED here.
}

static void scan_switches(void) {
    for (int i = 0; i < NUM_SWITCHES; i++) {
        bool raw = !gpio_get(switch_pins[i]);   // active low
        if (raw == sw_state[i]) {
            sw_count[i] = 0;
        } else if (++sw_count[i] >= DEBOUNCE_MS) {
            sw_state[i] = raw;
            sw_count[i] = 0;
            if (raw) on_press(i);
        }
    }
}

static void exp_configure_pins(void) {
    // One contact is driven to 3.3 V as the pot reference, the other is read.
    uint ref_pin   = exp_wiper_on_tip ? PIN_EXP_RING : PIN_EXP_TIP;
    uint wiper_pin = exp_wiper_on_tip ? PIN_EXP_TIP  : PIN_EXP_RING;
    adc_gpio_init(wiper_pin);
    gpio_init(ref_pin);
    gpio_set_dir(ref_pin, GPIO_OUT);
    gpio_put(ref_pin, 1);
    adc_select_input(exp_wiper_on_tip ? ADC_CH_EXP_TIP : ADC_CH_EXP_RING);
}

static void scan_expression(void) {
    uint16_t raw = adc_read();
    exp_filtered_x8 += raw - (exp_filtered_x8 >> 3);   // IIR, 1/8 per step
    int32_t filtered = (int32_t)(exp_filtered_x8 >> 3);

    // Hysteresis: ignore movement smaller than about half a MIDI step.
    int32_t moved = filtered - exp_last_sent_raw;
    if (moved < 0) moved = -moved;
    if (moved < 16) return;

    int32_t value = (filtered - exp_min) * 127 / (exp_max - exp_min);
    if (value < 0) value = 0;
    if (value > 127) value = 127;

    exp_last_sent_raw = filtered;
    if (value != exp_last_value) {
        exp_last_value = (int)value;
        midi_send(0xB0 | MIDI_CHANNEL, MIDI_CC_EXPRESSION, (int)value);
    }
}

static void read_midi_in(void) {
    uint8_t packet[4];
    while (tud_midi_available() && tud_midi_packet_read(packet)) {
        if (packet[1] == (0xC0 | MIDI_CHANNEL)) {
            uint8_t program = packet[2] & 0x7F;
            bank = program / PRESETS_PER_BANK;
            slot = program % PRESETS_PER_BANK;
            // TODO: update LEDs and OLED here.
        }
    }
}

void controls_init(void) {
    for (int i = 0; i < NUM_SWITCHES; i++) {
        gpio_init(switch_pins[i]);
        gpio_set_dir(switch_pins[i], GPIO_IN);
        gpio_pull_up(switch_pins[i]);
    }
    adc_init();
    exp_configure_pins();
    next_scan_us = time_us_64();
}

bool controls_bootloader_requested(void) {
    sleep_ms(10);   // let the pull-ups settle
    return !gpio_get(PIN_SW_BANK_DOWN) && !gpio_get(PIN_SW_BANK_UP);
}

void controls_task(void) {
    read_midi_in();

    uint64_t now = time_us_64();
    if (now < next_scan_us) return;
    next_scan_us += SCAN_INTERVAL_US;
    if (now > next_scan_us + 100000) next_scan_us = now;   // fell far behind

    scan_switches();
    if (++exp_divider >= EXP_INTERVAL_MS) {
        exp_divider = 0;
        scan_expression();
    }
}

uint8_t controls_bank(void) { return bank; }
uint8_t controls_slot(void) { return slot; }
