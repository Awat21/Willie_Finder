"""Export the netlist with kicad-cli and confirm it matches the net table in gen_schematic.py."""
import json
import os
import subprocess
import sys
import tempfile

import sexpr

here = os.path.dirname(os.path.abspath(__file__))
subprocess.run([sys.executable, os.path.join(here, "gen_schematic.py")], check=True)
out = os.path.join(tempfile.mkdtemp(), "t.net")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", out, os.path.join(here, "willie_tracker.kicad_sch")],
               check=True, capture_output=True)
tree = sexpr.parse(open(out).read())
got = {}
for n in sexpr.find(sexpr.find(tree, "nets")[0], "net"):
    name = str(sexpr.find(n, "name")[0][1]).lstrip("/")
    if not name.startswith("unconnected"):
        got[name] = sorted("%s.%s" % (sexpr.find(x, "ref")[0][1], sexpr.find(x, "pin")[0][1]) for x in sexpr.find(n, "node"))
want = {k: [p for p in v if not p.startswith("#")] for k, v in json.load(open(os.path.join(here, "intended_nets.json"))).items()}
bad = [k for k in sorted(set(want) | set(got)) if want.get(k) != got.get(k)]
for k in bad:
    print("MISMATCH", k, want.get(k), got.get(k))
print("nets: %d, mismatches: %d" % (len(got), len(bad)))
sys.exit(1 if bad else 0)
