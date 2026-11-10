"""open-pedal dock: the circuit as data.

Captured from hardware/schematic-notes.md and hardware/pinmap.md. Both the
schematic and the board are generated from this one description, so they
cannot drift apart.

Each part maps symbol pins to net names. A key is a pin number, or a pin
name (which then applies to every pin with that name). The net "NC" places
a no-connect flag.
"""

R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
SOT235 = "Package_TO_SOT_SMD:SOT-23-5"
JACK_TS = "Connector_Audio:Jack_6.35mm_Neutrik_NMJ4HCD2_Horizontal"
JACK_TRS = "Connector_Audio:Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal"
JST4 = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"

# Project-library symbols: (name, ref prefix, description, left pins, right pins)
# pin = (number, name, electrical type)
CUSTOM_SYMBOLS = [
    ("PCM1808", "U", "24-bit 96 kHz stereo audio ADC, TSSOP-14",
     [("13", "VINL", "input"), ("14", "VINR", "input"), ("1", "VREF", "passive"),
      ("6", "SCKI", "input"), ("10", "MD0", "input"), ("11", "MD1", "input"),
      ("12", "FMT", "input"), ("2", "AGND", "power_in"), ("5", "DGND", "power_in")],
     [("3", "VCC", "power_in"), ("4", "VDD", "power_in"), ("8", "BCK", "bidirectional"),
      ("7", "LRCK", "bidirectional"), ("9", "DOUT", "output")]),
    ("Jack_TS_Switched", "J", "6.35 mm mono jack with tip and sleeve normalling contacts (Neutrik NMJ4HCD2)",
     [],
     [("T", "T", "passive"), ("TN", "TN", "passive"), ("S", "S", "passive"), ("SN", "SN", "passive")]),
    ("Jack_TRS_Switched", "J", "6.35 mm stereo jack with normalling contacts (Neutrik NMJ6HCD2)",
     [],
     [("T", "T", "passive"), ("TN", "TN", "passive"), ("R", "R", "passive"), ("RN", "RN", "passive"),
      ("S", "S", "passive"), ("SN", "SN", "passive")]),
]

PARTS = []      # dicts: ref, lib_id, value, footprint, pins, group, rot, place
GROUPS = []     # (key, title) in schematic order
_counters = {}


def group(key, title):
    GROUPS.append((key, title))
    group.current = key


def part(prefix, lib_id, value, footprint, pins, ref=None, rot=0, **extra):
    if ref is None:
        _counters[prefix] = _counters.get(prefix, 0) + 1
        ref = f"{prefix}{_counters[prefix]}"
    p = dict(ref=ref, lib_id=lib_id, value=value, footprint=footprint, pins=pins,
             group=group.current, rot=rot)
    p.update(extra)
    PARTS.append(p)
    return ref


def R(value, a, b, **kw):
    return part("R", "Device:R", value, R0603, {"1": a, "2": b}, rot=90, **kw)


def C(value, a, b="GND", fp=None, **kw):
    if fp is None:
        fp = C0805 if value.split()[0] in ("10u", "4.7u", "2.2u") else C0603
    return part("C", "Device:C", value, fp, {"1": a, "2": b}, rot=90, **kw)


def flag(net):
    part("#FLG", "power:PWR_FLAG", "PWR_FLAG", "", {"1": net})


# ---------------------------------------------------------------- USB and power
group("power", "USB and power")

part("J", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C (host)",
     "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
     {"VBUS": "VBUS", "GND": "GND", "SHIELD": "GND", "CC1": "USB_CC1", "CC2": "USB_CC2",
      "D+": "USB_CONN_DP", "D-": "USB_CONN_DM", "SBU1": "NC", "SBU2": "NC"}, ref="J1")
part("J", "Connector:USB_C_Receptacle_PowerOnly_6P", "USB-C (power)",
     "Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal",
     {"VBUS": "VPWR", "GND": "GND", "SHIELD": "GND", "CC1": "PWR_CC1", "CC2": "PWR_CC2"}, ref="J2")
