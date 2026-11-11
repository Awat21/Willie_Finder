"""Minimal S-expression reader/writer for KiCad files, plus symbol-library helpers."""
import copy
import os
import re

SYMDIR = "/usr/share/kicad/symbols"
_tok = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')


class Q(str):
    """A quoted string atom."""


def parse(text):
    stack, cur = [], []
    for m in _tok.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        elif t[0] == '"':
            cur.append(Q(t[1:-1].replace('\\"', '"').replace("\\\\", "\\")))
        else:
            cur.append(t)
    return cur[0]


def dump(node, depth=0):
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(node, str):
        return node
    if all(not isinstance(c, list) for c in node):
        return "(" + " ".join(dump(c) for c in node) + ")"
    pad = "\n" + "  " * (depth + 1)
    out = "(" + dump(node[0])
    for c in node[1:]:
        out += (pad + dump(c, depth + 1)) if isinstance(c, list) else (" " + dump(c))
    return out + "\n" + "  " * depth + ")"


def find(node, key):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]


_cache = {}


def _lib(lib):
    if lib not in _cache:
        path = lib if os.path.isabs(lib) else os.path.join(SYMDIR, lib + ".kicad_sym")
        _cache[lib] = {s[1]: s for s in find(parse(open(path).read()), "symbol")}
    return _cache[lib]


def load_symbol(lib, name, libname=None):
    """Return a flattened (extends resolved) copy of a library symbol, named 'Lib:Name'."""
    syms = _lib(lib)
    sym = copy.deepcopy(syms[name])
    ext = find(sym, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[0][1]])
        pname = parent[1]
        for unit in find(parent, "symbol"):
            unit[1] = Q(name + unit[1][len(pname):])
        props = {p[1]: p for p in find(sym, "property")}
        merged = []
        for c in parent[2:]:
            if isinstance(c, list) and c[0] == "property":
                if c[1] in props:
                    c = props.pop(c[1])
            merged.append(c)
        sym = ["symbol", Q(name)] + merged[: 0] + [c for c in merged if not (isinstance(c, list) and c[0] == "symbol")] \
            + list(props.values()) + [c for c in merged if isinstance(c, list) and c[0] == "symbol"]
    sym[1] = Q((libname or os.path.basename(lib).replace(".kicad_sym", "")) + ":" + name)
    return sym


def pins(sym):
    """{number: (name, x, y, angle, electrical_type)} in symbol coordinates (y up)."""
    out = {}
    for unit in find(sym, "symbol"):
        for p in find(unit, "pin"):
            at = find(p, "at")[0]
            out[str(find(p, "number")[0][1])] = (str(find(p, "name")[0][1]), float(at[1]), float(at[2]),
                                                 int(float(at[3])) if len(at) > 3 else 0, p[1])
    return out
