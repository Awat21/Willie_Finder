# Custom tracker PCB

Draft schematic (rev 0.3) for a single-board version of the collar tracker. **Not ready for layout or fabrication.**

- `willie_tracker.kicad_sch`, `willie_tracker.kicad_pro`, `sym-lib-table` - KiCad 9 project (needs KiCad 9 or newer).
- `willie_tracker.pdf` - the same schematic as a PDF.
- `willie.kicad_sym` - project symbol library (RAK4630).
- `gen_schematic.py`, `sexpr.py` - generator; the parts and net table at the top of `gen_schematic.py` are the source.
- `willie_tracker.net` - netlist exported by KiCad from the schematic.
- `check_netlist.py` - regenerates, exports the netlist with `kicad-cli`, compares it to the net table, checks the stacked pads, runs ERC and exports the PDF.
- `erc_report.txt` - KiCad's electrical rule check report.

## What is on it

| Block | Part | Notes |
|---|---|---|
| MCU + LoRa + Bluetooth | RAK4630 (-I variant with U.FL sockets) | Same pins as the Meshtastic `rak4631` variant |
| GNSS | u-blox MAX-M10S, U.FL socket for a passive antenna | UART on P0.15/P0.16, PPS on P0.17 |
| GNSS power switch | TPS22917 | Enabled by P1.02 (the firmware's `PIN_3V3_EN`) |
| Accelerometer | LIS3DH, I2C 0x18 | INT1 on P1.01 |
| Charger and power path | MCP73871, 100 mA USB input limit | Runs the system from USB while charging; battery supplements peaks. Amber LED while charging |
| Regulator | XC6220 3.3 V | Fed from VSYS (USB when plugged in, otherwise the battery) |
| GNSS signal buffer | 74LVC3G34 on the switched rail | Isolates TX, RX and PPS when the GNSS is off |
| Battery sense | 1M / 1.5M divider on P0.05 | Matches the RAK base boards |
| USB | USB-C with CC resistors and USBLC6 ESD protection | Charging and firmware updates |

## Review status (rev 0.3)

Response to the rev 0.2 schematic review:

| Finding | Status |
|---|---|
| 1. U6 and U7 ground pads unverified | Verified in the native netlist (`willie_tracker.net`, exported by KiCad): U6.1, U6.10, U6.12, U7.5, U7.10 and U7.12 are all on GND. `check_netlist.py` now asserts these and the other stacked pads on every run, and the schematic lists the stacked pins in a note. The library footprints (`RF_GPS:ublox_MAX`, `Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y`) contain pads 1-18 and 1-16. ERC has since been run; see below. |
| 2. USB inrush and current budget | Changed: the MCP73831 and the discrete load sharing are replaced by an MCP73871 power-path charger. SEL and PROG2 are tied low, which limits total USB input current to 100 mA (80-100 mA per the datasheet). Above that the battery supplements the load through the internal ideal diode. Only C1 (4.7 uF) is directly on VBUS; C3 is behind the current limit. |
| 3. Battery handover and VBUS leakage | Removed with the discrete circuit: Q1, D3 and R13 are gone. Handover is inside the MCP73871. |

Earlier fixes kept: regulator capacitors (10 uF / 4.7 uF), GNSS buffer U8, passive-antenna note.

MCP73871 pin settings, checked against Microchip DS20002090E: SEL low = USB input; PROG2 low = 100 mA; THERM 10k to VSS = no thermistor; VPCC tied to IN = disabled; TE low = safety timer enabled; CE high = charging enabled; PROG1 13k = 77 mA; PROG3 100k = 10 mA termination.

## Electrical rule check

Run with `kicad-cli` 9.0.9, all severities. Three items remain, all understood:

| Item | Severity | Explanation |
|---|---|---|
| U4 QOD (open collector) tied to VOUT (power output) | error | Intended: QOD is the load switch's output-discharge pin and is tied to its output. To be confirmed against the TPS22917 datasheet, then excluded. |
| U7 SDO/SA0 (bidirectional) on GND | warning | Intended: address-select pin tied low for I2C address 0x18. |
| Footprint library `willie` not found | warning | The RAK4630 footprint has not been drawn yet. |

No unconnected pins, undriven power pins or conflicting outputs were reported.

## Open items before layout

1. Resolve or formally exclude the three ERC items above.
2. RAK4630 supply pins (VDD_NRF, VBAT_NRF, VBAT_SX, VBAT_IO_SX) are all tied to 3.3 V. Confirm against RAK's RAK4631 reference schematic.
3. The RAK4630 footprint does not exist yet (`willie:RAK4630` is a placeholder). Check symbol-to-footprint pad assignments for every part once footprints are final.
4. VBUS capacitance: C1 is 4.7 uF. Whether the RAK4630 has its own capacitor on its VBUS pin is not known; if it does, add it to the total and keep the sum under 10 uF.
5. USB charge current: the datasheet says PROG1 sets fast charge when SEL is high. With SEL low the charge current may follow the 100 mA USB limit rather than the 77 mA resistor setting. Confirm, and check either value against the chosen cell's rating.
6. Charger variant: -2CC is a first pick (4.20 V). Confirm its timer period and low-battery-indicator options suit a small cell that powers a load while charging.
7. With USB connected the regulator input (VSYS) follows VBUS, about 5 V. The XC6220 is within its input rating there; confirm.
8. U8 relies on the 74LVC family's powered-off protection. The review confirmed this for the Nexperia part; use that manufacturer or re-check.
9. LIS3DH unused ADC pins are tied to ground; confirm against the datasheet.
10. Pin numbers for stock parts come from the KiCad libraries; RAK4630 pins come from the RAK datasheet table.

## To verify on a prototype

- Charge termination with the tracker running on USB, and USB attach, detach and cold boot on each kind of port you intend to support (including a plain USB 2.0 port or hub).
- The 3.3 V rail on a scope with a partly discharged cell during GNSS startup, LoRa transmit, and both together.
- GNSS RX pin voltage and switched-rail current with the GNSS off, during reset, and across several on/off cycles. Confirm 3V3_GNSS discharges on shutdown and that UART and PPS behave through power transitions.
- GNSS reception with the actual passive antenna in the enclosure; route GNSS_RF as a 50 ohm trace.

## Firmware checks

- GNSS enable is expected active-high on Arduino pin 34 (P1.02); confirm with the intended Meshtastic build.
- Battery reading: the 1M / 1.5M divider is nominally x1.667 and the RAK4631 firmware uses x1.73, so a 4.20 V cell may read about 0.16 V high. Calibrate against a meter.
- LIS3DH INT1 is wired to P1.01, but the stock Meshtastic driver polls over I2C. Wake-on-motion from deep sleep needs firmware support.
