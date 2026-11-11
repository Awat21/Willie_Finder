"""Simple grid autorouter for the Willie Finder board (run with the system python that has pcbnew).

  /usr/bin/python3 route.py     reads willie_tracker.kicad_pcb (placed), writes it back routed

Routes on F.Cu, In2.Cu and B.Cu on a 0.1 mm grid with A*. In1.Cu is a solid GND plane: every GND surface-mount
pad is routed to a via into that plane. Rules: 0.2 mm tracks, 0.15 mm clearance, 0.6/0.3 mm vias.
"""
import heapq
import math
import os
import sys

import numpy as np
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "willie_tracker.kicad_pcb")
G = 0.1                       # grid, mm
TRK, CLR, VIA, DRILL = 0.2, 0.15, 0.6, 0.3
EDGE = 0.25 + TRK / 2 + 0.05  # track centre to board edge
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
NL = len(LAYERS)
EPS = 1e-6
MM, TM = pcbnew.FromMM, pcbnew.ToMM

import subprocess
subprocess.run([sys.executable, os.path.join(HERE, "gen_layout.py")], check=True, stdout=subprocess.DEVNULL)   # fresh placement
board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
W, H = TM(bb.GetWidth()), TM(bb.GetHeight())
OX, OY = TM(bb.GetLeft()), TM(bb.GetTop())
NX, NY = int(round(W / G)) + 1, int(round(H / G)) + 1
XS = OX + np.arange(NX) * G
YS = OY + np.arange(NY) * G

own_t = np.zeros((NL, NY, NX), np.int32)     # who may put a track centre here (0 free, n net, -1 nobody)
own_v = np.zeros((NL, NY, NX), np.int32)     # who may put a via centre here
novia = np.zeros((NY, NX), bool)             # never a via (on or beside surface-mount pads, near the edge)

edge = np.zeros((NY, NX), bool)
edge[(YS[:, None] < OY + EDGE) | (YS[:, None] > OY + H - EDGE) | (XS[None, :] < OX + EDGE) | (XS[None, :] > OX + W - EDGE)] = True
own_t[:, edge] = -1
novia |= (YS[:, None] < OY + 0.6) | (YS[:, None] > OY + H - 0.6) | (XS[None, :] < OX + 0.6) | (XS[None, :] > OX + W - 0.6)


def claim(arr, mask_slice, mask, n):
    sub = arr[mask_slice]
    conflict = mask & (sub != 0) & (sub != n)
    sub[mask & (sub == 0)] = n
    sub[conflict] = -1


def rect_dist(x1, y1, x2, y2, pad):
    ix1, ix2 = max(0, int((x1 - pad - OX) / G)), min(NX, int((x2 + pad - OX) / G) + 2)
    iy1, iy2 = max(0, int((y1 - pad - OY) / G)), min(NY, int((y2 + pad - OY) / G) + 2)
    xs, ys = XS[ix1:ix2][None, :], YS[iy1:iy2][:, None]
    d = np.hypot(np.maximum(np.maximum(x1 - xs, xs - x2), 0), np.maximum(np.maximum(y1 - ys, ys - y2), 0))
    return (slice(iy1, iy2), slice(ix1, ix2)), d


