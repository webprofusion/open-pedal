# Hardware

Design inputs and the KiCad project for the open-pedal dock board. Nothing here has been built or measured.

- `pinmap.md`: RP2040 GPIO assignment (matches `firmware/src/pins.h`)
- `schematic-notes.md`: block-by-block connections and part values
- `bom.csv`: bill of materials with approximate prices
- `layout.json`: mechanical layout (enclosure, switch and rear-panel positions, device holder), shared by the board generator and the Blender enclosure model in `../enclosure/`
- `kicad/`: KiCad 10 project

See `../docs/design.md` for the reasoning behind the part choices.

## KiCad project

`kicad/open-pedal.kicad_pro` opens in KiCad 10. The schematic and board are generated from two files, so edit those and rebuild instead of editing the sheet by hand:

- `kicad/scripts/design.py`: every part, value, footprint and net
- `layout.json`: board size and where the connectors, headers and holes sit

Rebuild with the Python that ships with KiCad (it provides `pcbnew`):

```
"<KiCad 10>/bin/python" hardware/kicad/scripts/build.py
```

The build writes the schematic, runs ERC, exports KiCad's netlist and compares it pin by pin with `design.py`, writes the board, runs DRC, and exports a schematic PDF, a board render and a board GLB to `kicad/exports/`. It fails on any ERC violation, any netlist difference, or any DRC violation other than unrouted nets and silkscreen overlaps.

What is there:

- **Schematic**: 159 parts, 111 nets, one sheet. It is drawn netlist-style: parts are grouped by block and each pin carries a net label, so connections are by name and not by drawn wire.
- **Board**: 176 x 72 mm outline, 4 copper layers, every footprint placed with its nets assigned. Rear-panel connectors, switch headers and mounting holes are at their `layout.json` positions. The remaining parts are packed by block as a starting point.

What is not there:

- No routing, planes, stackup or design rules beyond KiCad's defaults. Decoupling capacitors are grouped with their block, not yet next to their pins.
- KiCad ships no 3D models for the Neutrik jacks and Alps pots, so they are missing from the board render. The Blender model draws stand-ins.

## Choices made at capture

`schematic-notes.md` leaves some parts open. The schematic picks these; all are unverified against current datasheets:

| Block | Choice |
| --- | --- |
| Boost converter | TPS61040, 10 uH, 360 k / 100 k feedback for about 5.7 V |
| 5 V analog LDO | TPS7A2050 (6.0 V maximum input, so the boost voltage must stay below that) |
| 3.3 V LDOs | AP2112K-3.3 (digital), LP5907-3.3 (analog) |
| 5 V input OR | Two B5819W Schottky diodes |
| Jacks | Neutrik NMJ4HCD2 (mono, switched) and NMJ6HCD2 (stereo, switched) |
| Pots | Alps RK09K (gain), RK09L dual (volume) |
| USB-C | GCT USB4105 (host), GCT USB4125 (power only) |
| Headphone amp | TPA6132A2, single-ended inputs, G0 = G1 = low for the lowest gain |
| Input jack | Tip switch contact to ground, so the input is shorted with nothing plugged in |
| R output detect | Sleeve switch contact to GPIO 7; reads high when a plug is in |
| Footswitches | Momentary with a single-colour LED ring, 12 mm bushing assumed; no particular part chosen |
| LED ring drive | V5 through 150 ohm, 2N7002 low-side switch per ring from GPIO 16 to 21 |
| Footswitch and OLED leads | JST XH headers, four-way |

The PCM1808 pin numbers in the project symbol library are from memory. Check them, and every pin strap, against the datasheets before ordering boards.

## To do

1. Breadboard proof with a Pico, a PCM1808 module and a PCM5102A module, wired to `pinmap.md`.
2. Check every symbol pin and strap against the current datasheets.
3. Confirm the connector heights in `layout.json` against the parts bought; they set the rear-panel drilling.
4. Place decoupling, route the 4-layer board, add ground planes and stackup.
