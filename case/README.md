# Collar pod case

Form-factor study (v0) for the collar unit: RAK19003 mini base + RAK4631 + RAK12500 GPS,
a 250 mAh LiPo (5 x 20 x 30 mm) and a 15 mm GPS patch antenna.

- `collar_pod.scad` - parametric OpenSCAD source. Set `part` to `base`, `lid`, or `assembly`.
- `stl/` - exported parts (`base.stl` and `lid.stl` are the case; the rest are mock components).

Outside size: about 72 mm along the collar (with strap lugs) x 34 mm wide x 12.6 mm tall,
with a 32 degree bend between the board bay and the battery bay.

Not print-ready: no screws, seal or port plug yet. `stack_h` (9.5 mm) and the USB-C position
are assumptions to be checked against the real boards.
