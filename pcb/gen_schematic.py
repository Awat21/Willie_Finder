"""Generate the Willie Finder tracker schematic (KiCad 7 format) from a net table.

Run: python3 gen_schematic.py   ->  willie_tracker.kicad_sch, willie.kicad_sym
Every pin gets a short wire stub ending in a net label or power symbol, so the
connectivity is exactly the table below. Requires the stock KiCad symbol libraries.
"""
import os
import uuid

from sexpr import Q, dump, find, load_symbol, parse, pin_units, pins

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "willie_tracker"
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, PROJECT))
POWER = {"GND": "GND", "+3V3": "+3V3", "VBUS": "VBUS", "+BATT": "+BATT"}
NC = None
_n = [0]


def uid():
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, "%s-%d" % (PROJECT, _n[0])))


# ---------------------------------------------------------------- RAK4630 symbol
RAK_PINS = [  # (number, name, type) from the RAK4630 datasheet pin table
    (1, "VBUS", "power_in"), (2, "USB-", "bidirectional"), (3, "USB+", "bidirectional"),
    (4, "P0.13/I2C_SDA", "bidirectional"), (5, "P0.14/I2C_SCL", "bidirectional"),
    (6, "P0.15/UART2_RX", "bidirectional"), (7, "P0.16/UART2_TX", "bidirectional"),
    (8, "P0.17/UART2_DE", "bidirectional"), (9, "P0.19/UART1_RX", "bidirectional"),
    (10, "P0.20/UART1_TX", "bidirectional"), (11, "P0.21/UART1_DE", "bidirectional"),
    (12, "P0.10/NFC2", "bidirectional"), (13, "P0.09/NFC1", "bidirectional"), (14, "GND", "power_in"),
    (15, "RF_BT", "passive"), (16, "GND", "passive"), (17, "NRF_RESET", "input"),
    (18, "SWDCLK", "input"), (19, "SWDIO", "bidirectional"), (20, "VBAT_SX", "power_in"),
    (21, "VBAT_IO_SX", "power_in"), (22, "GND", "passive"),
    (23, "P0.24/I2C_SDA_2", "bidirectional"), (24, "P0.25/I2C_SCL_2", "bidirectional"),
    (25, "P1.01/SW1", "bidirectional"), (26, "P1.02/SW2", "bidirectional"),
    (27, "P1.03/LED1", "bidirectional"), (28, "P1.04/LED2", "bidirectional"),
    (29, "P0.03/QSPI_CLK", "bidirectional"), (30, "P0.02/QSPI_DIO3", "bidirectional"),
    (31, "P0.28/QSPI_DIO2", "bidirectional"), (32, "P0.29/QSPI_DIO1", "bidirectional"),
    (33, "P0.30/QSPI_DIO0", "bidirectional"), (34, "P0.26/QSPI_CS", "bidirectional"),
    (35, "GND", "passive"), (36, "GND", "passive"), (37, "RF_LoRa", "passive"), (38, "GND", "passive"),
    (39, "P0.31/AIN7", "bidirectional"), (40, "P0.05/AIN3", "bidirectional"),
    (41, "P0.04/AIN2", "bidirectional"), (42, "GND", "passive"),
    (43, "VDD_NRF", "power_in"), (44, "VBAT_NRF", "power_in"),
]
RAK_LEFT = [1, 44, 43, 20, 21, 2, 3, 17, 18, 19, 15, 37, 14, 16, 22, 35, 36, 38, 42]
RAK_RIGHT = [n for n, _, _ in RAK_PINS if n not in RAK_LEFT]


