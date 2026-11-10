# Schematic notes

Connections and values for each block, as input to schematic capture. Pin straps are from memory of the datasheets; confirm each one against the current datasheet before layout.

## Power

- VBUS (device USB-C) and VPWR (power-only USB-C) are diode-ORed into V5 through Schottky diodes or an ideal-diode P-FET pair.
- Both USB-C receptacles: 5.1 k from CC1 to ground and from CC2 to ground.
- V5 through a ferrite bead and 10 uF to a 3.3 V LDO: 3V3_D for the RP2040 and flash.
- V5 to a boost converter set to about 5.6 V, then LC filter, then a low-noise 5.0 V LDO: 5V_A for the PCM1808 analog supply and the op-amp.
- V5 through a ferrite bead to a second 3.3 V LDO: 3V3_A for the PCM5102A and the headphone amp.
- Mid-rail reference VREF = 5V_A / 2 from a 10 k / 10 k divider, 10 uF to ground.

## Instrument input

- 6.35 mm TS jack, tip to a 47 nF film capacitor.
- After the capacitor: 1 M to VREF, then 2.2 k in series, then 47 pF to ground and a BAT54S clamp to 5V_A and ground.
- TLV9062 half A, non-inverting: feedback through a 10 k gain pot, 1.5 k and 10 uF in series from the inverting input to ground. Gain 1 to about 7.7 (0 to +18 dB).
- TLV9062 half B, unity buffer, then 1 k in series and 4.7 nF to ground, then 1 uF coupling into PCM1808 VINL.
- PCM1808 VINR: 1 uF to an unpopulated footprint for a second input; tie to ground through 0 ohm when unused.

## PCM1808 (ADC)

- VCC = 5V_A, VDD = 3V3_D, decoupling per datasheet, VREF pin to its capacitors.
- SCKI from a 12.288 MHz oscillator (3.3 V) through 33 ohm.
- MD1 = high, MD0 = high: master mode, 256 fs.
- FMT = low: I2S, 24-bit.
- BCK, LRCK and DOUT to the RP2040 (GPIO 11, 12, 10) through 33 ohm; BCK and LRCK also to the PCM5102A.

## PCM5102A (DAC)

- AVDD, CPVDD = 3V3_A; DVDD = 3V3_D; charge-pump and LDO capacitors per datasheet.
- SCK = ground (internal PLL from BCK).
- FMT = low (I2S), FLT = low, DEMP = low.
- XSMT from GPIO 14 with a 10 k pull-down so the DAC stays muted through reset.
- BCK, LRCK from the PCM1808; DIN from GPIO 13.
- OUTL and OUTR each through 470 ohm, then 2.2 nF to ground.

## Outputs

- Out L/Mono: 6.35 mm TS jack from the filtered OUTL.
- Out R: 6.35 mm switched TS jack from the filtered OUTR; the sleeve switch contact goes to GPIO 7. It rests on the grounded sleeve and opens when a plug goes in, so with the internal pull-up the pin reads high when plugged.
- Headphones: filtered OUTL and OUTR to a dual-gang 10 k log volume pot, then a TPA6132A2-class cap-less headphone amp on 3V3_A, then a 6.35 mm TRS jack.

## Foot controls

- Six momentary SPST footswitches with a built-in LED ring, each on a four-way lead: switch, ground, LED anode, LED cathode.
- Switch contacts from GPIO 0 to 5 to ground, 100 nF across each at the board.
- LED rings: anode from V5 through 150 ohm, cathode to ground through a 2N7002 driven by GPIO 16 to 21, 100 k from each gate to ground so the rings stay off at reset. The 150 ohm value assumes a bare single-colour ring; change it to suit the switch bought, and fit a link if the switch has its own resistor.
- OLED header: 3V3_D, ground, SDA (GPIO 8), SCL (GPIO 9), 4.7 k pull-ups.
- Clip LED from GPIO 15 through 1 k.

## Expression jack

- 6.35 mm TRS jack. Tip through 1 k to GPIO 26, ring through 1 k to GPIO 27, sleeve to ground.
- 100 k from tip to ground and from ring to ground, so an empty jack reads zero.
- 100 nF to ground at each GPIO.

## RP2040

- 12 MHz crystal with load capacitors, 2 MB QSPI flash, 1.1 V core decoupling, per the Raspberry Pi hardware design guide.
- USB D+ and D- through 27 ohm to the device USB-C receptacle, USBLC6-2 at the connector.
- Internal BOOTSEL button: QSPI_SS to ground through 1 k.
- SWD pads: SWCLK, SWDIO, ground.
