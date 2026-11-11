"""Build the open-pedal enclosure model in Blender from hardware/layout.json.

    blender --background --python enclosure/build_enclosure.py

Writes enclosure/open-pedal.blend and six renders in enclosure/renders/: the
bare unit and the removable device holder with a tablet (an iPad mini) and with a phone.
The renders are path-traced with Cycles; set OPEN_PEDAL_SAMPLES or OPEN_PEDAL_VIEWS for a quicker check.
Tested with Blender 5.2. The board is the KiCad export
hardware/kicad/exports/open-pedal-board.glb (run hardware/kicad/scripts/build.py
first); jacks, pots, LED-ring footswitches and the display are simplified stand-ins.

Dimensions in layout.json are millimetres; the scene is built in metres.
"""
import json
import math
import os

import bpy
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
L = json.load(open(os.path.join(REPO, "hardware", "layout.json"), encoding="utf8"))
BOARD_GLB = os.path.join(REPO, "hardware", "kicad", "exports", "open-pedal-board.glb")
MM = 0.001

E, B = L["enclosure"], L["board"]
W, D, H, WALL = E["width"], E["depth"], E["height"], E["wall"]
BASE = E["base_plate"]
TOP_IN = H - WALL                       # underside of the top face
REAR_IN = D / 2 - WALL                  # inside of the rear wall
PCB_TOP = B["top_z"]
PCB_GLB_TOP = 1.56                      # top surface height in the KiCad export


def board_xy(u, v):
    return u - B["width"] / 2, B["rear_edge_y"] - v


# ---------------------------------------------------------------- scene helpers
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"


def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_SHELL, C_CONTROLS, C_REAR, C_BOARD, C_LABELS, C_HOLDER, C_DEVICE, C_STAGE = (
    collection(n) for n in ("Enclosure", "Controls", "Rear panel parts", "Board", "Labels",
                            "Device holder", "Example devices", "Stage"))


