# Collar pod case

Form-factor study (v0) for the collar unit: RAK19003 mini base + RAK4631 + RAK12500 GPS,
a small LiPo (bay is 20 x 30 x 5 mm), a 15 mm GPS patch antenna, and a 38 x 10 mm adhesive
flex LoRa antenna stuck to the collar beside the pod.

- `collar_pod.step` - full assembly: case base and lid plus mock components, strap and antenna.
- `collar_pod_case.step` - case base and lid only.
- `collar_pod.py` - CadQuery source that generates the STEP and STL files (`pip install cadquery`, then `python3 collar_pod.py`).
- `stl/` - mesh exports of each part.

Outside size: about 72 mm along the collar (with strap lugs) x 34 mm wide x 12.6 mm tall,
with a 32 degree bend between the board bay and the battery bay.

Not print-ready: no screws, seal or port plug yet. The 9.5 mm electronics height and the
USB-C position are assumptions to be checked against the real boards.