# ---------------------------------------------------------------- pads
netid, pads = {}, []          # pads: dict(net, layers, cx, cy, cells, th, ref)
inpad = np.zeros((NL, NY, NX), bool)
uniq = [100000]
for fp in board.GetFootprints():
    for pad in fp.Pads():
        name = pad.GetNetname()
        if name:
            n = netid.setdefault(name, len(netid) + 1)
        else:
            uniq[0] += 1
            n = uniq[0]
        b = pad.GetBoundingBox()
        x1, y1, x2, y2 = TM(b.GetLeft()), TM(b.GetTop()), TM(b.GetRight()), TM(b.GetBottom())
        th = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        if th:
            ls = list(range(NL))
            ds = pad.GetDrillSize()
            r = max(TM(ds.x), TM(ds.y)) / 2 + 0.05
            c = pad.GetPosition()
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                r += 0.12                   # hole-to-copper clearance is larger than copper-to-copper
            x1, y1, x2, y2 = min(x1, TM(c.x) - r), min(y1, TM(c.y) - r), max(x2, TM(c.x) + r), max(y2, TM(c.y) + r)
        else:
            ls = [i for i, l in enumerate(LAYERS) if pad.IsOnLayer(l)]
        if not ls:
            continue
        sl, d = rect_dist(x1, y1, x2, y2, 0.8)
        for l in ls:
            claim(own_t[l], sl, d < TRK / 2 + CLR - EPS, n)
            claim(own_v[l], sl, d < VIA / 2 + CLR - EPS, n)
        novia[sl] |= d < VIA / 2 + 0.05
        for l in ls:
            inpad[l][sl] |= d < EPS
        mx, my = min(TRK / 2, (x2 - x1) / 2 - 0.03), min(TRK / 2, (y2 - y1) / 2 - 0.03)
        sl2, din = rect_dist(x1 + mx, y1 + my, x2 - mx, y2 - my, 0.0)
        cells = [(l, sl2[0].start + j, sl2[1].start + i) for l in ls for j, i in zip(*np.nonzero(din < EPS))]
        c = pad.GetPosition()
        if name and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
            if not cells:
                dc = np.hypot(XS[sl[1]][None, :] - TM(c.x), YS[sl[0]][:, None] - TM(c.y))
                j, i = np.unravel_index(np.argmin(dc), dc.shape)
                cells = [(l, sl[0].start + j, sl[1].start + i) for l in ls]
            pads.append(dict(net=name, n=n, layers=ls, cx=TM(c.x), cy=TM(c.y), cells=cells, th=th,
                             ref="%s.%s" % (fp.GetReference(), pad.GetNumber())))

# keepout rule areas that come with footprints (for example under the U.FL connector)
for fp in board.GetFootprints():
    for z in fp.Zones():
        if not z.GetIsRuleArea():
            continue
        b = z.GetBoundingBox()
        sl, d = rect_dist(TM(b.GetLeft()), TM(b.GetTop()), TM(b.GetRight()), TM(b.GetBottom()), 0.5)
        for i, l in enumerate(LAYERS):
            if z.GetLayerSet().Contains(l) and z.GetDoNotAllowTracks():
                sub = own_t[i][sl]
                sub[(d < TRK / 2 + 0.02) & ~inpad[i][sl]] = -1
        if z.GetDoNotAllowVias() or z.GetDoNotAllowCopperPour():
            novia[sl] |= d < VIA / 2 + 0.05

# ---------------------------------------------------------------- routing with rip-up and re-route
import random
import time

SQ2 = math.sqrt(2)
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]
VIA_COST = 12.0
LAYER_COST = [1.0, 1.15, 1.0]
RIP0 = 20


def disk(r):
    k = int(math.ceil(r / G))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    return k, (np.hypot(xx, yy) * G) < r - EPS


DISK_TT = disk(TRK + CLR)                 # track centre vs other track centre
DISK_TV = disk(TRK / 2 + CLR + VIA / 2)   # track vs via centre
DISK_VV = disk(VIA + CLR)                 # via vs via
DISK_SAME = disk(DRILL + 0.3)             # same-net vias, drill to drill

BASE_T, BASE_V = own_t, own_v             # static: pads and board edge, keyed by net id
dyn_t = np.zeros((NL, NY, NX), np.int32)  # routed copper, keyed by unit id (0 free, -1 several units)
dyn_v = np.zeros((NL, NY, NX), np.int32)

# units: one per signal net, one per GND surface-mount pad
units = []                                # dict(name, net, n, pads)
for name in netid:
    ps = [p for p in pads if p["net"] == name]
    if name == "GND":
        for p in ps:
            if not p["th"]:
                units.append(dict(name="GND:" + p["ref"], net=name, n=netid[name], pads=[p], gnd=True))
    elif len(ps) > 1:
        units.append(dict(name=name, net=name, n=netid[name], pads=ps, gnd=False))