def material(name, color, metallic=0.0, roughness=0.5, emission=None, strength=0.0, alpha=1.0,
             bevel=0.3, grain=None, coat=0.0):
    """Principled material. bevel (mm) rounds sharp edges at render time (Cycles bevel node, so the
    meshes stay simple). grain = (noise scale per metre, bump strength, roughness variation) adds a
    fine surface texture."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.05
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1.0)
        p.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
    normal = None
    if bevel:
        bv = nt.nodes.new("ShaderNodeBevel")
        bv.samples = 4
        bv.inputs["Radius"].default_value = bevel * MM
        normal = bv.outputs["Normal"]
    if grain:
        scale, bump, rough_var = grain
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = 4.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        if bump:
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            bp.inputs["Distance"].default_value = 0.0002
            nt.links.new(nz.outputs[0], bp.inputs["Height"])
            if normal:
                nt.links.new(normal, bp.inputs["Normal"])
            normal = bp.outputs["Normal"]
        if rough_var:
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.inputs[3].default_value = max(roughness - rough_var, 0.02)
            mr.inputs[4].default_value = min(roughness + rough_var, 1.0)
            nt.links.new(nz.outputs[0], mr.inputs[0])
            nt.links.new(mr.outputs[0], p.inputs["Roughness"])
    if normal:
        nt.links.new(normal, p.inputs["Normal"])
    m.diffuse_color = (*color, alpha)
    return m


M_BODY = material("Body black powder coat", (0.014, 0.014, 0.016), metallic=0.0, roughness=0.5,
                  bevel=1.2, grain=(2500.0, 0.25, 0.08))
next(n for n in M_BODY.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Specular IOR Level"].default_value = 0.35
M_ALU = material("Bare aluminium", (0.72, 0.73, 0.74), metallic=1.0, roughness=0.32, grain=(900.0, 0.0, 0.08))
M_CHROME = material("Chrome", (0.92, 0.92, 0.93), metallic=1.0, roughness=0.06, bevel=0.5)
M_BLACK = material("Black plastic", (0.015, 0.015, 0.017), roughness=0.35, bevel=0.6)
M_RUBBER = material("Rubber", (0.02, 0.02, 0.02), roughness=0.85, bevel=0.6, grain=(1500.0, 0.2, 0.05))
M_PRINT = material("Label print", (0.86, 0.86, 0.84), roughness=0.55, bevel=0)
M_GLASS = material("Display glass", (0.005, 0.006, 0.01), roughness=0.04, bevel=0)
M_OLED = material("Display lit", (0.1, 0.5, 1.0), emission=(0.25, 0.65, 1.0), strength=5.0, bevel=0)
M_OLED_PCB = material("Display board", (0.02, 0.09, 0.25), roughness=0.5)
M_LED_ON = material("LED ring lit", (0.02, 0.5, 0.15), roughness=0.3, emission=(0.03, 1.0, 0.22), strength=5.0,
                    bevel=0)
M_LED_OFF = material("LED ring dim", (0.14, 0.20, 0.17), roughness=0.25, emission=(0.03, 1.0, 0.22), strength=0.06,
                     bevel=0)
M_BRASS = material("Standoff", (0.78, 0.6, 0.25), metallic=1.0, roughness=0.3)
M_PRINTED = material("Holder black printed plastic", (0.016, 0.016, 0.017), roughness=0.5, bevel=0.5,
                     grain=(4000.0, 0.3, 0.1))
M_FOAM = material("Holder foam pad", (0.02, 0.02, 0.02), roughness=1.0, bevel=0.4, grain=(1200.0, 0.8, 0.0))
M_DEVICE = material("Example device aluminium", (0.33, 0.34, 0.36), metallic=1.0, roughness=0.3, bevel=0.9,
                    grain=(3000.0, 0.0, 0.05))
M_DEVICE_GLASS = material("Example device glass", (0.004, 0.004, 0.005), roughness=0.03, bevel=0.2)
M_LENS = material("Example device camera lens", (0.01, 0.01, 0.015), roughness=0.02, coat=1.0)
M_UI_TEXT = material("Example app text", (0.9, 0.9, 0.9), roughness=0.05, emission=(0.95, 0.95, 0.92), strength=2.2,
                     bevel=0)
M_UI_DIM = material("Example app panel", (0.05, 0.05, 0.06), roughness=0.05, emission=(0.10, 0.11, 0.14),
                    strength=1.5, bevel=0)
M_UI_ACCENT = material("Example app accent", (1.0, 0.5, 0.1), roughness=0.05, emission=(1.0, 0.45, 0.08),
                       strength=2.5, bevel=0)


def screen_material():
    """Lit display: a dark vertical gradient, glossy like the glass above it."""
    m = material("Example device screen", (0.01, 0.01, 0.015), roughness=0.04, bevel=0)
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.012, 0.016, 0.030, 1.0)
    ramp.color_ramp.elements[1].color = (0.050, 0.035, 0.075, 1.0)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs[1], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = 1.6
    return m


M_SCREEN = screen_material()


def obj_from_bm(name, bm, coll, mat=None):
    """Finish a bmesh built in millimetres: scale to metres, shade, link."""
    bmesh.ops.scale(bm, vec=(MM, MM, MM), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle() < math.radians(35)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    if mat:
        mesh.materials.append(mat)
    return ob


def add_box(bm, size, center):
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=r["verts"])
    bmesh.ops.translate(bm, vec=center, verts=r["verts"])


def add_cyl(bm, radius, a, b, segments=48):
    """Cylinder from point a to point b (mm)."""
    a, b = Vector(a), Vector(b)
    axis = b - a
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius,
                              depth=axis.length)
    rot = Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=r["verts"])


def add_rounded_prism(bm, w, d, radius, z0, z1, center=(0.0, 0.0), matrix=None):
    """Rounded rectangle w x d in XY, extruded from z0 to z1."""
    pts, steps = [], 10
    for cx, cy, start in ((w / 2 - radius, d / 2 - radius, 0), (-w / 2 + radius, d / 2 - radius, 90),
                          (-w / 2 + radius, -d / 2 + radius, 180), (w / 2 - radius, -d / 2 + radius, 270)):
        for i in range(steps + 1):
            a = math.radians(start + 90 * i / steps)
            pts.append((center[0] + cx + radius * math.cos(a), center[1] + cy + radius * math.sin(a)))
    verts = [bm.verts.new((x, y, z0)) for x, y in pts]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    new = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=new)
    if matrix is not None:
        bmesh.ops.transform(bm, matrix=matrix, verts=verts + new)


def simple(name, coll, mat, build):
    bm = bmesh.new()
    build(bm)
    return obj_from_bm(name, bm, coll, mat)


def cut(target, cutter):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = mesh
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter)


def label(text, x, y, size, z=H + 0.03):
    cu = bpy.data.curves.new("label " + text, "FONT")
    cu.body = text
    cu.size = size * MM
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.02 * MM
    cu.materials.append(M_PRINT)
    ob = bpy.data.objects.new("label " + text, cu)
    ob.location = (x * MM, y * MM, z * MM)
    C_LABELS.objects.link(ob)
    return ob


# ---------------------------------------------------------------- enclosure
shell = simple("Enclosure body", C_SHELL, M_BODY,
               lambda bm: add_rounded_prism(bm, W, D, E["corner_radius"], BASE, H))


def cutters(bm):
    add_rounded_prism(bm, W - 2 * WALL, D - 2 * WALL, E["corner_radius"] - WALL, BASE - 1, TOP_IN)
    for s in L["footswitches"]["items"]:
        add_cyl(bm, L["footswitches"]["hole_diameter"] / 2, (s["x"], s["y"], TOP_IN - 1), (s["x"], s["y"], H + 1))
    o = L["oled"]
    add_rounded_prism(bm, o["window"][0], o["window"][1], 1.0, TOP_IN - 1, H + 1, center=(o["x"], o["y"]))
    rc = L["rear_cutouts"]
    for item in L["rear_panel"]:
        x, _ = board_xy(item["u"], 0)
        spec = rc[item["type"]]
        z = PCB_TOP + spec["axis_z"]
        if item["type"] == "usb_c":
            # rounded slot in the XZ plane, pushed through the wall along Y
            m = Matrix.Translation((x, REAR_IN - 1, z)) @ Matrix.Rotation(math.radians(-90), 4, "X")
            add_rounded_prism(bm, spec["width"], spec["height"], spec["height"] / 2 - 0.01, 0, WALL + 2, matrix=m)
        else:
            add_cyl(bm, spec["diameter"] / 2, (x, REAR_IN - 1, z), (x, D / 2 + 1, z))
    for x, y in L["holder"]["mount"]["holes"]:          # threaded holes for the holder thumbscrews
        add_cyl(bm, L["holder"]["mount"]["hole_diameter"] / 2, (x, y, TOP_IN - 1), (x, y, H + 1), 24)


cut(shell, simple("cutters", C_SHELL, None, cutters))
for p in shell.data.polygons:
    p.use_smooth = False

simple("Base plate", C_SHELL, M_ALU, lambda bm: add_rounded_prism(bm, W, D, E["corner_radius"], 0, BASE))


def feet(bm):
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 - 14), sy * (D / 2 - 14)
            add_cyl(bm, 6, (x, y, -2.5), (x, y, 0))


simple("Feet", C_SHELL, M_RUBBER, feet)

# ---------------------------------------------------------------- footswitches
FS = L["footswitches"]


def switch_metal(bm):
    ring = FS["ring_diameter"] / 2
    for s in FS["items"]:
        x, y = s["x"], s["y"]
        add_cyl(bm, 5.9, (x, y, TOP_IN - 2), (x, y, H + 2.0))                 # threaded bushing
        add_cyl(bm, ring + 1.5, (x, y, H), (x, y, H + 3.0))                   # bezel
        add_cyl(bm, 4.6, (x, y, H + 3.0), (x, y, H + 12.0))                   # actuator
        add_cyl(bm, 5.2, (x, y, H + 11.0), (x, y, H + 12.5))                  # actuator cap


def switch_bodies(bm):
    depth = FS["body_depth"]
    for s in FS["items"]:
        x, y = s["x"], s["y"]
        add_box(bm, (15.0, 17.0, depth - 6), (x, y, TOP_IN - (depth - 6) / 2))
        for dx in (-3.5, 3.5):
            add_box(bm, (2.0, 0.6, 6.0), (x + dx, y, TOP_IN - depth + 3))     # solder lugs


simple("Footswitch hardware", C_CONTROLS, M_CHROME, switch_metal)
simple("Footswitch bodies", C_CONTROLS, M_BLACK, switch_bodies)
for s in FS["items"]:
    label(s["label"], s["x"], s["y"] - 14.5, 5.0 if len(s["label"]) == 1 else 3.6)

# ---------------------------------------------------------------- LED rings built into the footswitches
# Shown as in use: the active preset bright, the other rings dim.
for s in FS["items"]:
    simple("LED ring " + s["name"], C_CONTROLS, M_LED_ON if s["name"] == "PRESET_A" else M_LED_OFF,
           lambda bm, s=s: add_cyl(bm, FS["ring_diameter"] / 2, (s["x"], s["y"], H + 3.0), (s["x"], s["y"], H + 4.2)))

# ---------------------------------------------------------------- display
o = L["oled"]
mw, md, mh = o["module"]
simple("OLED glass", C_CONTROLS, M_GLASS,
       lambda bm: add_box(bm, (o["window"][0] + 1.5, o["window"][1] + 4.0, 1.5), (o["x"], o["y"], TOP_IN - 0.75)))
simple("OLED module board", C_CONTROLS, M_OLED_PCB,
       lambda bm: add_box(bm, (mw, md, 1.2), (o["x"], o["y"], TOP_IN - 1.5 - 0.6)))
simple("OLED lit area", C_CONTROLS, M_OLED,
       lambda bm: add_box(bm, (o["window"][0] - 3.0, 0.5, 0.05), (o["x"], o["y"] - 3.6, TOP_IN + 0.05)))
readout = label("BANK 03  A", o["x"], o["y"] + 0.8, 3.4, z=TOP_IN + 0.03)
readout.name = "OLED readout"
readout.data.materials.clear()
readout.data.materials.append(M_OLED)
C_LABELS.objects.unlink(readout)
C_CONTROLS.objects.link(readout)

# ---------------------------------------------------------------- rear panel parts
RC = L["rear_cutouts"]


def rear_plastic(bm):
    for item in L["rear_panel"]:
        x, _ = board_xy(item["u"], 0)
        if item["type"] == "jack":          # Neutrik NMJ body: 18.2 wide, 20.6 deep, about 16 high
            add_box(bm, (18.2, 20.6, 16.0), (x, REAR_IN - 10.3, PCB_TOP + 8.0))
        elif item["type"] == "pot":         # Alps RK09 body
            add_box(bm, (9.8, 6.8, 11.0), (x, REAR_IN - 0.8 - 3.4, PCB_TOP + 5.5))


def rear_metal(bm):
    for item in L["rear_panel"]:
        x, _ = board_xy(item["u"], 0)
        z = PCB_TOP + RC[item["type"]]["axis_z"]
        if item["type"] == "jack":          # chrome ferrule through the wall
            add_cyl(bm, 5.7, (x, REAR_IN, z), (x, D / 2 + 0.5, z))
        elif item["type"] == "pot":         # shaft
            add_cyl(bm, 3.0, (x, REAR_IN - 0.8, z), (x, D / 2 + 14.0, z), 32)


def rear_dark(bm):
    for item in L["rear_panel"]:
        x, _ = board_xy(item["u"], 0)
        z = PCB_TOP + RC[item["type"]]["axis_z"]
        if item["type"] == "jack":          # socket opening
            add_cyl(bm, 3.3, (x, D / 2 + 0.45, z), (x, D / 2 + 0.6, z), 32)
        elif item["type"] == "pot":         # knob
            add_cyl(bm, 6.5, (x, D / 2 + 2.0, z), (x, D / 2 + 14.5, z))


simple("Jack and pot bodies", C_REAR, M_BLACK, rear_plastic)
simple("Jack ferrules and pot shafts", C_REAR, M_CHROME, rear_metal)
simple("Knobs and jack openings", C_REAR, M_BLACK, rear_dark)
for item in L["rear_panel"]:
    x, _ = board_xy(item["u"], 0)
    label(item["name"], x, D / 2 - 6.5, 2.3)
label("open-pedal", 0, 31.0, 4.5)

# ---------------------------------------------------------------- board
def standoffs(bm):
    for u, v in B["mounting_holes"]:
        x, y = board_xy(u, v)
        add_cyl(bm, 3.0, (x, y, BASE), (x, y, PCB_TOP - B["thickness"]), segments=6)


simple("Board standoffs", C_BOARD, M_BRASS, standoffs)
if os.path.exists(BOARD_GLB):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=BOARD_GLB)
    new = [ob for ob in bpy.data.objects if ob not in before]
    for ob in new:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        C_BOARD.objects.link(ob)
    root = bpy.data.objects.new("Board (KiCad export)", None)
    C_BOARD.objects.link(root)
    for ob in new:
        if ob.parent is None:
            ob.parent = root
    x0, y0 = board_xy(0, 0)
    root.location = (x0 * MM, y0 * MM, (PCB_TOP - PCB_GLB_TOP) * MM)
else:
    print("WARNING: board export not found, run hardware/kicad/scripts/build.py first:", BOARD_GLB)
    simple("Board (placeholder)", C_BOARD, material("PCB", (0.0, 0.25, 0.1)),
           lambda bm: add_box(bm, (B["width"], B["depth"], B["thickness"]),
                              (0, B["rear_edge_y"] - B["depth"] / 2, PCB_TOP - B["thickness"] / 2)))

# ---------------------------------------------------------------- removable device holder
# Local holder frame: x across, s up the slope from the ledge, n out of the backrest towards the player.
HD = L["holder"]
HA = math.radians(HD["angle_deg"])
CA, SA = math.cos(HA), math.sin(HA)
H_TB, H_S = HD["backrest"]["thickness"], HD["backrest"]["height"]
H_NL, H_LIP = HD["ledge"]["depth"], HD["ledge"]["lip_height"]
H_LEDGE_T, H_LIP_T = 4.0, 3.0
H_HW = HD["width"] / 2                       # half width over the cheeks
H_CW = H_HW - HD["cheek"]                    # half width of the centre section
H_YP = HD["front_y"] + H_LEDGE_T * CA + (H_NL + H_LIP_T) * SA
H_ZP = H + HD["rise"]
HM = Matrix.Translation((0, H_YP, H_ZP)) @ Matrix.Rotation(HA, 4, "X")
HOOK_IN, HOOK_OUT = D / 2 + 0.3, D / 2 + 3.5
ARM, JAW = HD["arms"], HD["jaws"]


def hw(s, n):
    """Holder (s, n) to enclosure (y, z)."""
    return H_YP + s * CA - n * SA, H_ZP + s * SA + n * CA


def add_profile(bm, pts, x0, x1):
    """Polygon in the YZ plane extruded along X."""
    verts = [bm.verts.new((x0, y, z)) for y, z in pts]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(x1 - x0, 0, 0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])


def holder_obj(name, mat, local=None, world=None, coll=None):
    bm = bmesh.new()
    if local:
        local(bm)
        bmesh.ops.transform(bm, matrix=HM, verts=bm.verts)
    if world:
        world(bm)
    return obj_from_bm(name, bm, coll or C_HOLDER, mat)


def cut_local(target, size, center):
    cut(target, holder_obj("cutter", None, local=lambda bm: add_box(bm, size, center)))


# cross-section shared by the centre section and the cheeks: backrest face, ledge, lip, base, rear hook
_front = [hw(H_S, 0), hw(0, 0), hw(0, H_NL), hw(H_LIP, H_NL), hw(H_LIP, H_NL + H_LIP_T),
          hw(-H_LEDGE_T, H_NL + H_LIP_T), (HD["front_y"], H), (HOOK_IN, H),
          (HOOK_IN, H - HD["hook_drop"]), (HOOK_OUT, H - HD["hook_drop"])]
_s_hook = (HOOK_OUT - H_YP - H_TB * SA) / CA           # where the backrest's rear face meets the hook
_rear_top = hw(H_S, -H_TB)
FOOT_F, FOOT_R = HD["leg_foot_y"]
centre_profile = _front + [hw(_s_hook, -H_TB), _rear_top]
cheek_profile = _front + [(FOOT_F, 0.0), (FOOT_R, 0.0), _rear_top]


def holder_tabs(bm):
    for x, y in HD["mount"]["holes"]:
        sx = 1 if x > 0 else -1
        add_rounded_prism(bm, 18.0, 12.0, 3.0, H, H + 4.0, center=(sx * (H_HW - 9.0), HD["front_y"] - 5.5))


holder_centre = holder_obj("Holder centre", M_PRINTED, world=lambda bm: (
    add_profile(bm, centre_profile, -H_CW, H_CW), holder_tabs(bm)))
holder_cheeks = holder_obj("Holder cheeks and legs", M_PRINTED, world=lambda bm: (
    add_profile(bm, cheek_profile, -H_HW, -H_CW), add_profile(bm, cheek_profile, H_CW, H_HW)))

# lightening window in each leg: the leg outline shrunk about its centre
_leg = [(HOOK_OUT, H - HD["hook_drop"]), (FOOT_F, 0.0), (FOOT_R, 0.0), _rear_top, hw(_s_hook, -H_TB)]
_cy, _cz = sum(p[0] for p in _leg) / len(_leg), sum(p[1] for p in _leg) / len(_leg)
LT = HD["lightening"]
_window = [(_cy + LT["leg_window"] * (y - _cy), _cz + LT["leg_window"] * (z - _cz)) for y, z in _leg]
cut(holder_cheeks, holder_obj("cutter", None, world=lambda bm: add_profile(bm, _window, -H_HW - 5, H_HW + 5)))

# T-slots for the two side arms, right through the backrest and both cheeks
N_ARM = -H_TB / 2 - 0.25                               # arm centre depth inside the backrest
for part in (holder_centre, holder_cheeks):
    for s_arm in ARM["s"]:
        cut_local(part, (2 * H_HW + 10, ARM["width"] + 0.5, ARM["thickness"] + 0.5), (0, s_arm, N_ARM))
        cut_local(part, (2 * H_HW + 10, 6.0, -N_ARM + 2.0), (0, s_arm, (N_ARM + 2.0) / 2))
# slot in the ledge and lip for a right-angle charging plug (portrait phone)
_slot_s0 = -(HD["rise"] - 2.0) / SA
cut_local(holder_centre, (HD["ledge"]["cable_slot"], H_LIP - _slot_s0 + 2, H_NL + H_LIP_T + 2),
          (0, (H_LIP + 2 + _slot_s0) / 2, (H_NL + H_LIP_T + 2) / 2))


# Lightening. Honeycomb cut into the backrest from the rear, left solid at the edges and around the two
# arm lock knobs.
SLOT_FRONT = N_ARM + (ARM["thickness"] + 0.5) / 2      # front of the arm channels = back of the front skin
def honeycomb(bm):
    flat, rib, border = LT["hex_flat"], LT["rib"], LT["border"]
    radius = flat / math.sqrt(3)                        # hexagon corner radius; flats face up and down the slope
    pitch_s, pitch_x = flat + rib, (flat + rib) * math.cos(math.radians(30))
    s_min, s_max = border + flat / 2, H_S - border - flat / 2
    cols = int((H_CW - border - radius) / pitch_x)
    for i in range(-cols, cols + 1):
        s = s_min + (pitch_s / 2 if i % 2 else 0.0)
        while s <= s_max:
            x = i * pitch_x
            near_knob = any(math.hypot(x - sx * ARM["lock_x"], s - s_arm) < 6.0 + radius + 1.0
                            for sx, s_arm in zip((-1, 1), ARM["s"]))
            if not near_knob:
                # Below the arm slots the holes go right through. Elsewhere they stop behind a front skin,
                # so the face the device rests on and the lips that hold the arms stay whole.
                through = s + flat / 2 < min(ARM["s"]) - ARM["width"] / 2 - 1.0
                add_cyl(bm, radius, (x, s, -H_TB - 1), (x, s, 1.0 if through else SLOT_FRONT - 0.1), segments=6)
            s += pitch_s


cut(holder_centre, holder_obj("cutter", None, local=honeycomb))


# Pockets under the ledge, open to the bottom, leaving the ledge and front wall as a shell with cross ribs.
def base_pockets(bm):
    wall = LT["wall"]
    y0, y1 = HD["front_y"] + wall, HOOK_IN - wall
    under_ledge = hw(-H_LEDGE_T, 0)                     # underside of the ledge at the device's rear corner
    y_front, z_front = hw(-H_LEDGE_T, H_NL + H_LIP_T)   # and at the front wall
    slope = (under_ledge[1] - z_front) / (under_ledge[0] - y_front)
    pocket = [(y0, H - 1), (y1, H - 1), (y1, under_ledge[1] - wall / 2), (under_ledge[0], under_ledge[1] - wall / 2),
              (y0, z_front + slope * (y0 - y_front) - wall / 2)]
    inner = HD["ledge"]["cable_slot"] / 2 + wall        # keep the middle solid around the cable slot
    n = LT["pocket_ribs"] // 2 + 1
    step = (H_CW - wall - inner + wall) / n
    for sx in (-1, 1):
        for k in range(n):
            a, b = inner + k * step, inner + (k + 1) * step - wall
            add_profile(bm, pocket, sx * a, sx * b)


cut(holder_centre, holder_obj("cutter", None, world=base_pockets))
for part in (holder_centre, holder_cheeks):
    for p in part.data.polygons:
        p.use_smooth = False


def ledge_pads(bm):
    half_slot = HD["ledge"]["cable_slot"] / 2 + 2
    for sx in (-1, 1):
        add_box(bm, (H_HW - half_slot - 2, 1.5, H_NL - 2), (sx * (half_slot + H_HW - 2) / 2, 0.75, H_NL / 2))


def leg_feet(bm):
    for sx in (-1, 1):
        add_box(bm, (HD["cheek"], FOOT_R - FOOT_F, 2.5), (sx * (H_HW + H_CW) / 2, (FOOT_F + FOOT_R) / 2, -1.25))


holder_obj("Holder ledge pads", M_FOAM, local=ledge_pads)
holder_obj("Holder leg feet", M_RUBBER, world=leg_feet)


def holder_knobs_local(bm):                             # arm lock knobs on the rear of the backrest
    for sx, s_arm in zip((-1, 1), ARM["s"]):
        add_cyl(bm, 6.0, (sx * ARM["lock_x"], s_arm, -H_TB), (sx * ARM["lock_x"], s_arm, -H_TB - 8.0), 12)


def holder_knobs_world(bm):                             # thumbscrews into the top face
    for x, y in HD["mount"]["holes"]:
        add_cyl(bm, 5.5, (x, y, H + 4.0), (x, y, H + 10.0), 12)


holder_obj("Holder knobs and thumbscrews", M_BLACK, local=holder_knobs_local, world=holder_knobs_world)

# Side arms. Each is built with the inside face of its jaw wall at x = 0 and placed by its object X location,
# so sliding the object along X in the .blend is the adjustment the real part makes.
JAW_MIN = ARM["length"] - JAW["wall"] - H_HW            # arm fully in: its inner end is flush with the far cheek
JAW_MAX = ARM["length"] - JAW["wall"] + ARM["lock_x"] - 4.0   # arm out as far as the lock knob still bears on it
print("holder: device width %.0f to %.0f mm" % (2 * (JAW_MIN - JAW["pad"]), 2 * (JAW_MAX - JAW["pad"])))
jaws = []
for sx, s_arm, side in zip((-1, 1), ARM["s"], ("left", "right")):
    def bx(bm, o0, o1, s0, s1, n0, n1, sx=sx):          # o = distance outward from the jaw wall's inside face
        add_box(bm, (o1 - o0, s1 - s0, n1 - n0), (sx * (o0 + o1) / 2, (s0 + s1) / 2, (n0 + n1) / 2))

    js0, js1 = JAW["s"]
    jd, jw, jl, jp = JAW["depth"], JAW["wall"], JAW["lip"], JAW["pad"]
    arm = holder_obj("Holder side arm " + side, M_PRINTED, local=lambda bm: (
        bx(bm, 0, jw, js0, js1, 0.4, jd),                                           # side wall
        bx(bm, -jl, 0, js0, js1, jd - 3.0, jd),                                     # front lip
        bx(bm, -15.0, jw, s_arm - 2.6, s_arm + 2.6, N_ARM, 0.5),                    # neck through the slot
        bx(bm, jw - ARM["length"], jw, s_arm - ARM["width"] / 2, s_arm + ARM["width"] / 2,
           N_ARM - ARM["thickness"] / 2, N_ARM + ARM["thickness"] / 2)))            # sliding bar
    pad = holder_obj("Holder side pad " + side, M_FOAM, local=lambda bm: (
        bx(bm, -jp, 0, js0 + 2, js1 - 2, 0.8, jd - 3.0),                            # against the device edge
        bx(bm, -jl, -jp, js0 + 2, js1 - 2, jd - 4.5, jd - 3.0)))                    # under the lip
    pad.parent = arm
    jaws.append((sx, arm))


def plastic_cm3(objects):
    total = 0.0
    for ob in objects:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        total += abs(bm.calc_volume()) * 1e6
        bm.free()
    return total


print("holder: about %.0f cm3 of printed plastic" % plastic_cm3([holder_centre, holder_cheeks] + [a for _, a in jaws]))


def set_jaws(device_width):
    half = min(max(device_width / 2 + JAW["pad"] - 0.5, JAW_MIN), JAW_MAX)
    for sx, arm in jaws:
        arm.location.x = sx * half * MM


def local_matrix(x, s_up, n):
    """Object matrix (metres) for something lying flat on the holder's backrest plane at (x, s, n) mm."""
    y, z = hw(s_up, n)
    return Matrix.Translation((x * MM, y * MM, z * MM)) @ Matrix.Rotation(HA, 4, "X")