def rak_symbol():
    font = "(effects (font (size 1.27 1.27)))"
    rows = max(len(RAK_LEFT), len(RAK_RIGHT))
    top = (rows - 1) * 2.54 / 2
    hw = 20.32
    out = ['(symbol "RAK4630" (in_bom yes) (on_board yes)',
           '(property "Reference" "U" (at %.2f %.2f 0) %s)' % (-hw, top + 5.08, font),
           '(property "Value" "RAK4630" (at %.2f %.2f 0) %s)' % (hw - 7, top + 5.08, font),
           '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '(property "Datasheet" "https://docs.rakwireless.com/product-categories/wisduo/rak4630-module/datasheet/"'
           ' (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '(symbol "RAK4630_0_1" (rectangle (start %.2f %.2f) (end %.2f %.2f)'
           ' (stroke (width 0.254) (type default)) (fill (type background))))' % (-hw, top + 2.54, hw, -top - 2.54),
           '(symbol "RAK4630_1_1"']
    info = {n: (name, typ) for n, name, typ in RAK_PINS}
    for side, x, ang in ((RAK_LEFT, -hw - 2.54, 0), (RAK_RIGHT, hw + 2.54, 180)):
        for i, n in enumerate(side):
            out.append('(pin %s line (at %.2f %.2f %d) (length 2.54) (name "%s" %s) (number "%d" %s))'
                       % (info[n][1], x, top - i * 2.54, ang, info[n][0], font, n, font))
    out.append("))")
    return parse("\n".join(out))


with open(os.path.join(HERE, "willie.kicad_sym"), "w") as f:
    f.write("(kicad_symbol_lib (version 20220914) (generator willie_gen)\n" + dump(rak_symbol(), 1) + "\n)\n")

# ---------------------------------------------------------------- parts and nets
FP_R, FP_C = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric"
FP_C6 = "Capacitor_SMD:C_0603_1608Metric"
V = {"1": None, "2": None}   # placeholder for two-pin parts


def two(a, b):
    return {"1": a, "2": b}


RAK_NETS = {
    1: "VBUS", 2: "USB_DM", 3: "USB_DP", 4: "I2C_SDA", 5: "I2C_SCL", 6: "HOST_RX", 7: "HOST_TX",
    8: "HOST_PPS", 14: "GND", 16: "GND", 17: "RESET", 18: "SWDCLK", 19: "SWDIO", 20: "+3V3", 21: "+3V3",
    22: "GND", 25: "ACC_INT1", 26: "GNSS_EN", 27: "LED_GREEN", 35: "GND", 36: "GND", 38: "GND",
    40: "VBAT_SENSE", 42: "GND", 43: "+3V3", 44: "+3V3",
}

# (ref, lib, symbol, value, footprint or None for library default, x, y, {pin: net})
PARTS = [
    # --- USB-C, ESD, charger, battery
    ("J1", "Connector", "USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", (40.64, 68.58),
     {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP",
      "A7": "USB_DM", "B7": "USB_DM", "A8": NC, "B8": NC, "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND"}),
    ("R1", "Device", "R", "5.1k", FP_R, (76.2, 60.96), two("CC1", "GND")),
    ("R2", "Device", "R", "5.1k", FP_R, (88.9, 60.96), two("CC2", "GND")),
    ("U5", "Power_Protection", "USBLC6-2SC6", "USBLC6-2SC6", None, (83.82, 86.36),
     {"1": "USB_DP", "6": "USB_DP", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "2": "GND"}),
    # MCP73871: power-path charger. SEL low = USB input, PROG2 low = 100 mA total input limit; the battery
    # supplements the load through the internal ideal diode. THERM 10k = no thermistor, VPCC to IN = disabled,
    # TE low = safety timer on, CE high = charging enabled (per Microchip DS20002090E).
    ("U2", "Battery_Management", "MCP73871-2CC", "MCP73871-2CCI/ML", None, (142.24, 71.12),
     {"18": "VBUS", "19": "VBUS", "2": "VBUS", "17": "VBUS", "3": "GND", "4": "GND", "9": "GND",
      "10": "GND", "11": "GND", "21": "GND", "13": "CHG_PROG1", "12": "CHG_PROG3", "5": "CHG_THERM",
      "1": "VSYS", "20": "VSYS", "14": "+BATT", "15": "+BATT", "16": "+BATT", "8": "CHG_STAT", "6": NC, "7": NC}),
    ("C1", "Device", "C", "4.7uF", FP_C6, (106.68, 116.84), two("VBUS", "GND")),
    ("R3", "Device", "R", "13k", FP_R, (119.38, 116.84), two("CHG_PROG1", "GND")),
    ("R14", "Device", "R", "100k", FP_R, (132.08, 116.84), two("CHG_PROG3", "GND")),
    ("R15", "Device", "R", "10k", FP_R, (147.32, 116.84), two("CHG_THERM", "GND")),
    ("R4", "Device", "R", "1k", FP_R, (157.48, 116.84), two("VBUS", "CHG_LED")),
    ("C2", "Device", "C", "4.7uF", FP_C6, (170.18, 116.84), two("+BATT", "GND")),
    ("D1", "Device", "LED", "CHG amber", "LED_SMD:LED_0402_1005Metric", (187.96, 93.98), {"2": "CHG_LED", "1": "CHG_STAT"}),
    ("J2", "Connector_Generic", "Conn_01x02", "LiPo 3.7V", "Connector_Wire:SolderWire-0.15sqmm_1x02_P4mm_D0.5mm_OD1.5mm", (403.86, 60.96),
     {"1": "+BATT", "2": "GND"}),
    # --- 3.3 V regulator and battery sense
    ("U3", "Regulator_Linear", "XC6220B331MR", "XC6220B331MR", None, (215.9, 60.96),
     {"1": "VSYS", "3": "VSYS", "2": "GND", "5": "+3V3", "4": NC}),
    ("C3", "Device", "C", "10uF", FP_C6, (193.04, 68.58), two("VSYS", "GND")),
    ("C4", "Device", "C", "4.7uF", FP_C6, (238.76, 68.58), two("+3V3", "GND")),
    ("R5", "Device", "R", "1M", FP_R, (261.62, 58.42), two("+BATT", "VBAT_SENSE")),
    ("R6", "Device", "R", "1.5M", FP_R, (261.62, 81.28), two("VBAT_SENSE", "GND")),
    ("C5", "Device", "C", "100nF", FP_C, (276.86, 81.28), two("VBAT_SENSE", "GND")),
    # --- MCU + LoRa module
    ("U1", os.path.join(HERE, "willie.kicad_sym"), "RAK4630", "RAK4630-9-SM-I", "willie:RAK4630", (88.9, 175.26),
     {str(n): RAK_NETS.get(n, NC) for n, _, _ in RAK_PINS}),
    ("C6", "Device", "C", "10uF", FP_C6, (30.48, 152.4), two("+3V3", "GND")),
    ("C7", "Device", "C", "100nF", FP_C, (43.18, 152.4), two("+3V3", "GND")),
    ("C8", "Device", "C", "100nF", FP_C, (30.48, 175.26), two("+3V3", "GND")),
    ("SW1", "Switch", "SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_B3U-1000P", (35.56, 198.12), {"1": "RESET", "2": "GND"}),
    ("R10", "Device", "R", "1k", FP_R, (142.24, 152.4), two("LED_GREEN", "LED_G_A")),
    ("D2", "Device", "LED", "green", "LED_SMD:LED_0402_1005Metric", (154.94, 170.18), {"2": "LED_G_A", "1": "GND"}),
    ("R8", "Device", "R", "4.7k", FP_R, (142.24, 190.5), two("+3V3", "I2C_SDA")),
    ("R9", "Device", "R", "4.7k", FP_R, (154.94, 190.5), two("+3V3", "I2C_SCL")),
    ("TP1", "Connector", "TestPoint", "SWDIO", "TestPoint:TestPoint_Pad_D1.0mm", (30.48, 220.98), {"1": "SWDIO"}),
    ("TP2", "Connector", "TestPoint", "SWDCLK", "TestPoint:TestPoint_Pad_D1.0mm", (43.18, 220.98), {"1": "SWDCLK"}),
    ("TP3", "Connector", "TestPoint", "RESET", "TestPoint:TestPoint_Pad_D1.0mm", (55.88, 220.98), {"1": "RESET"}),
    ("TP4", "Connector", "TestPoint", "3V3", "TestPoint:TestPoint_Pad_D1.0mm", (68.58, 220.98), {"1": "+3V3"}),
    ("TP5", "Connector", "TestPoint", "GND", "TestPoint:TestPoint_Pad_D1.0mm", (81.28, 220.98), {"1": "GND"}),
    # --- GNSS with switched supply
    ("U4", "Power_Management", "TPS22917DBV", "TPS22917DBV", None, (200.66, 124.46),
     {"1": "+3V3", "3": "GNSS_EN", "4": NC, "2": "GND", "6": "3V3_GNSS", "5": "3V3_GNSS"}),
    ("R7", "Device", "R", "100k", FP_R, (177.8, 137.16), two("GNSS_EN", "GND")),
    ("C9", "Device", "C", "1uF", FP_C, (226.06, 132.08), two("3V3_GNSS", "GND")),
    ("C10", "Device", "C", "100nF", FP_C, (238.76, 132.08), two("3V3_GNSS", "GND")),
    ("U6", "RF_GPS", "MAX-M10S", "MAX-M10S", None, (215.9, 180.34),
     {"8": "3V3_GNSS", "7": "3V3_GNSS", "6": "+3V3", "1": "GND", "10": "GND", "12": "GND", "2": "GNSS_TXD", "3": "GNSS_RXD",
      "4": "GNSS_PPS", "11": "GNSS_RF", "5": NC, "9": NC, "13": NC, "14": NC, "15": NC, "16": NC, "17": NC, "18": NC}),
    # --- GNSS signal buffer, powered from the switched rail so every line is isolated when the GNSS is off
    ("U8", "74xGxx", "74LVC3G34", "74LVC3G34", "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
     {1: (205.74, 215.9), 2: (266.7, 215.9), 3: (327.66, 215.9), 4: (375.92, 215.9)},
     {"1": "HOST_TX", "7": "GNSS_RXD", "3": "GNSS_TXD", "5": "HOST_RX", "6": "GNSS_PPS", "2": "HOST_PPS",
      "8": "3V3_GNSS", "4": "GND"}),
    ("C12", "Device", "C", "100nF", FP_C, (396.24, 215.9), two("3V3_GNSS", "GND")),
    ("R11", "Device", "R", "100k", FP_R, (142.24, 226.06), two("+3V3", "HOST_RX")),
    ("R12", "Device", "R", "100k", FP_R, (154.94, 226.06), two("HOST_PPS", "GND")),
    ("J3", "Connector", "Conn_Coaxial", "GNSS passive ant", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", (261.62, 180.34),
     {"1": "GNSS_RF", "2": "GND"}),
    # --- accelerometer
    ("U7", "Sensor_Motion", "LIS3DH", "LIS3DH", None, (330.2, 172.72),
     {"1": "+3V3", "14": "+3V3", "5": "GND", "10": "GND", "12": "GND", "4": "I2C_SCL", "6": "I2C_SDA", "7": "GND",
      "8": "+3V3", "11": "ACC_INT1", "9": NC, "13": "GND", "15": "GND", "16": "GND", "2": NC, "3": NC}),
    ("C11", "Device", "C", "100nF", FP_C, (365.76, 160.02), two("+3V3", "GND")),
    # --- power flags (tell the rule checker these nets are driven from off-sheet sources)
    ("#FLG01", "power", "PWR_FLAG", "PWR_FLAG", "", (330.2, 60.96), {"1": "VBUS"}),
    ("#FLG02", "power", "PWR_FLAG", "PWR_FLAG", "", (350.52, 60.96), {"1": "GND"}),
]

NOTES = [
    (25.4, 30.48, 2.5, "Willie Finder tracker - draft schematic rev 0.3 (not for fabrication)"),
    (25.4, 40.64, 1.8, "USB-C, ESD, power-path charger (100 mA USB input limit), battery"),
    (190.5, 40.64, 1.8, "3.3 V regulator and battery sense (same divider as RAK4631 firmware expects)"),
    (25.4, 137.16, 1.8, "RAK4630: nRF52840 + SX1262. Pin use mirrors the Meshtastic rak4631 variant"),
    (175.26, 106.68, 1.8, "GNSS on a switched rail (GNSS_EN = P1.02, high = on)"),
    (304.8, 147.32, 1.8, "Accelerometer, I2C address 0x18"),
    (190.5, 243.84, 1.8, "GNSS buffer on the switched rail: host lines are isolated while the GNSS is off"),
    (25.4, 248.92, 1.4, "LoRa and Bluetooth antennas plug into the U.FL sockets on the RAK4630 itself (-I variant)."),
    (25.4, 254.0, 1.4, "J3 is for a passive GNSS antenna only: there is no DC bias on the coax. Route GNSS_RF as 50 ohm."),
    (25.4, 259.08, 1.4, "MAX-M10S VIO_SEL left open = 3.3 V I/O. Battery must have its own protection circuit."),
    (25.4, 264.16, 1.4, "Battery reading: divider is nominally x1.667, stock firmware uses x1.73. Calibrate against a meter."),
    (25.4, 271.78, 1.4, "Stacked pins (several pads share one drawn pin; all are in the netlist):"),
    (25.4, 276.86, 1.4, "U6 GND = 1, 10, 12.  U7 GND = 5, 10, 12.  U2 IN = 18, 19; OUT = 1, 20; VBAT = 14, 15; VSS = 10, 11, EP(21).  J1 VBUS = A4, A9, B4, B9; GND = A1, A12, B1, B12."),
    (294.64, 88.9, 1.4, "U2: SEL and PROG2 low = USB, 100 mA input limit. The cell supplements"),
    (294.64, 93.98, 1.4, "the load above that. Only C1 (4.7 uF) sits directly on VBUS."),
]

# ---------------------------------------------------------------- emit
STUB = 5.08
lib_symbols, body, pwr_n, nets = {}, [], [0], {}


def get_sym(lib, name):
    libname = "willie" if lib.endswith(".kicad_sym") else lib
    key = libname + ":" + name
    if key not in lib_symbols:
        lib_symbols[key] = load_symbol(lib, name, libname)
    return key, lib_symbols[key]


def place(ref, lib, name, value, footprint, x, y, hide_ref=False, unit=None):
    key, sym = get_sym(lib, name)
    props = []
    for p in find(sym, "property"):
        if p[1] not in ("Reference", "Value", "Footprint", "Datasheet"):
            continue
        at = find(p, "at")[0]
        val = {"Reference": ref, "Value": value, "Footprint": p[2] if footprint is None else footprint}.get(p[1], p[2])
        eff = [e for e in p if isinstance(e, list) and e[0] == "effects"]
        eff = eff[0] if eff else parse("(effects (font (size 1.27 1.27)))")
        if p[1] == "Reference" and hide_ref and "hide" not in eff:
            eff = eff + ["hide"]
        props.append(["property", Q(p[1]), Q(val), ["at", "%.2f" % (x + float(at[1])), "%.2f" % (y - float(at[2])), at[3]], eff])
    pu = pin_units(sym)
    pin_nodes = [["pin", Q(n), ["uuid", uid()]] for n in pins(sym) if unit is None or pu[n] in (0, unit)]
    body.append(["symbol", ["lib_id", Q(key)], ["at", "%.2f" % x, "%.2f" % y, "0"], ["unit", str(unit or 1)],
                 ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", uid()]] + props + pin_nodes +
                [["instances", ["project", Q(PROJECT), ["path", Q("/" + ROOT_UUID), ["reference", Q(ref)], ["unit", str(unit or 1)]]]]])
    return sym


def wire(x1, y1, x2, y2):
    body.append(parse('(wire (pts (xy %.2f %.2f) (xy %.2f %.2f)) (stroke (width 0) (type default)) (uuid %s))'
                      % (x1, y1, x2, y2, uid())))


DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # pin angle -> direction away from the body (sheet coords)
LABEL = {0: (180, "right"), 180: (0, "left"), 90: (270, "right"), 270: (90, "left")}

for ref, lib, name, value, fp, pos, netmap in PARTS:
    if isinstance(pos, dict):
        for u, (ux, uy) in pos.items():
            sym = place(ref, lib, name, value, fp, ux, uy, unit=u)
    else:
        sym = place(ref, lib, name, value, fp, pos[0], pos[1])
        pos = {0: pos}
    plist, punit = pins(sym), pin_units(sym)
    missing = set(plist) - set(netmap)
    assert not missing, "%s: pins without a net or NC: %s" % (ref, sorted(missing))
    assert not set(netmap) - set(plist), "%s: unknown pins %s" % (ref, sorted(set(netmap) - set(plist)))
    done = set()
    for num, (pname, px, py, ang, ptype) in plist.items():
        net = netmap[num]
        x, y = pos.get(punit[num], pos[min(pos)])
        sx, sy = round(x + px, 2), round(y - py, 2)
        if net is not NC:
            nets.setdefault(net, set()).add("%s.%s" % (ref, num))
        if (sx, sy) in done:
            continue
        done.add((sx, sy))
        if net is NC:
            if ptype != "no_connect":
                body.append(parse("(no_connect (at %.2f %.2f) (uuid %s))" % (sx, sy, uid())))
            continue
        dx, dy = DIRS[ang]
        stub = STUB * 2 if (net in POWER and dx) else STUB   # keep power symbols clear of neighbouring labels
        ex, ey = sx + dx * stub, sy + dy * stub
        if ref.startswith("#FLG"):
            ex, ey = sx, sy + STUB
        wire(sx, sy, ex, ey)
        if net in POWER:
            pwr_n[0] += 1
            place("#PWR%02d" % pwr_n[0], "power", POWER[net], POWER[net], "", ex, ey)
        else:
            a, just = LABEL[ang]
            body.append(parse('(label "%s" (at %.2f %.2f %d) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid %s))'
                              % (net, ex, ey, a, just, uid())))

for x, y, size, text in NOTES:
    body.append(["text", Q(text), ["at", "%.2f" % x, "%.2f" % y, "0"],
                 ["effects", ["font", ["size", str(size), str(size)]], ["justify", "left", "bottom"]], ["uuid", uid()]])

sch = ["kicad_sch", ["version", "20230121"], ["generator", "eeschema"], ["uuid", ROOT_UUID], ["paper", Q("A3")],
       ["title_block", ["title", Q("Willie Finder tracker")], ["rev", Q("0.3 draft")],
        ["comment", "1", Q("Rev 0.3: power-path charger replaces discrete load sharing. Generated from pcb/gen_schematic.py.")]],
       ["lib_symbols"] + list(lib_symbols.values())] + body + [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]]]
with open(os.path.join(HERE, PROJECT + ".kicad_sch"), "w") as f:
    f.write(dump(sch) + "\n")

if __name__ == "__main__":
    import json
    json.dump({k: sorted(v) for k, v in sorted(nets.items())}, open(os.path.join(HERE, "intended_nets.json"), "w"), indent=1)
    single = [k for k, v in nets.items() if len(v) < 2]
    print("parts:", len(PARTS), "nets:", len(nets), "single-pin nets:", single)
