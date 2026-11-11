"""Willie Finder - collar pod, form-factor study (v0).

CadQuery source for the case. Run `python3 collar_pod.py` to regenerate
collar_pod.step (full assembly), collar_pod_case.step (base + lid only) and stl/*.stl.

Fits: RAK19003 mini base + RAK4631 core + RAK12500 GPS, a small LiPo laid across the
pod, a 15 mm GPS patch antenna on top of the battery, and a 38 x 10 mm adhesive flex
LoRa antenna on the collar. Two flat bays joined at an angle so the pod follows the neck.
All dimensions in mm. Values marked ASSUMED must be checked against real parts.
"""
import math
import os
import cadquery as cq

# ---- electronics envelope ----
board_l, board_w = 35.0, 30.0   # RAK19003 outline
stack_h = 9.5                   # ASSUMED: base + core on top + GPS module underneath
batt_l, batt_w, batt_h = 20.0, 30.0, 5.0   # battery bay envelope (502030 cell)
patch, patch_h = 15.0, 4.0      # GPS patch antenna
ant_l, ant_w = 38.0, 10.0       # flex LoRa antenna (Molex 211140-0100)

# ---- case ----
clr, wall, floor, roof = 0.5, 1.6, 1.4, 1.4
bend = 32.0                     # angle between the two bays, degrees
rr = 3.0                        # outside edge radius
strap_w, strap_t = 10.5, 1.8    # cat collar webbing
lug_l, lug_w = 7.0, 15.5

in_w = board_w + 2 * clr
in_h = stack_h + 0.3
la = board_l + 2 * clr + wall   # bay A (board) outside length, runs in -x
lb = batt_l + 2 * clr + wall    # bay B (battery) outside length, runs in +x, tilted
W = in_w + 2 * wall
H = in_h + floor + roof
split = floor + 5.2             # lid/base seam height

_b = math.radians(bend)


def R(x, z):
    """Bay B frame -> world: hinged about the bottom edge of the joint, end drops toward the neck."""
    return (x * math.cos(_b) + z * math.sin(_b), -x * math.sin(_b) + z * math.cos(_b))


def profile(pts, width):
    """Extrude an XZ side profile symmetrically in Y."""
    clean = [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-6]
    return cq.Workplane("XZ").polyline(clean).close().extrude(width / 2, both=True)


def kinked(a_len, b_len, z0, z1, width):
    """Solid that spans both bays between heights z0..z1 (measured in each bay's own frame)."""
    def joint(z):
        # above the hinge the two bays open into a wedge; below it they meet at one point
        return [(0, z), R(0, z)] if z >= 0 else [(z * math.tan(_b / 2), z)]
    return profile([(-a_len, z0)] + joint(z0) + [R(b_len, z0), R(b_len, z1)]
                   + joint(z1)[::-1] + [(-a_len, z1)], width)


def in_b(obj):
    return obj.rotate((0, 0, 0), (0, 1, 0), bend)


def box(x0, x1, w, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, w, z1 - z0, centered=(False, True, False)).translate((x0, 0, z0))


def lug():
    """Tapered strap lug, built in +x from x=0; doubles as an anti-snag ramp."""
    body = profile([(-rr, 0), (lug_l - rr, 0), (lug_l - rr, 3.6), (-rr, 6.0)], lug_w)
    body = body.edges("|Z").fillet(1.5)
    slot = box(lug_l - rr - 3.6, lug_l - rr - 1.4, strap_w, -1, 10)
    return body.cut(slot)


outer = kinked(la, lb, 0, H, W).edges().fillet(rr)
outer = outer.union(lug().mirror("YZ").translate((-la, 0, 0)))
outer = outer.union(in_b(lug().translate((lb, 0, 0))))

cavity = kinked(la - wall, lb - wall, floor, floor + in_h, in_w)
usb = box(-(la + 6), -(la - wall - 1), 10, floor + 4.6, floor + 8.6)   # ASSUMED port position
shell = outer.cut(cavity).cut(usb)

upper = kinked(la + 20, lb + 20, split, split + 30, 100)
base = shell.cut(upper)
lid = shell.intersect(upper)

# ---- mock components (envelopes only) ----
board = (box(-(clr + board_l), -clr, board_w, floor + 3.0, floor + 4.0)                 # base PCB
         .union(box(-(clr + 34), -(clr + 4), 20, floor + 4.0, floor + 7.2))             # RAK4631 core
         .union(box(-(clr + 29), -(clr + 6), 10, floor + 0.2, floor + 3.0).translate((0, -7, 0)))  # RAK12500
         .union(box(-(clr + board_l), -(clr + board_l - 7.5), 9, floor + 4.0, floor + 7.2)))       # USB-C
battery = in_b(box(clr, clr + batt_l, batt_w, floor + 0.2, floor + 0.2 + batt_h))
gps = in_b(box(clr + 2.5, clr + 2.5 + patch, patch, floor + 0.4 + batt_h, floor + 0.4 + batt_h + patch_h))
strap_len_a = la + lug_l + ant_l + 12
strap = kinked(strap_len_a, lb + lug_l + 20, -strap_t - 0.2, -0.2, strap_w)
antenna = box(-(la - rr + lug_l + 2 + ant_l), -(la - rr + lug_l + 2), ant_w, -0.2, 0.1)

PARTS = {
    "base": (base, (0.22, 0.26, 0.25)),
    "lid": (lid, (0.29, 0.33, 0.32)),
    "board": (board, (0.18, 0.54, 0.34)),
    "battery": (battery, (0.67, 0.71, 0.74)),
    "gps": (gps, (0.85, 0.81, 0.68)),
    "strap": (strap, (0.88, 0.38, 0.12)),
    "antenna": (antenna, (0.84, 0.70, 0.29)),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, "stl"), exist_ok=True)
    full, case = cq.Assembly(name="collar_pod"), cq.Assembly(name="collar_pod_case")
    for name, (obj, rgb) in PARTS.items():
        full.add(obj, name=name, color=cq.Color(*rgb))
        if name in ("base", "lid"):
            case.add(obj, name=name, color=cq.Color(*rgb))
        cq.exporters.export(obj, os.path.join(here, "stl", name + ".stl"), tolerance=0.02, angularTolerance=0.15)
    full.export(os.path.join(here, "collar_pod.step"))
    case.export(os.path.join(here, "collar_pod_case.step"))
    bb = shell.val().BoundingBox()
    print("pod bounding box: %.1f x %.1f x %.1f mm; height in bay frame %.1f" % (bb.xlen, bb.ylen, bb.zlen, H))
    for n in ("base", "lid"):
        s = PARTS[n][0].val()
        print(n, "valid:", s.isValid(), "solids:", len(PARTS[n][0].solids().vals()), "volume mm3: %.0f" % s.Volume())
