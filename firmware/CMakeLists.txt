cmake_minimum_required(VERSION 3.13)

# Needs PICO_SDK_PATH set, or pass -DPICO_SDK_FETCH_FROM_GIT=ON.
include(pico_sdk_import.cmake)

project(open_pedal C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(open_pedal
    src/main.c
    src/controls.c
    src/usb_descriptors.c
)

# Draft I2S slave programs for the audio path (assembled, not yet used).
pico_generate_pio_header(open_pedal ${CMAKE_CURRENT_LIST_DIR}/src/i2s_slave.pio)

target_include_directories(open_pedal PRIVATE src)

target_link_libraries(open_pedal
    pico_stdlib
    pico_unique_id
    pico_bootrom
    hardware_adc
    hardware_pio
    tinyusb_device
    tinyusb_board
)

target_compile_options(open_pedal PRIVATE -Wall -Wextra)

# USB is used by TinyUSB directly, so no stdio over USB.
pico_enable_stdio_usb(open_pedal 0)
pico_enable_stdio_uart(open_pedal 0)

pico_add_extra_outputs(open_pedal)
