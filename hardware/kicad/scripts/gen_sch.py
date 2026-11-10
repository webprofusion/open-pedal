"""Generate open-pedal.kicad_sch (plus the project symbol library) from design.py.

The sheet is drawn netlist-style: parts are grouped by block and every pin
carries a net label, so connectivity is by name rather than by drawn wire.
"""
import copy
import os

from sexpr import dump, find, find_all, q, unq
from common import (PROJECT, PROJECT_DIR, CUSTOM, load_symbol, symbol_pins, symbol_units, resolve, uid)
import design

VERSION = "20251024"
GRID = 2.54
STUB = 2.54
CHAR = 1.15
PAGE_W = 594.0
MARGIN = 20.0
ROOT = uid("root")

# outward direction on the sheet (y down) for each library pin angle
OUT = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}
LABEL = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, -1): (90, "left"), (0, 1): (270, "right")}


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def place(px, py, ang, rot):
    """Library pin (y up) -> sheet offset and outward direction for a symbol rotated `rot`."""
    dx, dy = px, -py
    ox, oy = OUT[ang]
    for _ in range(rot // 90):
        dx, dy = dy, -dx
        ox, oy = oy, -ox
    return dx, dy, ox, oy


def items():
    """One layout item per symbol unit."""
    out = []
    for part in design.PARTS:
        nets = resolve(part)
        pins = symbol_pins(part["lib_id"])
        for unit in symbol_units(part["lib_id"]):
            conns = {}
            for num, name, etype, x, y, ang, u in pins:
                if u not in (0, unit) or num not in nets:
                    continue
                dx, dy, ox, oy = place(x, y, ang, part["rot"])
                if num in part.get("dirs", {}):
                    ox, oy = part["dirs"][num]
                key = (round(dx, 3), round(dy, 3))
                if key in conns and conns[key][2] != nets[num]:
                    raise SystemExit(f"{part['ref']}: stacked pins at {key} on different nets")
                conns[key] = (ox, oy, nets[num])
            ext = [4.0, 4.0, 4.0, 4.0]          # left, right, up, down
            for (dx, dy), (ox, oy, net) in conns.items():
                reach = STUB + 1.5 + (CHAR * len(net) if net != "NC" else 0)
                ext[0] = max(ext[0], -(dx + ox * reach) + 1, -dx + 2)
                ext[1] = max(ext[1], dx + ox * reach + 1, dx + 2)
                ext[2] = max(ext[2], -(dy + oy * reach) + 1, -dy + 3.5)
                ext[3] = max(ext[3], dy + oy * reach + 1, dy + 3.5)
            if not conns:
                ext = [6.0, 12.0, 5.0, 5.0]
            out.append(dict(part=part, unit=unit, conns=conns, ext=ext, small=len(pins) <= 2 and part["rot"] == 90))
    return out


def layout(all_items):
    y = MARGIN + 10
    titles = []
    for key, title in design.GROUPS:
        group = [i for i in all_items if i["part"]["group"] == key]
        titles.append((title, MARGIN, y))
        y += 6
        for chunk in ([i for i in group if not i["small"]], [i for i in group if i["small"]]):
            x, row = MARGIN, []
            for item in chunk + [None]:
                width = item and item["ext"][0] + item["ext"][1] + 3
                if item is None or (row and x + width > PAGE_W - MARGIN):
                    up = max(i["ext"][2] for i in row) if row else 0
                    down = max(i["ext"][3] for i in row) if row else 0
                    for i in row:
                        i["y"] = snap(y + up + GRID / 2)
                    y += up + down + (2 if chunk and chunk[0]["small"] else 8) if row else 0
                    x, row = MARGIN, []
                if item is not None:
                    item["x"] = snap(x + item["ext"][0] + GRID / 2)
                    x = item["x"] + item["ext"][1] + 3
                    row.append(item)
        y += 14
    return titles, y


def fmt(v):
    return f"{round(v, 4):g}"


def sym_instance(item):
    part, unit, x, y = item["part"], item["unit"], item["x"], item["y"]
    lib = load_symbol(part["lib_id"])
    ref = part["ref"]
    power = ref.startswith("#")
    node = ["symbol", ["lib_id", q(part["lib_id"])], ["at", fmt(x), fmt(y), str(part["rot"])], ["unit", str(unit)],
            ["exclude_from_sim", "no"], ["in_bom", "no" if power or not part["footprint"] else "yes"],
            ["on_board", "no" if power else "yes"], ["dnp", "no"], ["uuid", q(uid("sym", ref, unit))]]
    values = {"Reference": ref, "Value": part["value"], "Footprint": part["footprint"]}
    for prop in find_all(lib, "property"):
        name = unq(prop[1])
        if name not in ("Reference", "Value", "Footprint", "Datasheet", "Description"):
            continue
        p = copy.deepcopy(prop)
        if name in values:
            p[2] = q(values[name])
        at = find(p, "at")
        if item["small"]:
            off = {"Reference": -2.8, "Value": 2.8}.get(name, 0)
            at[1:] = [fmt(x), fmt(y + off), "90"]      # stored relative to the rotated symbol
            eff = find(p, "effects")
            eff[:] = [e for e in eff if not (isinstance(e, list) and e[0] == "justify")]
        else:
            at[1:] = [fmt(x + float(at[1])), fmt(y - float(at[2])), at[3] if len(at) > 3 else "0"]
        node.append(p)
    for num, name, etype, px, py, ang, u in symbol_pins(part["lib_id"]):
        if u in (0, unit):
            node.append(["pin", q(num), ["uuid", q(uid("pin", ref, unit, num))]])
    node.append(["instances", ["project", q(PROJECT), ["path", q("/" + ROOT), ["reference", q(ref)], ["unit", str(unit)]]]])
    return node


def connections(item):
    out = []
    ref, unit = item["part"]["ref"], item["unit"]
    for (dx, dy), (ox, oy, net) in sorted(item["conns"].items()):
        x, y = item["x"] + dx, item["y"] + dy
        tag = uid("conn", ref, unit, dx, dy)
        if net == "NC":
            out.append(["no_connect", ["at", fmt(x), fmt(y)], ["uuid", q(tag)]])
            continue
        ex, ey = x + ox * STUB, y + oy * STUB
        out.append(["wire", ["pts", ["xy", fmt(x), fmt(y)], ["xy", fmt(ex), fmt(ey)]],
                    ["stroke", ["width", "0"], ["type", "default"]], ["uuid", q(tag)]])
        ang, just = LABEL[(ox, oy)]
        out.append(["label", q(net), ["at", fmt(ex), fmt(ey), str(ang)],
                    ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", just, "bottom"]],
                    ["uuid", q(uid("label", ref, unit, dx, dy))]])
    return out


def text(s, x, y, size, bold=False):
    font = ["font", ["size", fmt(size), fmt(size)]] + ([["bold", "yes"]] if bold else [])
    return ["text", q(s), ["exclude_from_sim", "no"], ["at", fmt(x), fmt(y), "0"],
            ["effects", font, ["justify", "left", "bottom"]], ["uuid", q(uid("text", s))]]


def main():
    all_items = items()
    titles, height = layout(all_items)
    libs = []
    for lib_id in dict.fromkeys(p["lib_id"] for p in design.PARTS):
        libs.append(load_symbol(lib_id))
    sch = ["kicad_sch", ["version", VERSION], ["generator", q("open_pedal_gen")], ["generator_version", q("1.0")],
           ["uuid", q(ROOT)], ["paper", q("User"), fmt(PAGE_W), fmt(max(210, height + MARGIN))],
           ["title_block", ["title", q("open-pedal dock")], ["rev", q("A0")],
            ["comment", "1", q("Generated by hardware/kicad/scripts from design.py; edit that, not this sheet.")],
            ["comment", "2", q("Not built or measured. Check every pin strap against the current datasheets.")]],
           ["lib_symbols"] + libs]
    for title, x, y in titles:
        sch.append(text(title, x, y, 3.0, bold=True))
    for item in all_items:
        sch.extend(connections(item))
    for item in all_items:
        sch.append(sym_instance(item))
    sch.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
    sch.append(["embedded_fonts", "no"])
    with open(os.path.join(PROJECT_DIR, PROJECT + ".kicad_sch"), "w", encoding="utf8", newline="\n") as f:
        f.write(dump(sch) + "\n")

    lib = ["kicad_symbol_lib", ["version", VERSION], ["generator", q("open_pedal_gen")], ["generator_version", q("1.0")]]
    lib += [copy.deepcopy(CUSTOM[name]) for name in CUSTOM]
    with open(os.path.join(PROJECT_DIR, PROJECT + ".kicad_sym"), "w", encoding="utf8", newline="\n") as f:
        f.write(dump(lib) + "\n")
    with open(os.path.join(PROJECT_DIR, "sym-lib-table"), "w", encoding="utf8", newline="\n") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "open-pedal")(type "KiCad")'
                '(uri "${KIPRJMOD}/open-pedal.kicad_sym")(options "")(descr "open-pedal project symbols"))\n)\n')
    parts = [p for p in design.PARTS if not p["ref"].startswith("#")]
    print(f"schematic: {len(parts)} parts, {len(all_items)} symbols, sheet {PAGE_W:g} x {height + MARGIN:.0f} mm")


if __name__ == "__main__":
    main()
