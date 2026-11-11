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
BOARD_W, BOARD_H = 25.0, 40.0
T, B = "F", "B"

# ref: (x, y, rotation, side)   board origin = top-left corner, mm
# Tall parts are all on the top side; the bottom carries only 0402 parts and test pads, to keep the board thin.
PLACE = {
    # ---- top
    "U1": (12.5, 8.6, 0, T),
    "C6": (22.4, 17.7, 0, T),
    "U6": (6.6, 23.2, 0, T),
    "U8": (15.4, 19.6, 0, T),
    "J2": (14.2, 22.4, 0, T),             # through-hole battery wire pads
    "J3": (15.3, 26.5, 0, T),
    "U7": (21.8, 20.6, 0, T),
    "U4": (21.4, 25.6, 0, T),
    "U3": (21.4, 29.8, 0, T),
    "C2": (8.0, 29.6, 0, T), "C3": (11.2, 29.6, 0, T),
    "J1": (12.5, 35.8, 0, T),
    "U2": (3.6, 33.0, 0, T),
    "SW1": (3.6, 38.0, 0, T),
    "C1": (21.4, 33.0, 0, T),
    "U5": (21.4, 37.4, 0, T),
    # ---- bottom: 0402 parts and test pads
    "C7": (22.6, 3.9, 0, B), "C8": (2.4, 11.6, 0, B),
    "TP1": (6.0, 6.0, 0, B), "TP2": (8.5, 6.0, 0, B), "TP3": (11.0, 6.0, 0, B), "TP4": (13.5, 6.0, 0, B),
    "TP5": (16.0, 6.0, 0, B),
    "D2": (14.0, 12.0, 0, B), "R10": (16.2, 12.0, 0, B),
    "R11": (12.0, 18.4, 0, B), "C12": (15.4, 19.6, 0, B), "R12": (18.6, 18.4, 0, B),
    "C11": (21.8, 20.6, 0, B), "R8": (21.0, 23.0, 0, B), "R9": (23.2, 23.0, 0, B),
    "C9": (6.6, 22.0, 0, B), "C10": (6.6, 24.4, 0, B),
    "R7": (21.4, 25.6, 0, B),
    "C4": (21.4, 28.8, 0, B),
    "R3": (1.6, 29.4, 0, B), "R14": (3.8, 29.4, 0, B), "R15": (6.0, 29.4, 0, B),
    "R1": (9.6, 29.2, 0, B), "R2": (15.4, 29.2, 0, B),
    "R5": (19.0, 33.0, 0, B), "R6": (21.2, 33.0, 0, B), "C5": (23.4, 33.0, 0, B),
    "R4": (1.6, 37.2, 0, B), "D1": (3.8, 37.2, 0, B),
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
    for fp in board.GetFootprints():          # through-hole pads occupy both sides
        for pad in fp.Pads():
            if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                pb = pad.GetBoundingBox()
                px1, py1, px2, py2 = tm(pb.GetLeft()), tm(pb.GetTop()), tm(pb.GetRight()), tm(pb.GetBottom())
                for r2, (f2, x1, y1, x2, y2) in boxes.items():
                    if r2 != fp.GetReference() and min(px2, x2) - max(px1, x1) > 0 and min(py2, y2) - max(py1, y1) > 0:
                        print("THROUGH-HOLE %s.%s under/over %s" % (fp.GetReference(), pad.GetNumber(), r2))
    return boxes


if __name__ == "__main__":
    board, nets = build()
    boxes = report(board)
    if "-v" in sys.argv:
        for r in ("J1", "U6", "J3", "U2", "J2"):
            print(r, ["%.2f" % v for v in boxes[r][1:]])
        for fp in board.GetFootprints():
            if fp.GetReference() in ("U6", "J1", "U1", "J3"):
                for pad in fp.Pads():
                    if (fp.GetReference(), pad.GetNumber()) in (("U6", "11"), ("U6", "2"), ("U6", "8"), ("J1", "A4"), ("J1", "S1"), ("J3", "1"), ("U1", "1")):
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