for i, u in enumerate(units):
    u["uid"] = i + 1
    u["routes"] = None                    # list of (path, via_cells) when routed
    u["rips"] = 0
UNET = np.zeros(len(units) + 2, np.int32)  # unit id -> net id ; index -1 -> -1
for u in units:
    UNET[u["uid"]] = u["n"]
UNET[-1] = -1
UFAC = np.ones(len(units) + 2, np.float32)


def stamp(arr, y, x, dk, n):
    k, m = dk
    y1, y2, x1, x2 = max(0, y - k), min(NY, y + k + 1), max(0, x - k), min(NX, x + k + 1)
    claim(arr, (slice(y1, y2), slice(x1, x2)), m[y1 - y + k:y2 - y + k, x1 - x + k:x2 - x + k], n)


def stamp_unit(u):
    for path, via_cells in u["routes"]:
        for l, y, x in path:
            stamp(dyn_t[l], y, x, DISK_TT, u["uid"])
            stamp(dyn_v[l], y, x, DISK_TV, u["uid"])
        for y, x in via_cells:
            for l in range(NL):
                stamp(dyn_t[l], y, x, DISK_TV, u["uid"])
                stamp(dyn_v[l], y, x, DISK_VV, u["uid"])


def rebuild():
    dyn_t[:] = 0
    dyn_v[:] = 0
    for u in units:
        if u["routes"]:
            stamp_unit(u)


def cost_maps(u):
    n = u["n"]
    for m in units:
        UFAC[m["uid"]] = min(1.0 + m["rips"], 10.0)
    UFAC[-1] = 2.0
    P, PEN = [], []
    stat_ok = []
    for l in range(NL):
        ok = (BASE_T[l] == 0) | (BASE_T[l] == n)
        dn = UNET[dyn_t[l]]
        soft = ok & ~((dn == 0) | (dn == n))
        pen = np.where(soft, np.minimum(RIP0 * UFAC[dyn_t[l]], 250), 0).astype(np.uint8)
        stat_ok.append(ok)
        P.append(ok.tobytes())
        PEN.append(pen.tobytes())
    vok = ~novia
    vpen = np.zeros((NY, NX), np.float32)
    for l in range(NL):
        vok &= stat_ok[l] & ((BASE_V[l] == 0) | (BASE_V[l] == n))
        for d in (dyn_t[l], dyn_v[l]):
            dn = UNET[d]
            vpen = np.maximum(vpen, np.where((dn == 0) | (dn == n), 0, np.minimum(RIP0 * UFAC[d], 250)))
    near = np.zeros((NY, NX), np.int32)          # same-net vias: share the exact spot or keep the drills apart
    centres = []
    for m in units:
        if m["routes"] and m["n"] == n and m is not u:
            for _, vc in m["routes"]:
                centres.extend(vc)
    for y, x in centres:
        stamp(near, y, x, DISK_SAME, 1)
    for y, x in centres:
        near[y, x] = 0
    vok &= near == 0
    return P, PEN, bytearray(vok.tobytes()), vpen.astype(np.uint8).tobytes()