def screen_text(text, x, s_up, n, size, mat):
    cu = bpy.data.curves.new("screen " + text, "FONT")
    cu.body = text
    cu.size = size * MM
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.materials.append(mat)
    ob = bpy.data.objects.new("Example app text " + text, cu)
    C_DEVICE.objects.link(ob)
    ob.matrix_world = local_matrix(x, s_up, n)
    return ob


def image_screen_material(path):
    """Lit display showing an image, glossy like the glass above it."""
    m = material("Example device screen image", (0.0, 0.0, 0.0), roughness=0.04, bevel=0)
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = 3.5
    return m, tex.image


def add_image_quad(bm, w, h, cx, cs, n, v0, v1):
    """Flat rectangle in the holder frame, UV-mapped to the image rows between v0 and v1."""
    verts = [bm.verts.new(q) for q in ((cx - w / 2, cs - h / 2, n), (cx + w / 2, cs - h / 2, n),
                                       (cx + w / 2, cs + h / 2, n), (cx - w / 2, cs + h / 2, n))]
    face = bm.faces.new(verts)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, co in zip(face.loops, ((0, v0), (1, v0), (1, v1), (0, v1))):
        loop[uv].uv = co


def example_device(key, spec):
    """A device resting on the ledge: aluminium body, glass front, a lit display and a rear camera if the
    spec asks for one. The display shows the spec's screen_image, or a generic amp-app screen (preset
    name and a row of dials) if it has none."""
    w, h, t = spec["size"]
    r, bezel = spec["corner_radius"], spec["bezel"]
    name = spec["name"]
    s0 = 1.5                                            # bottom edge sits on the ledge pad
    cs = s0 + h / 2                                     # centre, up the slope
    n_back, n_front = 0.2, 0.2 + t
    dw, dh = w - 2 * bezel, h - 2 * bezel               # lit display area
    parts = []

    def part(suffix, mat, build):
        ob = holder_obj("Example " + name + suffix, mat, coll=C_DEVICE, local=build)
        parts.append(ob)
        return ob

    part("", M_DEVICE, lambda bm: add_rounded_prism(bm, w, h, r, n_back, n_front - 0.3, center=(0, cs)))
    part(" glass", M_DEVICE_GLASS, lambda bm: add_rounded_prism(
        bm, w - 1.0, h - 1.0, r - 0.5, n_front - 0.3, n_front, center=(0, cs)))
    shot = spec.get("screen_image")
    shot = os.path.join(REPO, shot) if shot else None
    if shot and os.path.exists(shot):
        # A screenshot fills the display height; the strips left at the sides take the image's background colour.
        mat, img = image_screen_material(shot)
        crop = spec.get("screen_crop_top", 0)            # pixel rows to drop from the top (a window title bar)
        px_w, px_h = img.size[0], img.size[1] - crop
        iw = min(dw, dh * px_w / px_h)
        ih = iw * px_h / px_w
        backing = material("Example device screen backing", (0.0, 0.0, 0.0), roughness=0.04, bevel=0,
                           emission=tuple(spec.get("screen_background", (0.011, 0.011, 0.013))), strength=3.5)
        part(" screen", backing, lambda bm: add_rounded_prism(
            bm, dw, dh, min(4.0, bezel), n_front, n_front + 0.02, center=(0, cs)))
        part(" screen image", mat, lambda bm: add_image_quad(bm, iw, ih, 0, cs, n_front + 0.04, 0.0,
                                                             px_h / img.size[1]))
        if spec.get("camera"):
            cx, c_s = w / 2 - 13.0, s0 + h - 13.0
            part(" camera ring", M_DEVICE, lambda bm: add_cyl(bm, 6.0, (cx, c_s, n_back), (cx, c_s, n_back - 1.2)))
            part(" camera lens", M_LENS, lambda bm: add_cyl(bm, 4.6, (cx, c_s, n_back - 1.2), (cx, c_s, n_back - 1.3)))
        return parts
    if shot:
        print("WARNING: screen image not found, drawing the generic screen:", shot)
    part(" screen", M_SCREEN, lambda bm: add_rounded_prism(
        bm, dw, dh, min(4.0, bezel), n_front, n_front + 0.02, center=(0, cs)))
    if spec.get("camera"):
        cx, c_s = w / 2 - 13.0, s0 + h - 13.0
        part(" camera ring", M_DEVICE, lambda bm: add_cyl(bm, 6.0, (cx, c_s, n_back), (cx, c_s, n_back - 1.2)))
        part(" camera lens", M_LENS, lambda bm: add_cyl(bm, 4.6, (cx, c_s, n_back - 1.2), (cx, c_s, n_back - 1.3)))

    # generic amp-app screen, sized from the display so it works in landscape and portrait
    n_ui = n_front + 0.04
    u = min(dw, dh * 1.5)                               # layout unit
    top = cs + dh / 2
    dials = ("GAIN", "BASS", "MID", "TREBLE", "VOLUME") if dw > 120 else ("GAIN", "TONE", "VOL")
    xs = [(i - (len(dials) - 1) / 2) * dw / (len(dials) + 0.6) for i in range(len(dials))]
    dial_r = min(dw / (len(dials) + 0.6) * 0.30, dh * 0.11)
    dial_s = cs - dh * 0.20

    def panels(bm):
        add_box(bm, (dw - 0.06 * u, 0.09 * u, 0.02), (0, top - 0.085 * u, n_ui))               # top bar
        for x in xs:
            add_cyl(bm, dial_r, (x, dial_s, n_ui - 0.01), (x, dial_s, n_ui + 0.01))            # dials

    def accents(bm):
        add_box(bm, (0.36 * u, 0.006 * u, 0.02), (0, cs + dh * 0.10, n_ui))                    # rule under the name
        for x, a in zip(xs, (-0.9, 0.5, 0.0, 0.8, -0.3)):                                      # dial pointers
            add_cyl(bm, dial_r * 0.13, (x + dial_r * 0.6 * math.sin(a), dial_s + dial_r * 0.6 * math.cos(a), n_ui),
                    (x + dial_r * 0.6 * math.sin(a), dial_s + dial_r * 0.6 * math.cos(a), n_ui + 0.04), 16)

    part(" app panels", M_UI_DIM, panels)
    part(" app accents", M_UI_ACCENT, accents)
    texts = [screen_text("BANK 03   PRESET A", 0, top - 0.085 * u, n_ui + 0.03, 0.036 * u, M_UI_TEXT),
             screen_text("Clean Chime", 0, cs + dh * 0.21, n_ui, 0.105 * u, M_UI_TEXT)]
    for x, d in zip(xs, dials):
        texts.append(screen_text(d, x, dial_s - dial_r - 0.035 * u, n_ui, 0.028 * u, M_UI_TEXT))
    return parts + texts


