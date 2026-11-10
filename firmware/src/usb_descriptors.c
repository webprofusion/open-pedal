// USB descriptors: one USB MIDI interface (stage 1).
#include <string.h>
#include "pico/unique_id.h"
#include "tusb.h"

// Placeholder IDs from the TinyUSB examples. Replace before distributing
// boards (for example with a pid.codes allocation).
#define USB_VID 0xCafe
#define USB_PID 0x4001

static const tusb_desc_device_t desc_device = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,
    .bDeviceClass       = 0x00,
    .bDeviceSubClass    = 0x00,
    .bDeviceProtocol    = 0x00,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor           = USB_VID,
    .idProduct          = USB_PID,
    .bcdDevice          = 0x0100,
    .iManufacturer      = 1,
    .iProduct           = 2,
    .iSerialNumber      = 3,
    .bNumConfigurations = 1,
};

const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&desc_device;
}

enum { ITF_NUM_MIDI = 0, ITF_NUM_MIDI_STREAMING, ITF_NUM_TOTAL };

#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_MIDI_DESC_LEN)
#define EPNUM_MIDI_OUT 0x01
#define EPNUM_MIDI_IN  0x81

static const uint8_t desc_configuration[] = {
    // Bus powered, 100 mA so Lightning iPhones accept the device.
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 100),
    TUD_MIDI_DESCRIPTOR(ITF_NUM_MIDI, 0, EPNUM_MIDI_OUT, EPNUM_MIDI_IN, 64),
};

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return desc_configuration;
}

static const char *const string_desc[] = {
    NULL,               // 0: language, handled below
    "open-pedal",       // 1: manufacturer
    "Open Pedal Dock",  // 2: product
    NULL,               // 3: serial, from the flash unique ID
};

static uint16_t desc_str[32 + 1];

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    size_t count;

    if (index == 0) {
        desc_str[1] = 0x0409;  // English (US)
        count = 1;
    } else {
        char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
        const char *str;
        if (index == 3) {
            pico_get_unique_board_id_string(serial, sizeof(serial));
            str = serial;
        } else if (index < sizeof(string_desc) / sizeof(string_desc[0])) {
            str = string_desc[index];
        } else {
            return NULL;
        }
        count = strlen(str);
        if (count > 32) count = 32;
        for (size_t i = 0; i < count; i++) desc_str[1 + i] = (uint16_t)str[i];
    }

    desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * count + 2));
    return desc_str;
}
