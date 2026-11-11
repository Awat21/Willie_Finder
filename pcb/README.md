# Custom tracker PCB

Draft schematic (rev 0.3) and a first-pass board layout for a single-board version of the collar tracker. **Not ready for fabrication.**

- `willie_tracker.kicad_sch`, `willie_tracker.kicad_pro`, `sym-lib-table` - KiCad 9 project (needs KiCad 9 or newer).
- `willie_tracker.pdf` - the same schematic as a PDF.
- `willie.kicad_sym` - project symbol library (RAK4630).
- `gen_schematic.py`, `sexpr.py` - generator; the parts and net table at the top of `gen_schematic.py` are the source.
- `willie_tracker.net` - netlist exported by KiCad from the schematic.
- `check_netlist.py` - regenerates, exports the netlist with `kicad-cli`, compares it to the net table, checks the stacked pads, runs ERC and exports the PDF.
- `erc_report.txt` - KiCad's electrical rule check report.
- `willie_tracker.kicad_pcb` - first-pass board layout (KiCad 9).
- `willie.pretty/RAK4630.kicad_mod`, `fp-lib-table` - RAK4630 land pattern, drawn from RAK's datasheet drawings.
- `gen_layout.py` - places the parts (the placement table at the top is the source). `route.py` - grid autorouter with rip-up and re-route. Run both with the Python that has KiCad's `pcbnew` module: `/usr/bin/python3 route.py`.
- `drc_report.txt` - KiCad's design rule check report for the layout.
- `willie_tracker_board.step` - bare board (outline and holes, no component bodies) for CAD.
- `renders/` - top and bottom views of the board.

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

## Board layout (first pass)

| | |
|---|---|
| Size | 25.5 x 28.0 mm, 0.8 mm thick |
| Layers | 4: top (parts and signals), inner 1 (solid ground plane), inner 2 (signals), bottom (parts and signals) |
| Parts | Both sides: RAK4630, USB-C, charger on top; GNSS, regulator, sensors, buffer on the bottom |
| Assembled thickness | About 6.5 mm: USB-C 3.2 mm on top, board 0.8 mm, MAX-M10S 2.5 mm underneath (estimate from datasheet heights) |
| Rules | 0.2 mm tracks, 0.15 mm clearance, 0.6 / 0.3 mm vias, tented |
| Routing | 876 track segments, 106 vias, every net connected |
| KiCad DRC | 0 violations, 0 unconnected pads, 0 schematic parity issues (`drc_report.txt`) |

Both sides are populated because one side cannot hold everything in less area than the RAK19003 base board
(30 x 35 mm). This board is about 37% smaller in area than that, not the 22 x 26 mm single-sided board first estimated.

The routing was done by `route.py`, a simple autorouter written for this board. It satisfies the clearance rules but
has had no engineering review. Before fabrication:

1. All tracks are 0.2 mm, including power (VBUS, VSYS, +BATT, +3V3). Widen the power tracks.
2. GNSS_RF is a short 0.2 mm track, not a calculated 50 ohm line. Set its width from the board house's stackup.
3. Tracks and tented vias run under the RAK4630. Check RAK's layout guidance for keep-out areas under the module.
4. Decoupling capacitors were placed for fit, not for shortest loop to their pins. Review each one.
5. USB D+ and D- are routed as two ordinary tracks, not a matched pair. Acceptable at full speed over this length; confirm.
6. Only inner layer 1 has a ground pour. Add ground pours on the outer layers and stitch them.
7. The RAK4630 land pattern was drawn from the dimensions in RAK's datasheet images. Check it against a real module or RAK's own footprint before ordering.
8. Reference designators are hidden on the silkscreen; there is no silkscreen artwork, fiducials or mounting features.
9. USB-C sits on the top side at the right-hand short edge; the connector's exact overhang past the board edge is not checked.

## Electrical rule check

Run with `kicad-cli` 9.0.9, all severities. Two items remain, both intended:

| Item | Severity | Explanation |
|---|---|---|
| U4 QOD (open collector) tied to VOUT (power output) | error | Confirmed against TI's TPS22917 datasheet (section 9.3.3): shorting QOD to VOUT is one of the three documented configurations and uses the internal discharge resistance. CT left open is also a documented option. KiCad flags the pin types only. |
| U7 SDO/SA0 (bidirectional) on GND | warning | Intended: address-select pin tied low for I2C address 0x18. |

No unconnected pins, undriven power pins or conflicting outputs were reported.

## Confirmed since rev 0.3

- TPS22917 QOD to VOUT: confirmed (above). Its DBV pinout in the datasheet matches the KiCad symbol.
- RAK4630 supply pins: RAK's reference schematic states that for a single 3.3 V supply VBAT_NRF, VDD_NRF, VBAT_SX and VBAT_IO_SX are all connected to 3.3 V, as drawn here.
- RAK4630 pin order: RAK's pinout drawing matches the land pattern (pin 1 at the top-right of the top row, counting anticlockwise).
- VBUS capacitance: RAK's schematic shows a 4.7 uF capacitor on VBUS inside the module. With C1 that is 9.4 uF nominal directly on VBUS, just under the 10 uF limit.

## Open items

1. USB charge current: the datasheet says PROG1 sets fast charge when SEL is high. With SEL low the charge current may follow the 100 mA USB limit rather than the 77 mA resistor setting. Confirm, and check either value against the chosen cell's rating.
2. Charger variant: -2CC is a first pick (4.20 V). Confirm its timer period and low-battery-indicator options.
3. VBUS capacitance is 9.4 uF nominal against a 10 uF limit; decide whether to reduce C1.
4. With USB connected the regulator input (VSYS) follows VBUS, about 5 V. Confirm against the XC6220 rating.
5. U8 relies on the 74LVC family's powered-off protection. The review confirmed this for the Nexperia part; use that manufacturer or re-check.
6. LIS3DH unused ADC pins are tied to ground; confirm against the datasheet.
7. The layout items listed under "Board layout" above.

## To verify on a prototype

- Charge termination with the tracker running on USB, and USB attach, detach and cold boot on each kind of port you intend to support (including a plain USB 2.0 port or hub).
- The 3.3 V rail on a scope with a partly discharged cell during GNSS startup, LoRa transmit, and both together.
- GNSS RX pin voltage and switched-rail current with the GNSS off, during reset, and across several on/off cycles. Confirm 3V3_GNSS discharges on shutdown and that UART and PPS behave through power transitions.
- GNSS reception with the actual passive antenna in the enclosure; route GNSS_RF as a 50 ohm trace.

## Firmware checks

- GNSS enable is expected active-high on Arduino pin 34 (P1.02); confirm with the intended Meshtastic build.
- Battery reading: the 1M / 1.5M divider is nominally x1.667 and the RAK4631 firmware uses x1.73, so a 4.20 V cell may read about 0.16 V high. Calibrate against a meter.
- LIS3DH INT1 is wired to P1.01, but the stock Meshtastic driver polls over I2C. Wake-on-motion from deep sleep needs firmware support.