DEVICES = {key: example_device(key, spec) for key, spec in HD["example_devices"].items() if not key.startswith("_")}


def show_device(name):
    """Fit one example device (or none) and move the side arms to it."""
    for key, parts in DEVICES.items():
        for ob in parts:
            ob.hide_render = ob.hide_viewport = key != name
    if name:
        set_jaws(HD["example_devices"][name]["size"][0])


def show_holder(visible):
    for ob in C_HOLDER.objects:
        ob.hide_render = not visible


show_device("tablet")

# ---------------------------------------------------------------- stage: floor, lights, camera
def floor_material():
    """Smooth light concrete: large patches of slightly different grey, fine speckle, a little bump."""
    m = material("Floor", (0.42, 0.41, 0.39), roughness=0.6, bevel=0)
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    big, fine = nt.nodes.new("ShaderNodeTexNoise"), nt.nodes.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value, big.inputs["Detail"].default_value = 6.0, 8.0
    fine.inputs["Scale"].default_value, fine.inputs["Detail"].default_value = 900.0, 3.0
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY_ADD"                       # big * 0.8 + fine * 0.2
    mix.inputs[1].default_value = 0.8
    scale = nt.nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = 0.2
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.3, (0.115, 0.11, 0.105, 1.0)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.75, (0.20, 0.195, 0.185, 1.0)
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs[3].default_value, rough.inputs[4].default_value = 0.45, 0.75
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.0004
    for nz in (big, fine):
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(fine.outputs[0], scale.inputs[0])
    nt.links.new(big.outputs[0], mix.inputs[0])
    nt.links.new(scale.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(big.outputs[0], rough.inputs[0])
    nt.links.new(rough.outputs[0], p.inputs["Roughness"])
    nt.links.new(fine.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


floor = simple("Floor", C_STAGE, floor_material(), lambda bm: add_box(bm, (6000, 6000, 1), (0, 0, -3.0)))

# Image-based light from the interior HDRI that ships with Blender, for natural reflections in the
# black and chrome parts. Falls back to a plain sky colour if the file is not there.
world = bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
HDRI = os.path.join(bpy.utils.system_resource("DATAFILES"), "studiolights", "world", "interior.exr")
if os.path.exists(HDRI):
    env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(HDRI)
    world.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.30
else:
    print("WARNING: bundled HDRI not found, using a plain world:", HDRI)
    bg.inputs["Color"].default_value = (0.75, 0.78, 0.82, 1.0)
    bg.inputs["Strength"].default_value = 0.4


def light(name, kind, loc, energy, size=0.3, color=(1.0, 1.0, 1.0)):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    ob.rotation_euler = (Vector((0, 0.02, 0.04)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    C_STAGE.objects.link(ob)
    return ob


# three softboxes: a large warm key above the player's left, a cool fill, and a rim from behind
light("Key", "AREA", (-0.45, -0.40, 0.70), 11.0, 0.7, (1.0, 0.96, 0.90))
light("Fill", "AREA", (0.60, -0.30, 0.40), 2.5, 0.8, (0.90, 0.95, 1.0))
light("Rim", "AREA", (0.25, 0.65, 0.55), 9.0, 0.6)

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 55
cam_data.clip_start = 0.01
cam_data.clip_end = 20
cam_data.dof.use_dof = True                              # slight lens blur away from the focus point
cam_data.dof.aperture_fstop = 22.0
cam = bpy.data.objects.new("Camera", cam_data)
C_STAGE.objects.link(cam)
scene.camera = cam


def aim(loc, target):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam_data.dof.focus_distance = (Vector(target) - Vector(loc)).length


# Path-traced renders on the CPU (works everywhere; a discrete GPU can be selected in the .blend).
scene.render.engine = "CYCLES"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.image_settings.file_format = "PNG"
scene.render.use_persistent_data = True
scene.cycles.device = "CPU"
scene.cycles.samples = int(os.environ.get("OPEN_PEDAL_SAMPLES", "192"))
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass

aim((-0.16, -0.36, 0.30), (0, -0.005, 0.02))
os.makedirs(os.path.join(HERE, "renders"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "open-pedal.blend"))


scene.render.use_stamp_filename = False  # keep the local .blend path out of the PNG metadata


VIEWS = [v for v in os.environ.get("OPEN_PEDAL_VIEWS", "").split(",") if v]   # limit the views, for quick checks


def render(name):
    if VIEWS and name.split(".")[0] not in VIEWS:
        return
    scene.render.filepath = os.path.join(HERE, "renders", name)
    bpy.ops.render.render(write_still=True)


# the holder with a tablet, from the front and the rear, then with a phone
aim((-0.27, -0.56, 0.42), (0, 0.035, 0.07))
render("holder-tablet.png")
aim((0.33, 0.52, 0.36), (0, 0.06, 0.07))
render("holder-rear.png")
show_device("phone")
aim((-0.27, -0.53, 0.45), (0, 0.04, 0.085))
render("holder-phone.png")
show_device("tablet")

# the bare unit, holder removed
show_holder(False)
for parts in DEVICES.values():
    for ob in parts:
        ob.hide_render = True
aim((-0.16, -0.36, 0.30), (0, -0.005, 0.02))
render("front.png")
aim((0.17, 0.36, 0.20), (0, 0.02, 0.02))
render("rear.png")
# internals: hide the body and labels, look straight in from above the front
shell.hide_render = True
for ob in C_LABELS.objects:
    ob.hide_render = True
aim((-0.05, -0.22, 0.42), (0, 0.005, 0.015))
render("inside.png")
shell.hide_render = False
for ob in C_LABELS.objects:
    ob.hide_render = False
print("enclosure model written")
