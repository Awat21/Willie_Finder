# Custom tracker PCB

First-pass schematic for a single-board version of the collar tracker. **Draft: not reviewed, not ready for layout or fabrication.**

- `willie_tracker.kicad_sch` - KiCad 7 schematic (opens in KiCad 7 or newer).
- `willie_tracker.pdf` - the same schematic as a PDF.
- `willie.kicad_sym` - project symbol library (RAK4630).
- `gen_schematic.py`, `sexpr.py` - generator; the parts and net table at the top of `gen_schematic.py` are the source.
- `check_netlist.py` - regenerates, exports the netlist with `kicad-cli` and compares it to the net table.

## What is on it

| Block | Part | Notes |
|---|---|---|
| MCU + LoRa + Bluetooth | RAK4630 (-I variant with U.FL sockets) | Same pins as the Meshtastic `rak4631` variant |
| GNSS | u-blox MAX-M10S, U.FL socket for a passive antenna | UART on P0.15/P0.16, PPS on P0.17 |
| GNSS power switch | TPS22917 | Enabled by P1.02 (the firmware's `PIN_3V3_EN`) |
| Accelerometer | LIS3DH, I2C 0x18 | INT1 on P1.01 |
| Charger | MCP73831, 13k program resistor (about 77 mA) | Amber LED while charging |
| Regulator | XC6220 3.3 V | Fed straight from the battery |
| Battery sense | 1M / 1.5M divider on P0.05 | Matches the RAK base boards |
| USB | USB-C with CC resistors and USBLC6 ESD protection | Charging and firmware updates |

## Open items before layout

1. No electrical rule check has been run: KiCad 7's command-line tool does not include one. Run ERC in the KiCad GUI.
2. RAK4630 supply pins (VDD_NRF, VBAT_NRF, VBAT_SX, VBAT_IO_SX) are all tied to 3.3 V. Confirm against RAK's RAK4631 reference schematic.
3. The RAK4630 footprint does not exist yet (`willie:RAK4630` is a placeholder).
4. MAX-M10S: VIO_SEL left open for 3.3 V I/O, V_BCKP on the always-on rail. Confirm both against the u-blox integration manual, and confirm current Meshtastic firmware detects the M10 on this UART.
5. The GNSS UART lines can back-feed the GNSS module while its rail is off; firmware or series resistors need to handle that.
6. The charger and the regulator share the battery node with no power-path circuit.
7. LIS3DH unused ADC pins are tied to ground; confirm against the datasheet.
8. Pin numbers for stock parts come from the KiCad libraries; RAK4630 pins come from the RAK datasheet table.