def astar(maps, sources, targets, want_via):
    """sources: iterable of (l, y, x). targets: set of cells, or with want_via any cell where a via fits."""
    P, PEN, V, VPEN = maps
    if targets:
        ty = sum(t[1] for t in targets) / len(targets)
        tx = sum(t[2] for t in targets) / len(targets)
    best, prev, heap = {}, {}, []
    for s in sources:
        best[s] = 0.0
        heapq.heappush(heap, (0.0, 0.0, s))
    while heap:
        f, g, s = heapq.heappop(heap)
        if g > best.get(s, 1e18):
            continue
        l, y, x = s
        if l == -1 or (targets and s in targets):
            path = [s] if l != -1 else []
            while s in prev:
                s = prev[s]
                path.append(s)
            return path[::-1]
        i = y * NX + x
        for dx, dy, c in MOVES:
            x2, y2 = x + dx, y + dy
            if not (0 <= x2 < NX and 0 <= y2 < NY):
                continue
            i2 = y2 * NX + x2
            if not P[l][i2]:
                continue
            if dx and dy and not (P[l][y * NX + x2] and P[l][y2 * NX + x]):
                continue
            s2 = (l, y2, x2)
            g2 = g + c * LAYER_COST[l] + PEN[l][i2]
            if g2 < best.get(s2, 1e18):
                best[s2] = g2
                prev[s2] = s
                h = 0.0 if not targets else max(abs(x2 - tx), abs(y2 - ty)) * 0.98
                heapq.heappush(heap, (g2 + h, g2, s2))
        if V[i]:
            gv = g + VIA_COST + VPEN[i]
            if want_via and g > 0:
                s2 = (-1, y, x)
                if gv < best.get(s2, 1e18):
                    best[s2] = gv
                    prev[s2] = s
                    heapq.heappush(heap, (gv, gv, s2))
            else:
                for l2 in range(NL):
                    if l2 != l:
                        s2 = (l2, y, x)
                        if gv < best.get(s2, 1e18):
                            best[s2] = gv
                            prev[s2] = s
                            h = 0.0 if not targets else max(abs(x - tx), abs(y - ty)) * 0.98
                            heapq.heappush(heap, (gv + h, gv, s2))
    return None


def find_routes(u):
    """Return list of (path, via_cells, stubs) for the unit, or None if a pad cannot be reached at all."""
    maps = cost_maps(u)
    out = []
    if u["gnd"]:
        p = u["pads"][0]
        path = astar(maps, p["cells"], None, True)
        if path is None:
            return None
        return [(path, {(path[-1][1], path[-1][2])}, [(p, path[0])])]
    mine = sorted(u["pads"], key=lambda p: (p["cx"] + p["cy"]))
    cell_pad = {c: p for p in mine for c in p["cells"]}
    tree = set(mine[0]["cells"])
    todo = mine[1:]
    while todo:
        ty = sum(c[1] for c in tree) / len(tree)
        tx = sum(c[2] for c in tree) / len(tree)
        todo.sort(key=lambda p: abs((p["cy"] - OY) / G - ty) + abs((p["cx"] - OX) / G - tx))
        p = todo.pop(0)
        path = astar(maps, p["cells"], tree, False)
        if path is None:
            return None
        stubs = [(p, path[0])]
        if path[-1] in cell_pad:
            stubs.append((cell_pad[path[-1]], path[-1]))
        vc = {(a[1], a[2]) for a, b in zip(path, path[1:]) if a[0] != b[0]}
        out.append((path, vc, stubs))
        k, dm = DISK_SAME                      # later connections of this net keep clear of these vias too
        for vy, vx in vc:
            for yy in range(max(0, vy - k), min(NY, vy + k + 1)):
                for xx in range(max(0, vx - k), min(NX, vx + k + 1)):
                    if dm[yy - vy + k, xx - vx + k] and (yy, xx) != (vy, vx):
                        maps[2][yy * NX + xx] = 0
        tree.update(path)
        tree.update(p["cells"])
    return out


def conflicts(u, routes):
    tt = np.zeros((NL, NY, NX), np.int32)
    tv = np.zeros((NL, NY, NX), np.int32)
    v_tv = np.zeros((NY, NX), np.int32)
    v_vv = np.zeros((NY, NX), np.int32)
    for path, vc, _ in routes:
        for l, y, x in path:
            stamp(tt[l], y, x, DISK_TT, 1)
            stamp(tv[l], y, x, DISK_TV, 1)
        for y, x in vc:
            stamp(v_tv, y, x, DISK_TV, 1)
            stamp(v_vv, y, x, DISK_VV, 1)
    hit = []
    for m in units:
        if m is u or not m["routes"] or m["n"] == u["n"]:
            continue
        bad = False
        for path, vc in m["routes"]:
            for l, y, x in path:
                if tt[l, y, x] or v_tv[y, x]:
                    bad = True
                    break
            if not bad:
                for y, x in vc:
                    if v_vv[y, x] or tv[:, y, x].any():
                        bad = True
                        break
            if bad:
                break
        if bad:
            hit.append(m)
    return hit


