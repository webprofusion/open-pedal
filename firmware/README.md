# Firmware

RP2040 firmware for the open-pedal dock, in C on the Pico SDK with TinyUSB.

## Status

| Part | State |
| --- | --- |
| USB MIDI device | Implemented |
| Footswitches: bank up/down, presets A to D as Program Change | Implemented |
| Expression pedal as Control Change 11 | Implemented, fixed calibration |
| Program Change from the host moves bank and preset | Implemented |
| Bootloader entry (hold Bank - and Bank + at power-up) | Implemented |
| Footswitch LED rings and OLED | Not started; hooks marked `TODO` in `controls.c` |
| USB Audio Class 2 and I2S audio | Not started; draft PIO programs in `src/i2s_slave.pio` |
| Settings in flash, SysEx configuration | Not started |

The code compiles. It has not been run on hardware.

## Build

Needs the Pico SDK (2.x), CMake and the `arm-none-eabi-gcc` toolchain.

```
cd firmware
cmake -B build -DPICO_SDK_PATH=<path to pico-sdk>
cmake --build build
```

Without a local SDK, use `-DPICO_SDK_FETCH_FROM_GIT=ON` in place of `PICO_SDK_PATH`.

Copy `build/open_pedal.uf2` to the RP2040's USB drive (hold BOOTSEL while plugging in).

## Layout

- `src/main.c`: start-up and main loop
- `src/controls.c`: switch debounce, expression pedal, MIDI in and out
- `src/usb_descriptors.c`: USB device, configuration and string descriptors
- `src/tusb_config.h`: TinyUSB configuration
- `src/pins.h`: GPIO assignment, matching `hardware/pinmap.md`
- `src/i2s_slave.pio`: draft I2S slave receive and transmit programs

## Next steps

1. Flash a Pico and check the MIDI messages on iOS, Android and desktop.
2. Add PWM for the footswitch LED rings and the bank/preset display.
3. Add USB Audio Class 2 (1 in, 2 out, 48 kHz, 24-bit) beside MIDI, with I2S through PIO and DMA.