R("5.1k", "USB_CC1", "GND")
R("5.1k", "USB_CC2", "GND")
R("5.1k", "PWR_CC1", "GND")
R("5.1k", "PWR_CC2", "GND")
part("U", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
     {"1": "USB_CONN_DP", "6": "USB_CONN_DP", "3": "USB_CONN_DM", "4": "USB_CONN_DM",
      "5": "VBUS", "2": "GND"}, ref="U7")
# Diode-OR of the two 5 V inputs.
part("D", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", {"A": "VBUS", "K": "V5"}, ref="D1")
part("D", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", {"A": "VPWR", "K": "V5"}, ref="D2")
C("10u", "V5")
# 3V3_D: ferrite, 10 uF, LDO.
part("FB", "Device:FerriteBead_Small", "600R@100MHz", "Inductor_SMD:L_0603_1608Metric",
     {"1": "V5", "2": "V5_D"}, rot=90)
C("10u", "V5_D")
part("U", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", SOT235,
     {"VIN": "V5_D", "EN": "V5_D", "GND": "GND", "VOUT": "3V3_D"}, ref="U8")
C("10u", "3V3_D")
# 3V3_A: ferrite, low-noise LDO.
part("FB", "Device:FerriteBead_Small", "600R@100MHz", "Inductor_SMD:L_0603_1608Metric",
     {"1": "V5", "2": "V5_A"}, rot=90)
C("10u", "V5_A")
part("U", "Regulator_Linear:LP5907MFX-3.3", "LP5907MFX-3.3", SOT235,
     {"IN": "V5_A", "EN": "V5_A", "GND": "GND", "OUT": "3V3_A"}, ref="U9")
C("10u", "3V3_A")
# 5V_A: boost to about 5.6 V, LC filter, low-noise 5.0 V LDO.
part("U", "Regulator_Switching:TPS61040DBV", "TPS61040DBV", SOT235,
     {"VIN": "V5", "EN": "V5", "GND": "GND", "SW": "BOOST_SW", "FB": "BOOST_FB"}, ref="U11")
C("4.7u", "V5")
part("L", "Device:L", "10uH", "Inductor_SMD:L_Taiyo-Yuden_NR-30xx", {"1": "V5", "2": "BOOST_SW"}, rot=90)
part("D", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", {"A": "BOOST_SW", "K": "VBOOST"}, ref="D3")
R("360k", "VBOOST", "BOOST_FB")
R("100k", "BOOST_FB", "GND")
C("22p", "VBOOST", "BOOST_FB")
C("4.7u", "VBOOST")
part("FB", "Device:FerriteBead_Small", "600R@100MHz", "Inductor_SMD:L_0603_1608Metric",
     {"1": "VBOOST", "2": "VBOOST_F"}, rot=90)
C("10u", "VBOOST_F")
part("U", "Regulator_Linear:TPS7A20xxxDBV", "TPS7A2050PDBV", SOT235,
     {"IN": "VBOOST_F", "EN": "VBOOST_F", "GND": "GND", "OUT": "5V_A"}, ref="U10")
C("10u", "5V_A")
# Mid-rail reference for the input stage.
R("10k", "5V_A", "VREF")
R("10k", "VREF", "GND")
C("10u", "VREF")
for n in ("VBUS", "VPWR", "GND", "V5", "V5_D", "V5_A", "VBOOST", "VBOOST_F"):
    flag(n)

# ---------------------------------------------------------------- RP2040
group("mcu", "RP2040, flash, clock, debug")

rp = {"IOVDD": "3V3_D", "USB_VDD": "3V3_D", "ADC_AVDD": "3V3_D", "VREG_VIN": "3V3_D",
      "VREG_VOUT": "1V1", "DVDD": "1V1", "GND": "GND", "TESTEN": "GND", "RUN": "RUN",
      "XIN": "XIN", "XOUT": "XOUT", "SWCLK": "SWCLK", "SWDIO": "SWDIO",
      "USB_DP": "USB_DP", "USB_DM": "USB_DM",
      "~{QSPI_SS}": "QSPI_SS", "QSPI_SCLK": "QSPI_SCLK", "QSPI_SD0": "QSPI_SD0",
      "QSPI_SD1": "QSPI_SD1", "QSPI_SD2": "QSPI_SD2", "QSPI_SD3": "QSPI_SD3",
      "GPIO0": "SW_BANK_DOWN", "GPIO1": "SW_BANK_UP", "GPIO2": "SW_PRESET_A",
      "GPIO3": "SW_PRESET_B", "GPIO4": "SW_PRESET_C", "GPIO5": "SW_PRESET_D",
      "GPIO6": "NC", "GPIO7": "R_JACK_DETECT", "GPIO8": "OLED_SDA", "GPIO9": "OLED_SCL",
      "GPIO10": "I2S_ADC_DATA", "GPIO11": "I2S_BCK", "GPIO12": "I2S_LRCK",
      "GPIO13": "I2S_DAC_DATA", "GPIO14": "DAC_MUTE", "GPIO15": "CLIP_LED",
      "GPIO26/ADC0": "EXP_TIP", "GPIO27/ADC1": "EXP_RING",
      "GPIO28/ADC2": "NC", "GPIO29/ADC3": "NC"}
for g, name in zip(range(16, 22), ("BANK_DOWN", "BANK_UP", "PRESET_A", "PRESET_B", "PRESET_C", "PRESET_D")):
    rp[f"GPIO{g}"] = f"LED_{name}"
for g in range(22, 26):
    rp[f"GPIO{g}"] = "NC"
part("U", "MCU_RaspberryPi:RP2040", "RP2040", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm",
     rp, ref="U1")
part("U", "Memory_Flash:W25Q16JVSS", "W25Q16JVSS", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm",
     {"~{CS}": "QSPI_SS", "CLK": "QSPI_SCLK", "DI/IO_{0}": "QSPI_SD0", "DO/IO_{1}": "QSPI_SD1",
      "~{WP}/IO_{2}": "QSPI_SD2", "~{HOLD}/~{RESET}/IO_{3}": "QSPI_SD3",
      "VCC": "3V3_D", "GND": "GND"}, ref="U2")
C("100n", "3V3_D")                       # flash
part("Y", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
     {"1": "XIN", "3": "XTAL_OUT", "G": "GND"})
R("1k", "XOUT", "XTAL_OUT")
C("15p", "XIN")
C("15p", "XTAL_OUT")
R("27", "USB_DP", "USB_CONN_DP")
R("27", "USB_DM", "USB_CONN_DM")
R("10k", "3V3_D", "RUN")
R("1k", "QSPI_SS", "BOOTSEL")
part("SW", "Switch:SW_Push", "BOOTSEL", "Button_Switch_SMD:SW_SPST_B3U-1000P",
     {"1": "BOOTSEL", "2": "GND"})
part("J", "Connector_Generic:Conn_01x03", "SWD", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     {"1": "SWCLK", "2": "GND", "3": "SWDIO"}, ref="J15")
for _ in range(8):
    C("100n", "3V3_D")                   # IOVDD x6, USB_VDD, ADC_AVDD
C("1u", "3V3_D")                         # VREG_VIN
C("1u", "1V1")                           # VREG_VOUT
C("100n", "1V1")
C("100n", "1V1")

# ---------------------------------------------------------------- Input stage
group("input", "Instrument input")

part("J", "open-pedal:Jack_TS_Switched", "INPUT", JACK_TS,
     {"T": "IN_TIP", "TN": "GND", "S": "GND", "SN": "NC"}, ref="J3")
C("47n film", "IN_TIP", "IN_AC", fp="Capacitor_SMD:C_1206_3216Metric")
R("1M", "IN_AC", "VREF")
R("2.2k", "IN_AC", "IN_PROT")
C("47p", "IN_PROT")
part("D", "Diode:BAT54S", "BAT54S", "Package_TO_SOT_SMD:SOT-23",
     {"A": "GND", "K": "5V_A", "COM": "IN_PROT"}, ref="D4")
part("U", "Amplifier_Operational:TLV9062xD", "TLV9062IDR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
     {"3": "IN_PROT", "2": "GAIN_FB", "1": "GAIN_OUT",
      "5": "GAIN_OUT", "6": "BUF_OUT", "7": "BUF_OUT",
      "8": "5V_A", "4": "GND"}, ref="U5")
C("100n", "5V_A")
part("RV", "Device:R_Potentiometer_MountingPin", "10k lin (GAIN)",
     "Potentiometer_THT:Potentiometer_Alps_RK09K_Single_Horizontal",
     {"1": "GAIN_OUT", "2": "GAIN_FB", "3": "GAIN_FB", "MP": "GND"}, ref="RV1")
R("1.5k", "GAIN_FB", "GAIN_LEG")
C("10u", "GAIN_LEG")
R("1k", "BUF_OUT", "ADC_FILT")
C("4.7n", "ADC_FILT")
C("1u", "ADC_FILT", "ADC_VINL")
# Second input: unpopulated pad, grounded through 0 ohm when unused.
C("1u", "IN2", "ADC_VINR")
R("0", "IN2", "GND")
part("TP", "Connector:TestPoint", "IN2", "TestPoint:TestPoint_Pad_D1.5mm", {"1": "IN2"})

# ---------------------------------------------------------------- ADC
group("adc", "PCM1808 ADC and audio clock")

part("U", "open-pedal:PCM1808", "PCM1808PWR", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
     {"VINL": "ADC_VINL", "VINR": "ADC_VINR", "VREF": "ADC_VREF", "VCC": "5V_A", "VDD": "3V3_D",
      "AGND": "GND", "DGND": "GND", "SCKI": "ADC_SCKI", "MD0": "3V3_D", "MD1": "3V3_D",
      "FMT": "GND", "BCK": "ADC_BCK", "LRCK": "ADC_LRCK", "DOUT": "ADC_DOUT"}, ref="U3")
C("100n", "ADC_VREF")
C("10u", "ADC_VREF")
C("100n", "5V_A")
C("10u", "5V_A")
C("100n", "3V3_D")
C("10u", "3V3_D")
part("X", "Oscillator:ASE-xxxMHz", "12.288MHz", "Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm",
     {"Vdd": "3V3_D", "EN": "3V3_D", "GND": "GND", "OUT": "MCLK"})
C("100n", "3V3_D")
R("33", "MCLK", "ADC_SCKI")
R("33", "ADC_BCK", "I2S_BCK")
R("33", "ADC_LRCK", "I2S_LRCK")
R("33", "ADC_DOUT", "I2S_ADC_DATA")

# ---------------------------------------------------------------- DAC and line out
group("dac", "PCM5102A DAC and line outputs")

part("U", "Audio:PCM5102A", "PCM5102APWR", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
     {"AVDD": "3V3_A", "CPVDD": "3V3_A", "DVDD": "3V3_D", "AGND": "GND", "DGND": "GND",
      "CPGND": "GND", "CAPP": "DAC_CAPP", "CAPM": "DAC_CAPM", "VNEG": "DAC_VNEG",
      "LDOO": "DAC_LDOO", "SCK": "GND", "BCK": "I2S_BCK", "LRCK": "I2S_LRCK",
      "DIN": "I2S_DAC_DATA", "FMT": "GND", "FLT": "GND", "DEMP": "GND", "XSMT": "DAC_MUTE",
      "OUTL": "DAC_OUTL", "OUTR": "DAC_OUTR"}, ref="U4")
C("2.2u", "DAC_CAPP", "DAC_CAPM")
C("2.2u", "DAC_VNEG")
C("10u", "DAC_LDOO")
C("100n", "3V3_A")                       # AVDD
C("100n", "3V3_A")                       # CPVDD
C("10u", "3V3_A")
C("100n", "3V3_D")                       # DVDD
R("10k", "DAC_MUTE", "GND")
R("470", "DAC_OUTL", "LINE_L")
C("2.2n", "LINE_L")
R("470", "DAC_OUTR", "LINE_R")
C("2.2n", "LINE_R")
part("J", "open-pedal:Jack_TS_Switched", "OUT L/MONO", JACK_TS,
     {"T": "LINE_L", "TN": "NC", "S": "GND", "SN": "NC"}, ref="J4")
# R jack: the sleeve normalling contact opens when a plug goes in.
part("J", "open-pedal:Jack_TS_Switched", "OUT R", JACK_TS,
     {"T": "LINE_R", "TN": "NC", "S": "GND", "SN": "R_JACK_DETECT"}, ref="J5")

# ---------------------------------------------------------------- Headphones
group("phones", "Headphone amplifier")

part("RV", "Device:R_Potentiometer_Dual_MountingPin", "10k log x2 (VOLUME)",
     "Potentiometer_THT:Potentiometer_Alps_RK09L_Double_Horizontal",
     {"1": "GND", "2": "HP_VOL_L", "3": "LINE_L", "4": "GND", "5": "HP_VOL_R", "6": "LINE_R",
      "MP": "GND"}, ref="RV2", dirs={"3": (0, 1), "4": (0, 1)})   # inner pins face each other
part("U", "Amplifier_Audio:TPA6132A2RTE", "TPA6132A2RTE",
     "Package_DFN_QFN:WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
     {"INL+": "HP_INL", "INL-": "HP_INL_REF", "INR+": "HP_INR", "INR-": "HP_INR_REF",
      "OUTL": "HP_L", "OUTR": "HP_R", "G0": "GND", "G1": "GND", "EN": "3V3_A",
      "VDD": "3V3_A", "HPVDD": "HP_HPVDD", "HPVSS": "HP_HPVSS", "CPP": "HP_CPP", "CPN": "HP_CPN",
      "PGND": "GND", "SGND": "GND", "EP": "GND"}, ref="U6")
C("1u", "HP_VOL_L", "HP_INL")
C("1u", "HP_INL_REF")
C("1u", "HP_VOL_R", "HP_INR")
C("1u", "HP_INR_REF")
C("1u", "HP_CPP", "HP_CPN")
C("1u", "HP_HPVSS")
C("2.2u", "HP_HPVDD")
C("2.2u", "3V3_A")
part("J", "open-pedal:Jack_TRS_Switched", "PHONES", JACK_TRS,
     {"T": "HP_L", "R": "HP_R", "S": "GND", "TN": "NC", "RN": "NC", "SN": "NC"}, ref="J6")
flag("HP_HPVDD")
flag("HP_HPVSS")

# ---------------------------------------------------------------- Foot controls
group("controls", "Footswitches, LEDs, display")

SWITCHES = ["BANK_DOWN", "BANK_UP", "PRESET_A", "PRESET_B", "PRESET_C", "PRESET_D"]
# Each footswitch has an LED ring, so its lead is four wires: switch, ground, LED anode, LED cathode.
# The ring runs from V5 through a series resistor and is switched low-side, so the GPIO never carries
# the LED current and the ring stays off while the pin floats at reset.
for i, name in enumerate(SWITCHES):
    part("J", "Connector_Generic:Conn_01x04", f"SW {name}", JST4,
         {"1": f"SW_{name}", "2": "GND", "3": f"LEDA_{name}", "4": f"LEDK_{name}"},
         ref=f"J{7 + i}", place=("switch", name))
    C("100n", f"SW_{name}", place=("switch_cap", name))
    R("150", "V5", f"LEDA_{name}")
    part("Q", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23",
         {"G": f"LED_{name}", "S": "GND", "D": f"LEDK_{name}"})
    R("100k", f"LED_{name}", "GND")
part("J", "Connector_Generic:Conn_01x04", "OLED", JST4,
     {"1": "GND", "2": "3V3_D", "3": "OLED_SCL", "4": "OLED_SDA"}, ref="J13")
R("4.7k", "3V3_D", "OLED_SDA")
R("4.7k", "3V3_D", "OLED_SCL")
R("1k", "CLIP_LED", "CLIP_A")
part("D", "Device:LED", "CLIP red", "LED_SMD:LED_0603_1608Metric", {"A": "CLIP_A", "K": "GND"}, ref="D11")

# ---------------------------------------------------------------- Expression
group("expression", "Expression jack")

part("J", "open-pedal:Jack_TRS_Switched", "EXPRESSION", JACK_TRS,
     {"T": "EXP_T", "R": "EXP_R", "S": "GND", "TN": "NC", "RN": "NC", "SN": "NC"}, ref="J14")
R("1k", "EXP_T", "EXP_TIP")
R("1k", "EXP_R", "EXP_RING")
R("100k", "EXP_T", "GND")
R("100k", "EXP_R", "GND")
C("100n", "EXP_TIP")
C("100n", "EXP_RING")

# ---------------------------------------------------------------- Mechanical
group("mech", "Mechanical")
for _ in range(3):
    part("H", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {})
