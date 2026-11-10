// open-pedal dock firmware, stage 1: USB MIDI foot controller.
// Audio (USB Audio Class 2 + I2S) is not implemented yet; see README.md.
#include "controls.h"
#include "pico/bootrom.h"
#include "pico/stdlib.h"
#include "pins.h"
#include "tusb.h"

int main(void) {
    // Keep the DAC muted until the audio path exists.
    gpio_init(PIN_DAC_MUTE);
    gpio_set_dir(PIN_DAC_MUTE, GPIO_OUT);
    gpio_put(PIN_DAC_MUTE, 0);

    controls_init();
    if (controls_bootloader_requested()) {
        reset_usb_boot(0, 0);   // Bank - and Bank + held: UF2 bootloader
    }

    tusb_init();

    while (true) {
        tud_task();
        controls_task();
    }
}
