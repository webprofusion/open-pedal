"""Generate open-pedal.kicad_pcb: outline, footprints with nets, first-pass placement.

Run with KiCad's own Python (it needs the pcbnew module). Connectors,
headers and holes go where hardware/layout.json puts them; everything else is
packed into a region per circuit block. Nothing is routed.
"""
import json
import os

import pcbnew

from common import PROJECT, PROJECT_DIR, HARDWARE_DIR, SHARE, resolve, uid
import design

LAYOUT = json.load(open(os.path.join(HARDWARE_DIR, "layout.json"), encoding="utf8"))
B = LAYOUT["board"]
OX, OY = 50.0, 50.0            # board (u, v) origin on the KiCad page
mm = pcbnew.FromMM
E = LAYOUT["enclosure"]
GAP = E["depth"] / 2 - E["wall"] - B["rear_edge_y"]      # board rear edge to the inside of the wall

# Rear-panel parts: rotation that points the mating face at the rear edge, and
# how far (mm) the front of the Fab outline sits behind the board edge.
# Jack: the body stops at the inside of the wall and the 3 mm ferrule passes through it.
REAR = {"jack": (90, GAP + 3.0), "pot": (270, None), "usb_c": (180, 1.2)}
# Pots: terminal row, mm in from the rear edge, so the mounting face meets the wall.
POT_PIN_V = {"RV1": 4.2 - GAP, "RV2": 5.0 - GAP}

# Regions (u0, v0, u1, v1) each block is packed into, tried in order.
REGIONS = {
    "power": [(1.5, 9.5, 33.5, 27.5), (33.5, 37, 56, 63), (1.5, 50, 33.5, 63)],
    "expression": [(33.5, 28, 56, 37)],
    "mcu": [(57, 28, 91, 63)],
    "controls": [(57, 28, 91, 63)],
    "dac": [(92, 28, 121, 45)],
    "phones": [(92, 45, 121, 63)],
    "adc": [(122, 28, 144.5, 45)],
    "input": [(122, 45, 145, 63), (145, 51, 174.5, 63)],
}


def xy(u, v):
    return pcbnew.VECTOR2I(mm(OX + u), mm(OY + v))


def enclosure_to_board(x, y):
    return x + B["width"] / 2, B["rear_edge_y"] - y


def _bbox(fp, items):
    """Bounding box in mm, relative to the footprint position."""
    pos = fp.GetPosition()
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for it in items:
        bb = it.GetBoundingBox()
        x0, y0 = min(x0, bb.GetLeft()), min(y0, bb.GetTop())
        x1, y1 = max(x1, bb.GetRight()), max(y1, bb.GetBottom())
    return (x0 - pos.x) / 1e6, (y0 - pos.y) / 1e6, (x1 - pos.x) / 1e6, (y1 - pos.y) / 1e6


def _shapes(fp, layers):
    return [g for g in fp.GraphicalItems() if g.GetLayer() in layers and g.Type() == pcbnew.PCB_SHAPE_T]


def local_bbox(fp, layers):
    return _bbox(fp, list(fp.Pads()) + _shapes(fp, layers))


def fab_bbox(fp):
    return _bbox(fp, _shapes(fp, (pcbnew.F_Fab,)))


