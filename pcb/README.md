# Custom tracker PCB

Draft schematic (rev 0.2) for a single-board version of the collar tracker. **Not ready for layout or fabrication.**

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
| Regulator | XC6220 3.3 V | Fed from VSYS (USB when plugged in, otherwise the battery) |
| USB load sharing | DMG2305UX P-FET, PMEG2005EJ Schottky | Disconnects the cell from the load while on USB |
| GNSS signal buffer | 74LVC3G34 on the switched rail | Isolates TX, RX and PPS when the GNSS is off |
| Battery sense | 1M / 1.5M divider on P0.05 | Matches the RAK base boards |
| USB | USB-C with CC resistors and USBLC6 ESD protection | Charging and firmware updates |

## Review status (rev 0.2)

Changes made in response to the rev 0.1 schematic review:

| Finding | Status |
|---|---|
| 1. Charger and system share the battery | Fixed: added AN1149-style load sharing (Q1, D3, R13). On USB the system runs from VBUS through D3 and Q1 disconnects the cell from the load. |
| 2. Regulator capacitors | Fixed: C3 is now 10 uF and C4 4.7 uF, both 0603. |
| 3. Ground pads on U6 and U7 | No change needed: U6 pins 1, 10, 12 and U7 pins 5, 10, 12 are on GND in the netlist. The KiCad symbols stack those pins, so the PDF shows one number. |
| 4. Host UART driving an unpowered GNSS | Fixed: added U8 (74LVC3G34) powered from the switched GNSS rail. TX, RX and PPS all pass through it, so each line is isolated when the rail is off. R11 and R12 hold the host inputs at idle levels. |
| 5. Antenna type | Specified: J3 is for a passive antenna; no bias network. |
| 6. Firmware items | Not hardware changes; listed below. |

## Open items before layout

1. No electrical rule check has been run: KiCad 7's command-line tool does not include one. Run ERC in the KiCad GUI.
2. RAK4630 supply pins (VDD_NRF, VBAT_NRF, VBAT_SX, VBAT_IO_SX) are all tied to 3.3 V. Confirm against RAK's RAK4631 reference schematic.
3. The RAK4630 footprint does not exist yet (`willie:RAK4630` is a placeholder). Check symbol-to-footprint pad assignments for every part once footprints are final.
4. Load sharing: Q1 (DMG2305UX) and D3 (PMEG2005EJ) are first picks. With USB connected the regulator input is about 4.7 V; confirm part ratings and Q1's pinout against its datasheet.
5. U8 relies on the 74LVC family's powered-off protection (inputs and outputs high-impedance at VCC = 0). Confirm in the chosen manufacturer's datasheet.
6. Charge current is about 77 mA (13k). Check against the chosen cell's rating.
7. LIS3DH unused ADC pins are tied to ground; confirm against the datasheet.
8. Pin numbers for stock parts come from the KiCad libraries; RAK4630 pins come from the RAK datasheet table.

## To verify on a prototype

- Charge termination with the tracker running on USB.
- The 3.3 V rail on a scope with a partly discharged cell during GNSS startup, LoRa transmit, and both together.
- GNSS RX pin voltage and switched-rail current with the GNSS off, during reset, and across several on/off cycles.
- GNSS reception with the actual passive antenna in the enclosure; route GNSS_RF as a 50 ohm trace.

## Firmware checks

- GNSS enable is expected active-high on Arduino pin 34 (P1.02); confirm with the intended Meshtastic build.
- Battery reading: the 1M / 1.5M divider is nominally x1.667 and the RAK4631 firmware uses x1.73, so a 4.20 V cell may read about 0.16 V high. Calibrate against a meter.
- LIS3DH INT1 is wired to P1.01, but the stock Meshtastic driver polls over I2C. Wake-on-motion from deep sleep needs firmware support.
