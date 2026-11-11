"""Place the Willie Finder tracker board from the KiCad netlist (run with the system python that has pcbnew).

  /usr/bin/python3 gen_layout.py        ->  willie_tracker.kicad_pcb (placed, unrouted) + willie_tracker.dsn

Board: 4 layers (F.Cu parts+signals, In1.Cu GND plane, In2.Cu signals, B.Cu parts+signals), parts on both sides.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sexpr  # noqa: E402

MM = pcbnew.FromMM
BOARD_W, BOARD_H = 25.5, 28.0
T, B = "F", "B"

# ref: (x, y, rotation, side)   board origin = top-left corner, mm
PLACE = {
    # ---- top: module, USB, charger
    "U1": (12.75, 8.82, 0, T),
    "J1": (21.3, 22.6, 90, T),
    "U2": (4.0, 21.2, 0, T),
    "C1": (9.4, 18.3, 0, T), "C3": (9.4, 20.0, 0, T), "C2": (9.4, 21.7, 0, T),
    "R1": (13.3, 18.6, 90, T), "R2": (14.6, 18.6, 90, T),
    "R3": (1.4, 25.7, 0, T), "R14": (3.6, 25.7, 0, T), "R15": (5.8, 25.7, 0, T),
    "R4": (1.4, 27.25, 0, T), "D1": (3.6, 27.25, 0, T), "D2": (10.5, 27.1, 0, T), "R10": (13.6, 27.1, 0, T),
    # ---- bottom: GNSS, regulator, sensors
    "U6": (7.2, 7.2, 0, B),
    "J3": (16.4, 3.4, 0, B),
    "U4": (16.6, 9.0, 90, B), "C9": (15.0, 12.6, 0, B), "C10": (17.4, 12.6, 0, B), "R7": (19.8, 9.0, 90, B),
    "U8": (5.6, 14.7, 0, B), "C12": (9.6, 14.1, 0, B), "R11": (9.6, 15.6, 0, B), "R12": (12.0, 15.6, 0, B),
    "U7": (22.2, 12.4, 0, B), "C11": (22.2, 15.2, 0, B), "R8": (22.4, 8.8, 0, B), "R9": (22.4, 7.2, 0, B),
    "C6": (22.6, 2.2, 0, B), "C7": (22.9, 4.0, 0, B), "C8": (1.6, 14.2, 0, B),
    "U3": (4.4, 18.4, 0, B), "C4": (8.6, 18.6, 0, B),
    "R5": (12.2, 17.2, 0, B), "R6": (12.2, 18.4, 0, B), "C5": (12.2, 19.6, 0, B),
    "U5": (20.6, 22.6, 90, B),
    "SW1": (15.7, 23.0, 90, B),
    "J2": (8.4, 24.2, 0, B),            # through-hole wire pads: keep both sides clear
    "TP1": (5.0, 26.75, 0, B), "TP2": (7.2, 26.75, 0, B), "TP3": (9.4, 26.75, 0, B), "TP4": (11.6, 26.75, 0, B),
    "TP5": (13.8, 26.75, 0, B),
}
POS_OVERRIDE = {}


def load_netlist():
    t = sexpr.parse(open(os.path.join(HERE, "willie_tracker.net")).read())
    comps = {}
    for c in sexpr.find(sexpr.find(t, "components")[0], "comp"):
        comps[str(sexpr.find(c, "ref")[0][1])] = (str(sexpr.find(c, "value")[0][1]), str(sexpr.find(c, "footprint")[0][1]))
    pads = {}
    for n in sexpr.find(sexpr.find(t, "nets")[0], "net"):
        name = str(sexpr.find(n, "name")[0][1])
        for node in sexpr.find(n, "node"):
            pads[(str(sexpr.find(node, "ref")[0][1]), str(sexpr.find(node, "pin")[0][1]))] = name
    return comps, pads


def build():
    comps, padnets = load_netlist()
    missing = set(comps) - set(PLACE)
    assert not missing, "no placement for %s" % sorted(missing)
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(MM(0.15)); nc.SetTrackWidth(MM(0.2)); nc.SetViaDiameter(MM(0.6)); nc.SetViaDrill(MM(0.3))
    ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.5); ds.m_MinThroughDrill = MM(0.25)
    ds.m_MinClearance = MM(0.15); ds.m_CopperEdgeClearance = MM(0.25)
    ds.SetBoardThickness(MM(0.8))
    ds.m_TentViasFront = True               # cover vias with solder mask: many sit under the RAK module
    ds.m_TentViasBack = True

    nets = {}
    for name in sorted(set(padnets.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    for ref, (value, fpid) in sorted(comps.items()):
        lib, name = fpid.split(":")
        path = os.path.join(HERE, "willie.pretty") if lib == "willie" else "/usr/share/kicad/footprints/%s.pretty" % lib
        fp = pcbnew.FootprintLoad(path, name)
        assert fp is not None, fpid
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(value)
        board.Add(fp)
        x, y, rot, side = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        if side == B:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.Reference().SetVisible(False)
        fp.SetExcludedFromBOM(False)
        fp.SetExcludedFromPosFiles(False)
        used = set()
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in padnets:
                pad.SetNet(nets[padnets[key]])
                used.add(key)
        want = {k for k in padnets if k[0] == ref}
        assert want == used, "%s: netlist pins without pads: %s" % (ref, sorted(want - used))

    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_RECT)
    edge.SetStart(pcbnew.VECTOR2I(0, 0)); edge.SetEnd(pcbnew.VECTOR2I(MM(BOARD_W), MM(BOARD_H)))
    edge.SetLayer(pcbnew.Edge_Cuts); edge.SetWidth(MM(0.1))
    board.Add(edge)

    add_zone(board, nets["GND"], pcbnew.In1_Cu)
    return board, nets


def add_zone(board, net, layer, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(MM(0.2))
    z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)):
        o.Append(MM(x), MM(y))
    board.Add(z)
    return z


def report(board):
    tm = pcbnew.ToMM
    boxes = {}
    for fp in board.GetFootprints():
        layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
        c = fp.GetCourtyard(layer)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
        boxes[fp.GetReference()] = (fp.IsFlipped(), tm(bb.GetLeft()), tm(bb.GetTop()), tm(bb.GetRight()), tm(bb.GetBottom()))
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        fa, ax1, ay1, ax2, ay2 = boxes[a]
        if a != "J1" and (ax1 < 0.2 or ay1 < 0.2 or ax2 > BOARD_W - 0.2 or ay2 > BOARD_H - 0.2):
            print("EDGE   %s  (%.2f %.2f %.2f %.2f)" % (a, ax1, ay1, ax2, ay2))
        for b in refs[i + 1:]:
            fb, bx1, by1, bx2, by2 = boxes[b]
            if fa == fb and min(ax2, bx2) - max(ax1, bx1) > 0.01 and min(ay2, by2) - max(ay1, by1) > 0.01:
                print("OVERLAP %s %s  %.2f x %.2f" % (a, b, min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1)))
    return boxes


if __name__ == "__main__":
    board, nets = build()
    boxes = report(board)
    if "-v" in sys.argv:
        for r in ("J1", "U6", "J3", "U2"):
            print(r, ["%.2f" % v for v in boxes[r][1:]])
        for fp in board.GetFootprints():
            if fp.GetReference() in ("U6", "J1", "U1"):
                for pad in fp.Pads():
                    if (fp.GetReference(), pad.GetNumber()) in (("U6", "11"), ("U6", "1"), ("J1", "A4"), ("J1", "A1"), ("U1", "1"), ("U1", "20"), ("U1", "43"), ("U1", "6")):
                        print(fp.GetReference(), pad.GetNumber(), "%.2f %.2f" % (pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)))
    out = os.path.join(HERE, "willie_tracker.kicad_pcb")
    print("saving", flush=True)
    pcbnew.SaveBoard(out, board)
    print("saved", out, "footprints:", len(board.GetFootprints()), flush=True)
    if "--dsn" in sys.argv:
        board = pcbnew.LoadBoard(out)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(out, board)
        print("filled", flush=True)
        ok = pcbnew.ExportSpecctraDSN(board, os.path.join(HERE, "willie_tracker.dsn"))
        print("dsn export:", ok)