def span(u):
    ps = u["pads"]
    return (len(ps), max(p["cx"] for p in ps) - min(p["cx"] for p in ps) + max(p["cy"] for p in ps) - min(p["cy"] for p in ps))


FIRST = ["/GNSS_RF", "/USB_DP", "/USB_DM"]
byname = {u["name"]: u for u in units}
queue = [byname[n] for n in FIRST] + sorted((u for u in units if u["name"] not in FIRST and not u["gnd"]), key=span) \
    + [u for u in units if u["gnd"]]
budget = float(os.environ.get("ROUTE_SECONDS", "300"))
t0, it, hard = time.time(), 0, set()
while queue and time.time() - t0 < budget:
    u = queue.pop(0)
    it += 1
    routes = find_routes(u)
    if routes is None:
        hard.add(u["name"])
        continue
    hard.discard(u["name"])
    for m in conflicts(u, routes):
        m["routes"] = None
        m["rips"] += 1
        m["stubs"] = None
        queue.append(m)
    u["routes"] = [(p, vc) for p, vc, _ in routes]
    u["stubs"] = [s for _, _, st in routes for s in st]
    rebuild()
    if it % 20 == 0:
        print("iter %d  queue %d  unrouted %d" % (it, len(queue), sum(1 for x in units if not x["routes"])), flush=True)
unrouted = [x["name"] for x in units if not x["routes"]]
print("iterations %d, %.0f s, unrouted units: %s" % (it, time.time() - t0, unrouted or "none"))

segs, vias = [], []     # (net, layer, x1, y1, x2, y2) in mm ; (net, x, y)
for u in units:
    if not u["routes"]:
        continue
    name = u["net"]
    for path, vc in u["routes"]:
        for y, x in vc:
            if (name, XS[x], YS[y]) not in vias:
                vias.append((name, XS[x], YS[y]))
        run = [path[0]]
        for c in path[1:] + [None]:
            if c is not None and c[0] == run[-1][0]:
                run.append(c)
                continue
            i = 0
            while i < len(run) - 1:           # merge collinear cells into one segment
                j = i + 1
                d = (run[j][1] - run[i][1], run[j][2] - run[i][2])
                while j + 1 < len(run) and (run[j + 1][1] - run[j][1], run[j + 1][2] - run[j][2]) == d:
                    j += 1
                segs.append((name, run[i][0], XS[run[i][2]], YS[run[i][1]], XS[run[j][2]], YS[run[j][1]]))
                i = j
            if c is not None:
                run = [c]
    for pad, (l, y, x) in u["stubs"]:
        if abs(XS[x] - pad["cx"]) > EPS or abs(YS[y] - pad["cy"]) > EPS:
            segs.append((name, l, XS[x], YS[y], pad["cx"], pad["cy"]))
all_failed = unrouted

# ---------------------------------------------------------------- write tracks
nets = board.GetNetsByName()
for name, l, x1, y1, x2, y2 in segs:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(MM(float(x1)), MM(float(y1))))
    t.SetEnd(pcbnew.VECTOR2I(MM(float(x2)), MM(float(y2))))
    t.SetWidth(MM(TRK))
    t.SetLayer(LAYERS[l])
    t.SetNet(nets[name])
    board.Add(t)
for name, x, y in vias:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(MM(float(x)), MM(float(y))))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(pcbnew.F_Cu, MM(VIA))
    v.SetDrill(MM(DRILL))
    v.SetNet(nets[name])
    board.Add(v)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("segments %d, vias %d, failed: %s" % (len(segs), len(vias), all_failed or "none"))
