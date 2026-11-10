// GPIO assignment for the open-pedal dock (RP2040).
// Keep in step with hardware/pinmap.md.
#ifndef PINS_H
#define PINS_H

// Footswitches: momentary to ground, internal pull-ups.
#define PIN_SW_BANK_DOWN   0
#define PIN_SW_BANK_UP     1
#define PIN_SW_PRESET_A    2
#define PIN_SW_PRESET_B    3
#define PIN_SW_PRESET_C    4
#define PIN_SW_PRESET_D    5

// GPIO 6 is spare.
#define PIN_R_JACK_DETECT  7   // needs the internal pull-up; high when a plug is in the R output jack
#define PIN_OLED_SDA       8   // I2C0
#define PIN_OLED_SCL       9

// I2S: the PCM1808 is clock master. These three must stay consecutive,
// the PIO programs address BCK and LRCK relative to the ADC data pin.
#define PIN_I2S_ADC_DATA   10
#define PIN_I2S_BCK        11
#define PIN_I2S_LRCK       12
#define PIN_I2S_DAC_DATA   13

#define PIN_DAC_MUTE       14  // PCM5102A XSMT: low = muted
#define PIN_CLIP_LED       15

// Footswitch LED rings: high = lit, one low-side driver each. PWM-capable for dimming.
#define PIN_LED_BANK_DOWN  16
#define PIN_LED_BANK_UP    17
#define PIN_LED_PRESET_A   18
#define PIN_LED_PRESET_B   19
#define PIN_LED_PRESET_C   20
#define PIN_LED_PRESET_D   21

// Expression jack: tip and ring each through 1 k.
#define PIN_EXP_TIP        26  // ADC0
#define PIN_EXP_RING       27  // ADC1
#define ADC_CH_EXP_TIP     0
#define ADC_CH_EXP_RING    1

#endif