def main():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    # The stock USB-C footprint puts its locating pegs 0.19 mm from the ground pads.
    board.GetDesignSettings().m_HoleClearance = mm(0.15)
    nets = {}

    def net(name):
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])
        return nets[name]

    # ---- outline
    def shape(kind):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(kind)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
        return s

    r = shape(pcbnew.SHAPE_T_RECT)
    r.SetStart(xy(0, 0))
    r.SetEnd(xy(B["width"], B["depth"]))
    keepouts = []
    rad = B["switch_cutout_diameter"] / 2
    for sw in LAYOUT["footswitches"]["items"]:
        u, v = enclosure_to_board(sw["x"], sw["y"])
        if 0 < v < B["depth"]:
            c = shape(pcbnew.SHAPE_T_CIRCLE)
            c.SetCenter(xy(u, v))
            c.SetEnd(xy(u + rad, v))
            keepouts.append((u - rad - 1, v - rad - 1, u + rad + 1, v + rad + 1))

    # ---- footprints
    fps = {}
    for part in design.PARTS:
        if not part["footprint"]:
            continue
        lib, name = part["footprint"].split(":")
        fp = pcbnew.FootprintLoad(os.path.join(SHARE, "footprints", lib + ".pretty"), name)
        if fp is None:
            raise SystemExit(f"{part['ref']}: footprint {part['footprint']} not found")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(part["ref"])
        fp.SetValue(part["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + uid("sym", part["ref"], 1)))
        pins = resolve(part)
        pads = {p.GetNumber() for p in fp.Pads()}
        missing = set(pins) - pads
        if missing:
            raise SystemExit(f"{part['ref']}: footprint {name} has no pads {sorted(missing)}")
        for pad in fp.Pads():
            n = pins.get(pad.GetNumber())
            if n and n != "NC":
                pad.SetNet(net(n))
        board.Add(fp)
        fps[part["ref"]] = fp

    placed = []                 # (u0, v0, u1, v1)

    def put(ref, u, v, rot=0):
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(xy(u, v))
        x0, y0, x1, y1 = local_bbox(fp, (pcbnew.F_CrtYd, pcbnew.F_Fab))
        placed.append((u + x0, v + y0, u + x1, v + y1))

    # ---- rear panel
    for item in LAYOUT["rear_panel"]:
        fp = fps[item["ref"]]
        rot, overhang = REAR[item["type"]]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(xy(0, 0))
        x0, y0, x1, y1 = fab_bbox(fp)
        u = item["u"] - (x0 + x1) / 2
        if overhang is None:
            pad1 = next(p for p in fp.Pads() if p.GetNumber() == "1")
            v = POT_PIN_V[item["ref"]] - (pad1.GetPosition().y - fp.GetPosition().y) / 1e6
        else:
            v = -overhang - y0
        put(item["ref"], u, v, rot)

    # ---- footswitch headers (switch and LED ring) and their capacitors
    by_place = {p["place"]: p["ref"] for p in design.PARTS if "place" in p}
    for sw in LAYOUT["footswitches"]["items"]:
        su, sv = enclosure_to_board(sw["x"], sw["y"])
        if sv < B["depth"]:                      # bank switch: header beside the board cut-out
            hu, hv = su + (13.5 if su < B["width"] / 2 else -21), sv + 14
        else:                                    # preset switch: header at the front edge, under the switch
            hu, hv = su - 3.75, B["depth"] - 5.0
        put(by_place[("switch", sw["name"])], hu, hv)
        put(by_place[("switch_cap", sw["name"])], hu + 1.25, hv - 4.2)
    put("J13", B["width"] / 2 - 6.0, B["depth"] - 5.0)        # OLED lead
    put("J15", 59.5, 31.0)                                    # SWD
    holes = [p["ref"] for p in design.PARTS if p["ref"].startswith("H")]
    for ref, (u, v) in zip(holes, B["mounting_holes"]):
        put(ref, u, v)

    # ---- everything else: greedy packing, largest parts first, inside the block's regions
    def blocker(box):
        """Right edge of the first placed box or keep-out that `box` overlaps, else None."""
        for k in placed + keepouts:
            if box[0] < k[2] + 0.4 and box[2] > k[0] - 0.4 and box[1] < k[3] + 0.4 and box[3] > k[1] - 0.4:
                return k[2] + 0.4
        return None

    fixed = {ref for ref, fp in fps.items() if fp.GetPosition().x != 0}
    todo = [p for p in design.PARTS if p["ref"] in fps and p["ref"] not in fixed]
    boxes = {p["ref"]: local_bbox(fps[p["ref"]], (pcbnew.F_CrtYd,)) for p in todo}

    def size(p):
        x0, y0, x1, y1 = boxes[p["ref"]]
        a = (x1 - x0) * (y1 - y0)
        return -a if a > 12 else 0           # big parts first, then design order

    for part in sorted(todo, key=size):
        x0, y0, x1, y1 = boxes[part["ref"]]
        spot = None
        for (ru0, rv0, ru1, rv1) in REGIONS[part["group"]]:
            v = rv0 - y0
            while spot is None and v + y1 <= rv1:
                u = ru0 - x0
                while u + x1 <= ru1:
                    hit = blocker((u + x0, v + y0, u + x1, v + y1))
                    if hit is None:
                        spot = (u, v)
                        break
                    u = max(u + 0.25, hit - x0)
                v += 0.5
            if spot:
                break
        if spot is None:
            raise SystemExit(f"{part['ref']}: no room left in the {part['group']} region")
        put(part["ref"], round(spot[0], 2), round(spot[1], 2))

    # ---- silkscreen title
    t = pcbnew.PCB_TEXT(board)
    t.SetText("open-pedal rev A0 - unrouted")
    t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(xy(137.0, B["depth"] - 1.6))
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    t.SetTextThickness(mm(0.15))
    board.Add(t)

    out = os.path.join(PROJECT_DIR, PROJECT + ".kicad_pcb")
    pcbnew.SaveBoard(out, board)
    print(f"board: {len(fps)} footprints, {len(nets)} nets, {B['width']:g} x {B['depth']:g} mm")


if __name__ == "__main__":
    main()
