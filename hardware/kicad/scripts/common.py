"""Shared helpers: locate KiCad, load library symbols, resolve part pins to nets."""
import copy
import math
import os
import uuid

from sexpr import parse, find, find_all, q, unq
import design

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(HERE)                 # hardware/kicad
HARDWARE_DIR = os.path.dirname(PROJECT_DIR)         # hardware
PROJECT = "open-pedal"
NS = uuid.UUID("6f70656e-2d70-6564-616c-2d646f636b00")


def kicad_root():
    for cand in (os.environ.get("KICAD_ROOT"), r"D:\Program Files\KiCad\10.0", r"C:\Program Files\KiCad\10.0",
                 "/usr", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/.."):
        if cand and os.path.isdir(os.path.join(cand, "share", "kicad", "symbols")):
            return cand
    raise SystemExit("KiCad 10 not found; set KICAD_ROOT to the install folder")


SHARE = os.path.join(kicad_root(), "share", "kicad")


def uid(*parts):
    """Stable UUID so regenerated files diff cleanly and the board stays linked."""
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


# ---------------------------------------------------------------- symbols
_libs = {}
_symbols = {}


def _custom_symbol(name, prefix, desc, left, right):
    hw = 10.16 if left else 5.08
    n = max(len(left), len(right))
    top = 2.54 * math.ceil((n - 1) / 2)
    font = "(effects (font (size 1.27 1.27)))"
    pins = []
    for side, x, ang in ((left, -hw - 2.54, 0), (right, hw + 2.54, 180)):
        for i, (num, pname, etype) in enumerate(side):
            pins.append(f'(pin {etype} line (at {x:g} {top - 2.54 * i:g} {ang}) (length 2.54) '
                        f'(name {q(pname)} {font}) (number {q(num)} {font}))')
    text = f"""(symbol {q(name)} (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" {q(prefix)} (at {-hw:g} {top + 3.81:g} 0) (effects (font (size 1.27 1.27)) (justify left)))
      (property "Value" {q(name)} (at {-hw:g} {-top - 3.81:g} 0) (effects (font (size 1.27 1.27)) (justify left)))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (property "Description" {q(desc)} (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (symbol {q(name + "_0_1")} (rectangle (start {-hw:g} {top + 2.54:g}) (end {hw:g} {-top - 2.54:g})
        (stroke (width 0.254) (type default)) (fill (type background))))
      (symbol {q(name + "_1_1")} {" ".join(pins)}))"""
    return parse(text)[0]


CUSTOM = {c[0]: _custom_symbol(*c) for c in design.CUSTOM_SYMBOLS}


def _lib(name):
    if name not in _libs:
        path = os.path.join(SHARE, "symbols", name + ".kicad_sym")
        tree = parse(open(path, encoding="utf8").read())[0]
        _libs[name] = {unq(s[1]): s for s in find_all(tree, "symbol")}
    return _libs[name]


def load_symbol(lib_id):
    """Library symbol with any `extends` parent folded in, named `Lib:Name`."""
    if lib_id in _symbols:
        return _symbols[lib_id]
    lib, name = lib_id.split(":")
    if lib == PROJECT:
        node = copy.deepcopy(CUSTOM[name])
    else:
        node = copy.deepcopy(_lib(lib)[name])
        ext = find(node, "extends")
        if ext:
            parent_name = unq(ext[1])
            parent = copy.deepcopy(_lib(lib)[parent_name])
            overrides = {unq(p[1]): p for p in find_all(node, "property")}
            for i, item in enumerate(parent):
                if isinstance(item, list) and item[0] == "property" and unq(item[1]) in overrides:
                    parent[i] = overrides.pop(unq(item[1]))
                elif isinstance(item, list) and item[0] == "symbol":
                    item[1] = q(name + unq(item[1])[len(parent_name):])
            at = next(i for i, x in enumerate(parent) if isinstance(x, list) and x[0] == "symbol")
            parent[at:at] = list(overrides.values())
            node = parent
    node[1] = q(lib_id)
    _symbols[lib_id] = node
    return node


def symbol_pins(lib_id):
    """[(number, name, type, x, y, angle, unit)]; unit 0 means every unit."""
    out = []
    for sub in find_all(load_symbol(lib_id), "symbol"):
        unit = int(unq(sub[1]).rsplit("_", 2)[1])
        for p in find_all(sub, "pin"):
            at = find(p, "at")
            out.append((unq(find(p, "number")[1]), unq(find(p, "name")[1]), p[1],
                        float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0, unit))
    return out


def symbol_units(lib_id):
    units = sorted({p[6] for p in symbol_pins(lib_id) if p[6] > 0})
    return units or [1]


def resolve(part):
    """{pin number: net}. Every pin must be assigned unless its type is no_connect."""
    nets, used = {}, set()
    spec = part["pins"]
    for num, name, etype, *_ in symbol_pins(part["lib_id"]):
        key = num if num in spec else name if name in spec else None
        if key is None:
            if etype != "no_connect":
                raise SystemExit(f"{part['ref']}: pin {num} ({name}) is not assigned")
            continue
        used.add(key)
        nets[num] = spec[key]
    unknown = set(spec) - used
    if unknown:
        raise SystemExit(f"{part['ref']}: no such pins {sorted(unknown)}")
    return nets


def netlist():
    """{net: sorted [(ref, pin)]} for real parts (power flags left out)."""
    nets = {}
    for part in design.PARTS:
        if part["ref"].startswith("#"):
            continue
        for num, net in resolve(part).items():
            if net != "NC":
                nets.setdefault(net, set()).add((part["ref"], num))
    return {k: sorted(v) for k, v in nets.items()}
