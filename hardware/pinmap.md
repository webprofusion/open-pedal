# RP2040 pin map

Matches `firmware/src/pins.h`. Change both together.

| GPIO | Signal | Direction | Notes |
| --- | --- | --- | --- |
| 0 | SW_BANK_DOWN | in | Momentary to ground, internal pull-up |
| 1 | SW_BANK_UP | in | Momentary to ground, internal pull-up |
| 2 | SW_PRESET_A | in | Momentary to ground, internal pull-up |
| 3 | SW_PRESET_B | in | Momentary to ground, internal pull-up |
| 4 | SW_PRESET_C | in | Momentary to ground, internal pull-up |
| 5 | SW_PRESET_D | in | Momentary to ground, internal pull-up |
| 6 | spare | | |
| 7 | R_JACK_DETECT | in | Sleeve switch contact of the R output jack, internal pull-up; high when a plug is in |
| 8 | OLED_SDA | i/o | I2C0, SSD1306 |
| 9 | OLED_SCL | out | I2C0, SSD1306 |
| 10 | I2S_ADC_DATA | in | PCM1808 DOUT |
| 11 | I2S_BCK | in | From PCM1808 (clock master), also to PCM5102A BCK |
| 12 | I2S_LRCK | in | From PCM1808, also to PCM5102A LRCK |
| 13 | I2S_DAC_DATA | out | PCM5102A DIN |
| 14 | DAC_MUTE | out | PCM5102A XSMT, low = muted |
| 15 | CLIP_LED | out | Input clip indicator |
| 16 | LED_BANK_DOWN | out | Footswitch LED ring, high = lit, PWM for brightness |
| 17 | LED_BANK_UP | out | Footswitch LED ring |
| 18 | LED_PRESET_A | out | Footswitch LED ring |
| 19 | LED_PRESET_B | out | Footswitch LED ring |
| 20 | LED_PRESET_C | out | Footswitch LED ring |
| 21 | LED_PRESET_D | out | Footswitch LED ring |
| 26 | EXP_TIP | analog / out | ADC0, expression jack tip through 1 k |
| 27 | EXP_RING | analog / out | ADC1, expression jack ring through 1 k |
| 28 | spare | | ADC2 |

GPIO 10 to 12 must stay consecutive: the PIO programs address BCK and LRCK relative to the ADC data pin.

USB D+ and D- go to the device USB-C receptacle through 27 ohm series resistors. The internal BOOTSEL button pulls QSPI_SS low through 1 k.
