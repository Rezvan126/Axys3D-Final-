# Builds the interior scene for the virtual tour from the studio's Revit model (Navisworks FBX).
#
#   blender -b --factory-startup -P tools/tour-scene.py -- assets-src/amber/navis/amber.fbx assets-src/amber/tour.blend
#
# What it does:
#   1. imports the FBX and walks the real model tree (level > category > family > type > instance > mesh),
#      with the same drop list, the same name scrubbing and the same 17 finish classes as build-model-navis.py
#   2. bakes every mesh into place around the origin, in metres, and gives it a generic name
#      (no client, architect, address or person text is kept in the saved file)
#   3. one physically based material per finish class: painted plaster, white oak boards and joinery,
#      tile, stone, porcelain, stainless, black metal, real glass, fabric
#   4. light like an interior shoot: sky, a low warm sun through the street glazing, and small warm
#      ceiling lights in every room so the deep plan is never a black cave
#   5. a ground plane, a paved strip at the street and a far hedge line so windows do not look into a void
#   6. saves the .blend. tools/tour-render.py renders the panoramas from it.
#
# Environment switches for look development (defaults are the approved values):
#   TOUR_SUN_AZ, TOUR_SUN_EL, TOUR_SKY, TOUR_LAMP_W, TOUR_EXPOSURE
import bpy, bmesh, sys, os, re, math, json, collections, statistics
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
ENV = lambda k, d: float(os.environ.get(k, d))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
s = bpy.context.scene
D = bpy.data

# ---------------------------------------------------------------- the tree (as in build-model-navis.py)
def base(name):
    return re.sub(r"\.\d{3}$", "", name)

def mesh_descendants(o):
    out, stack = [], [o]
    while stack:
        x = stack.pop()
        if x.type == "MESH":
            out.append(x)
        stack.extend(x.children)
    return out

LEVELS = [
    ("SIDEWALK", "Ground floor", 0), ("GROUND", "Ground floor", 0),
    ("SECOND", "Second floor", 1), ("MEZZ", "Mezzanine", 1),
    ("THIRD", "Third floor", 2), ("ROOF", "Roof", 3),
]
def level_of(name):
    n = name.upper()
    for key, label, floor in LEVELS:
        if key in n:
            return label, floor
    return None

CATEGORIES = {
    "Walls": "Walls", "Doors": "Doors", "Windows": "Windows", "Roofs": "Roofs", "Fascias": "Fascias", "Floors": "Floors",
    "Ceilings": "Ceilings", "Stairs": "Stairs", "Railings": "Railings", "Handrails": "Railings", "Top Rails": "Railings",
    "Supports": "Railings", "Curtain Panels": "Curtain walls", "Curtain Wall Mullions": "Curtain walls", "Toposolid": "Site",
    "Structural Columns": "Structural columns", "Structural Framing": "Structural framing",
    "Casework": "Casework", "Furniture": "Furniture", "Specialty Equipment": "Specialty equipment",
    "Generic Models": "Generic models", "Plumbing Fixtures": "Plumbing fixtures", "Pipe Accessories": "Pipe accessories",
    "Electrical Equipment": "Electrical equipment", "Electrical Fixtures": "Electrical fixtures",
    "Mechanical Equipment": "Mechanical equipment", "Duct Accessories": "Duct accessories",
}
DROP = re.compile(r"^(rooms|levels|<room separation>|model lines|planting|pipes|pipe fittings|lines)$|demo", re.I)

SCRUB = re.compile(
    r"\b(yoon|leong|morgan|fergus[eo]n|gellert|gelle|jpa|amber|315|peders[eo]n|arnold|caroline|parkway|edward|martin|byron|"
    r"not a type|see type catalog|rfa|dxf|rvt|nwd|nwc|fbx)\b", re.I)
BANNED = re.compile(r"yoon|leong|morgan|fergus|gellert|jpa|amber|\b315\b|peders|arnold|caroline|parkway|edward martin|byron|\.rvt|\.dxf|element id|source file", re.I)

def clean(name):
    t = base(name)
    t = re.sub(r"\[\d+\]", "", t)
    t = re.sub(r"_[0-9a-f]{7,8}\b", "", t)
    t = re.sub(r"_\d{4,6}\b", "", t)
    t = t.replace("&", " and ").replace("_", " ").replace("-", " ")
    t = SCRUB.sub(" ", t)
    t = re.sub(r"[^ -~]", "", t)
    return re.sub(r"\s{2,}", " ", t).strip(" .,'")[:60]

# ---------------------------------------------------------------- finish classes (as in build-model-navis.py)
CLASSES = ["glass", "black", "metal", "brass", "white", "stucco", "siding", "oak", "woodfloor", "tile", "stone",
           "porcelain", "concrete", "roof", "fabric", "timber", "ground"]
BY_MATERIAL = [
    ("black", ["glass - control", "glass - door panel", "glass - front panel", "black", "ebony", "dark", "rubber", "epdm",
               "anthracite", "zink", "bronze, light", "marvin-bronze", "ultralox-bronze"]),
    ("glass", ["glass", "verre", "szk"]),
    ("brass", ["brass", "champagne", "titanium"]),
    ("tile", ["porcelain tile", "tile", "travertine"]),
    ("woodfloor", ["flooring", "aspen oak"]),
    ("white", ["painted white", "paint finish", "painted wood", "white cabinet", "gypsum", "gyp bd", "acoustic", "plastic",
               "door - panel", "clad - white", "nylon"]),
    ("porcelain", ["porcelain", "china", "ceramic", "cast iron", "cotton", "marble", "glossy colors"]),
    ("stone", ["stone"]),
    ("fabric", ["linen, white", "fabric"]),
    ("oak", ["oak", "cabinet", "birch", "cherry", "laminate", "sash", "trim", "wood - "]),
    ("timber", ["lumber", "beam", "joist", "rafter"]),
    ("concrete", ["concrete", "masonry"]),
    ("roof", ["tpo", "roofing"]),
    ("siding", ["siding", "clapboard", "cladding"]),
    ("stucco", ["stucco", "plaster"]),
    ("metal", ["chrome", "stainless", "steel", "alumin", "nickel", "silver", "metal", "m_al", "m_st", "door - frame"]),
]

def by_category(cat, text):
    t = text.lower()
    if cat == "Walls":
        if "tile" in t or "travertine" in t: return "tile"
        if "glass" in t: return "glass"
        if "nickel" in t: return "metal"
        if "siding" in t: return "siding"
        if "stucco" in t or "exterior" in t: return "stucco"
        if "concrete" in t: return "concrete"
        return "white"
    if cat == "Floors":
        if "tile" in t: return "tile"
        if "concrete" in t: return "concrete"
        return "woodfloor"
    if cat == "Stairs": return "concrete" if "cast" in t or "monolithic" in t else "woodfloor"
    if cat in ("Roofs",): return "oak" if "canopy" in t else "roof"
    if cat in ("Ceilings", "Doors", "Electrical equipment", "Mechanical equipment", "Duct accessories"): return "white"
    if cat in ("Windows", "Railings", "Fascias"): return "black"
    if cat == "Curtain walls": return "glass" if "glazed" in t or "panel" in t else "black"
    if cat == "Casework": return "stone" if "counter" in t else "oak"
    if cat == "Generic models": return "porcelain" if "shower" in t or "pan" in t.split() else "oak"
    if cat == "Furniture": return "fabric" if "bed" in t else "oak"
    if cat == "Plumbing fixtures": return "metal" if re.search(r"faucet|tap|trim|shower|mixer|scupper|drain", t) else "porcelain"
    if cat in ("Specialty equipment", "Electrical fixtures", "Pipe accessories", "Structural columns"):
        return "timber" if "timber" in t else "metal"
    if cat == "Structural framing": return "metal" if "bar" in t or "hss" in t else "timber"
    if cat == "Site": return "ground"
    return "white"

def finish_class(mat_name, cat, text):
    m = base(mat_name).lower()
    for cls, keys in BY_MATERIAL:
        if any(k in m for k in keys):
            return cls
    return by_category(cat, text)

# ---------------------------------------------------------------- collect
Item = collections.namedtuple("Item", "level floor cat label text obj")
items, skipped = [], collections.Counter()
rooms_raw = []
roots = [o for o in s.objects if o.parent is None]
for lv in [r for r in roots if r.type == "EMPTY" and mesh_descendants(r)]:
    lvl = level_of(lv.name)
    for cat_node in lv.children:
        rc = base(cat_node.name)
        if rc == "Rooms":                                       # room volumes: not rendered, but they say where the rooms are
            for m in mesh_descendants(cat_node):
                chain, x = [], m
                while x and x != cat_node:
                    chain.append(clean(x.name)); x = x.parent
                rooms_raw.append((" / ".join(dict.fromkeys(reversed(chain))), lvl[0] if lvl else "", m))
        if DROP.search(rc) or rc not in CATEGORIES:
            skipped[rc] += len(mesh_descendants(cat_node))
            continue
        cat = CATEGORIES[rc]
        for fam in cat_node.children:
            if DROP.search(base(fam.name)) or fam.type == "MESH":
                continue
            for typ in fam.children:
                text = f"{base(fam.name)} {base(typ.name)}"
                label = clean(text)
                for o in mesh_descendants(typ):
                    items.append(Item(lvl[0] if lvl else "", lvl[1] if lvl else -1, cat, label, text, o))
print("TOUR tree: meshes", len(items), "skipped", dict(skipped))

bpy.context.view_layer.update()
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for it in items:
    for c in it.obj.bound_box:
        w = it.obj.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
origin = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
SIZE = mx - mn
print("TOUR size", [round(v, 2) for v in SIZE])
rooms = []
for name, lvl_name, m in rooms_raw:
    pts = [m.matrix_world @ Vector(c) - origin for c in m.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    rooms.append({"n": name, "l": lvl_name, "lo": [round(v, 2) for v in lo], "hi": [round(v, 2) for v in hi]})
s["rooms"] = json.dumps(rooms)

# ---------------------------------------------------------------- materials
def node(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n

def link(nt, a, b):
    nt.links.new(a, b)

def fresh(name):
    m = D.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt, node(nt, "ShaderNodeOutputMaterial")

def wpos(nt, scale=(1, 1, 1), rot=(0, 0, 0)):
    g = node(nt, "ShaderNodeNewGeometry")
    m = node(nt, "ShaderNodeMapping")
    m.inputs["Scale"].default_value = scale
    m.inputs["Rotation"].default_value = rot
    link(nt, g.outputs["Position"], m.inputs["Vector"])
    return m.outputs["Vector"]

def planar(nt, scale=1.0):
    """World position folded to a 2D pattern coordinate by the face direction: floors use x,y; walls use the wall's run and z."""
    g = node(nt, "ShaderNodeNewGeometry")
    sp = node(nt, "ShaderNodeSeparateXYZ"); link(nt, g.outputs["Position"], sp.inputs[0])
    sn = node(nt, "ShaderNodeSeparateXYZ"); link(nt, g.outputs["True Normal"], sn.inputs[0])
    ax = node(nt, "ShaderNodeMath", operation="ABSOLUTE"); link(nt, sn.outputs["X"], ax.inputs[0])
    ay = node(nt, "ShaderNodeMath", operation="ABSOLUTE"); link(nt, sn.outputs["Y"], ay.inputs[0])
    az = node(nt, "ShaderNodeMath", operation="ABSOLUTE"); link(nt, sn.outputs["Z"], az.inputs[0])
    is_floor = node(nt, "ShaderNodeMath", operation="GREATER_THAN"); link(nt, az.outputs[0], is_floor.inputs[0]); is_floor.inputs[1].default_value = 0.6
    x_wall = node(nt, "ShaderNodeMath", operation="GREATER_THAN"); link(nt, ax.outputs[0], x_wall.inputs[0]); link(nt, ay.outputs[0], x_wall.inputs[1])
    floor_v = node(nt, "ShaderNodeCombineXYZ"); link(nt, sp.outputs["X"], floor_v.inputs[0]); link(nt, sp.outputs["Y"], floor_v.inputs[1])
    wx = node(nt, "ShaderNodeCombineXYZ"); link(nt, sp.outputs["Y"], wx.inputs[0]); link(nt, sp.outputs["Z"], wx.inputs[1])
    wy = node(nt, "ShaderNodeCombineXYZ"); link(nt, sp.outputs["X"], wy.inputs[0]); link(nt, sp.outputs["Z"], wy.inputs[1])
    wall = node(nt, "ShaderNodeMix", data_type="VECTOR"); link(nt, x_wall.outputs[0], wall.inputs[0]); link(nt, wy.outputs[0], wall.inputs[4]); link(nt, wx.outputs[0], wall.inputs[5])
    out = node(nt, "ShaderNodeMix", data_type="VECTOR"); link(nt, is_floor.outputs[0], out.inputs[0]); link(nt, wall.outputs[1], out.inputs[4]); link(nt, floor_v.outputs[0], out.inputs[5])
    m = node(nt, "ShaderNodeMapping"); m.inputs["Scale"].default_value = (scale, scale, scale)
    link(nt, out.outputs[1], m.inputs["Vector"])
    return m.outputs["Vector"]

def noise(nt, vec, scale, detail=4.0, rough=0.55, distortion=0.0):
    n = node(nt, "ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    link(nt, vec, n.inputs["Vector"])
    return n.outputs[0]

def remap(nt, val, lo, hi, a=0.0, b=1.0):
    m = node(nt, "ShaderNodeMapRange")
    m.inputs["From Min"].default_value = lo; m.inputs["From Max"].default_value = hi
    m.inputs["To Min"].default_value = a; m.inputs["To Max"].default_value = b
    link(nt, val, m.inputs["Value"])
    return m.outputs["Result"]

def put(nt, sock, v):
    if hasattr(v, "is_linked"):
        link(nt, v, sock)
    elif isinstance(v, (int, float)):
        sock.default_value = v
    else:
        sock.default_value = (*v, 1.0) if len(v) == 3 else v

def mixc(nt, fac, a, b, mode="MIX"):
    m = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type=mode)
    put(nt, m.inputs[0], fac); put(nt, m.inputs[6], a); put(nt, m.inputs[7], b)
    return m.outputs[2]

def mth(nt, op, a, b=None):
    m = node(nt, "ShaderNodeMath", operation=op)
    put(nt, m.inputs[0], a)
    if b is not None:
        put(nt, m.inputs[1], b)
    return m.outputs[0]

def bump(nt, height, strength, distance=0.02, normal=None):
    b = node(nt, "ShaderNodeBump")
    b.inputs["Strength"].default_value = strength; b.inputs["Distance"].default_value = distance
    link(nt, height, b.inputs["Height"])
    if normal is not None:
        link(nt, normal, b.inputs["Normal"])
    return b.outputs["Normal"]

def principled(nt, out, base=None, rough=None, normal=None, **vals):
    p = node(nt, "ShaderNodeBsdfPrincipled")
    for name, v in (("Base Color", base), ("Roughness", rough), ("Normal", normal)):
        if v is not None:
            put(nt, p.inputs[name], v)
    for k, v in vals.items():
        p.inputs[k].default_value = v
    link(nt, p.outputs[0], out.inputs["Surface"])
    return p

def m_paint(name, tint=(0.80, 0.795, 0.78), r=(0.48, 0.68), grain=0.05):
    """Painted plaster or painted joinery: an even white, roughness that drifts a little, a very fine roller texture."""
    m, nt, out = fresh(name)
    pos = wpos(nt)
    wide = noise(nt, pos, 0.7, 3.0)
    fine = noise(nt, pos, 180.0, 3.0, 0.7)
    col = mixc(nt, remap(nt, wide, 0.3, 0.7, 0.0, 0.5), tint, tuple(c * 0.965 for c in tint))
    rough = remap(nt, noise(nt, pos, 2.3, 4.0), 0.25, 0.75, r[0], r[1])
    principled(nt, out, col, rough, bump(nt, fine, grain, 0.002))
    return m

def wood_tone(nt, t, dark, light):
    return mixc(nt, t, dark, light)

def m_boards(name, dark=(0.30, 0.19, 0.10), light=(0.56, 0.40, 0.24), width=0.19, length=1.9, rough=(0.30, 0.46)):
    """White oak boards. They run the long way through the house (y). Each board gets its own tone and grain."""
    m, nt, out = fresh(name)
    g = node(nt, "ShaderNodeNewGeometry")
    sp = node(nt, "ShaderNodeSeparateXYZ"); link(nt, g.outputs["Position"], sp.inputs[0])
    v = node(nt, "ShaderNodeCombineXYZ")                      # brick rows are boards: row direction = world y
    link(nt, sp.outputs["Y"], v.inputs[0]); link(nt, sp.outputs["X"], v.inputs[1])
    br = node(nt, "ShaderNodeTexBrick")
    br.offset = 0.37; br.offset_frequency = 1; br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.0012
    br.inputs["Mortar Smooth"].default_value = 0.0
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Brick Width"].default_value = length
    br.inputs["Row Height"].default_value = width
    br.inputs["Color1"].default_value = (0.0, 0.0, 0.0, 1); br.inputs["Color2"].default_value = (1, 1, 1, 1)
    br.inputs["Mortar"].default_value = (0.5, 0.5, 0.5, 1)
    link(nt, v.outputs[0], br.inputs["Vector"])
    # grain: noise stretched along the board, pushed sideways per board so boards do not line up
    shift = node(nt, "ShaderNodeVectorMath", operation="SCALE"); link(nt, br.outputs["Color"], shift.inputs[0]); shift.inputs[3].default_value = 37.0
    gv = node(nt, "ShaderNodeMapping"); gv.inputs["Scale"].default_value = (22.0, 0.55, 22.0)
    link(nt, g.outputs["Position"], gv.inputs["Vector"])
    add = node(nt, "ShaderNodeVectorMath", operation="ADD"); link(nt, gv.outputs[0], add.inputs[0]); link(nt, shift.outputs[0], add.inputs[1])
    grain = noise(nt, add.outputs[0], 1.0, 5.0, 0.6, 0.6)
    fine = noise(nt, add.outputs[0], 6.0, 3.0, 0.7)
    tone = mth(nt, "ADD", mth(nt, "MULTIPLY", br.outputs["Color"], 0.45), mth(nt, "MULTIPLY", grain, 0.55))
    col = wood_tone(nt, remap(nt, tone, 0.36, 0.66), dark, light)
    col = mixc(nt, mth(nt, "MULTIPLY", br.outputs["Fac"], 0.75), col, (0.05, 0.03, 0.02))        # the joint
    r = remap(nt, fine, 0.3, 0.7, rough[0], rough[1])
    h = mth(nt, "SUBTRACT", mth(nt, "MULTIPLY", grain, 0.25), br.outputs["Fac"])
    principled(nt, out, col, r, bump(nt, h, 0.25, 0.003))
    return m

def m_joinery(name, dark=(0.40, 0.27, 0.15), light=(0.62, 0.46, 0.29)):
    """Oak veneer on cabinets, doors and trim: vertical grain, satin lacquer."""
    m, nt, out = fresh(name)
    pos = wpos(nt, (26.0, 26.0, 0.7))
    grain = noise(nt, pos, 1.0, 5.0, 0.62, 0.5)
    wide = noise(nt, wpos(nt), 1.6, 2.0)
    tone = mth(nt, "ADD", mth(nt, "MULTIPLY", grain, 0.7), mth(nt, "MULTIPLY", wide, 0.3))
    col = wood_tone(nt, remap(nt, tone, 0.25, 0.75), dark, light)
    principled(nt, out, col, remap(nt, grain, 0.3, 0.7, 0.36, 0.52), bump(nt, grain, 0.12, 0.002))
    return m

def m_tile(name, size=0.6, tint=(0.62, 0.61, 0.585), joint=(0.30, 0.30, 0.29)):
    """Large format porcelain tile with a thin grey joint; works on floors and walls."""
    m, nt, out = fresh(name)
    uv = planar(nt)
    br = node(nt, "ShaderNodeTexBrick")
    br.offset = 0.0; br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.003
    br.inputs["Mortar Smooth"].default_value = 0.1
    br.inputs["Brick Width"].default_value = size * 2
    br.inputs["Row Height"].default_value = size
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (0, 0, 0, 1); br.inputs["Color2"].default_value = (1, 1, 1, 1)
    link(nt, uv, br.inputs["Vector"])
    cloud = noise(nt, wpos(nt), 2.4, 5.0, 0.6, 0.4)
    col = mixc(nt, remap(nt, cloud, 0.3, 0.7, 0.0, 0.35), tint, tuple(c * 0.86 for c in tint))
    col = mixc(nt, mth(nt, "MULTIPLY", br.outputs["Color"], 0.06), col, tuple(c * 0.9 for c in tint))
    col = mixc(nt, br.outputs["Fac"], col, joint)
    r = mixc(nt, br.outputs["Fac"], remap(nt, cloud, 0.3, 0.7, 0.16, 0.30), (0.8, 0.8, 0.8))
    h = mth(nt, "SUBTRACT", 1.0, br.outputs["Fac"])
    principled(nt, out, col, r, bump(nt, h, 0.4, 0.002))
    return m

def m_stone(name):
    """Pale quartz worktop with soft veining, honed."""
    m, nt, out = fresh(name)
    pos = wpos(nt)
    vein = noise(nt, pos, 1.3, 6.0, 0.6, 2.2)
    vein = remap(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", vein, 0.5)), 0.0, 0.05, 1.0, 0.0)
    cloud = noise(nt, pos, 4.0, 4.0)
    col = mixc(nt, remap(nt, cloud, 0.3, 0.7, 0.0, 0.3), (0.80, 0.79, 0.77), (0.72, 0.71, 0.69))
    col = mixc(nt, mth(nt, "MULTIPLY", vein, 0.35), col, (0.45, 0.44, 0.42))
    principled(nt, out, col, 0.22)
    return m

def m_simple(name, base, rough, metallic=0.0, grain=0.0, scale=60.0, **vals):
    m, nt, out = fresh(name)
    nrm = None
    r = rough
    if grain:
        n = noise(nt, wpos(nt), scale, 4.0, 0.6)
        nrm = bump(nt, n, grain, 0.003)
        r = remap(nt, n, 0.3, 0.7, rough * 0.85, min(1.0, rough * 1.15))
    principled(nt, out, base, r, nrm, Metallic=metallic, **vals)
    return m

def m_brushed(name, base=(0.62, 0.63, 0.64), rough=0.30):
    """Stainless: metal with a fine brushed streak."""
    m, nt, out = fresh(name)
    n = noise(nt, wpos(nt, (3.0, 3.0, 260.0)), 1.0, 2.0)
    p = principled(nt, out, base, remap(nt, n, 0.3, 0.7, rough - 0.06, rough + 0.08), Metallic=1.0)
    return m

def m_fabric(name, tint=(0.62, 0.60, 0.56)):
    m, nt, out = fresh(name)
    pos = wpos(nt)
    weave = node(nt, "ShaderNodeTexWave", wave_type="BANDS")
    weave.inputs["Scale"].default_value = 700.0
    link(nt, pos, weave.inputs["Vector"])
    cloud = noise(nt, pos, 9.0, 3.0)
    col = mixc(nt, remap(nt, cloud, 0.3, 0.7, 0.0, 0.25), tint, tuple(c * 0.9 for c in tint))
    p = principled(nt, out, col, 0.95, bump(nt, weave.outputs[0], 0.2, 0.001))
    p.inputs["Sheen Weight"].default_value = 0.4
    p.inputs["Sheen Roughness"].default_value = 0.5
    return m

def m_glass(name):
    """Real glazing: refracts and reflects for the camera, but lets sun and sky light straight through
    (shadow and diffuse rays see it as clear), which is what keeps the rooms lit without caustics."""
    m, nt, out = fresh(name)
    gl = node(nt, "ShaderNodeBsdfGlass")
    gl.inputs["IOR"].default_value = 1.45; gl.inputs["Roughness"].default_value = 0.0
    gl.inputs["Color"].default_value = (0.97, 0.99, 0.98, 1)
    tr = node(nt, "ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.94, 0.97, 0.96, 1)
    lp = node(nt, "ShaderNodeLightPath")
    either = mth(nt, "MAXIMUM", lp.outputs["Is Shadow Ray"], lp.outputs["Is Diffuse Ray"])
    mix = node(nt, "ShaderNodeMixShader")
    link(nt, either, mix.inputs[0]); link(nt, gl.outputs[0], mix.inputs[1]); link(nt, tr.outputs[0], mix.inputs[2])
    link(nt, mix.outputs[0], out.inputs["Surface"])
    return m

def m_ground(name):
    """Garden ground outside: lawn with mown variation, a paved band by the street front, soft from a distance."""
    m, nt, out = fresh(name)
    pos = wpos(nt)
    patch = noise(nt, pos, 0.35, 4.0, 0.6)
    blade = noise(nt, pos, 40.0, 3.0, 0.7)
    grass = mixc(nt, remap(nt, patch, 0.3, 0.7), (0.060, 0.105, 0.030), (0.115, 0.165, 0.050))
    grass = mixc(nt, remap(nt, blade, 0.3, 0.7, 0.0, 0.5), grass, (0.045, 0.080, 0.022))
    principled(nt, out, grass, 0.9, bump(nt, blade, 0.5, 0.02))
    return m

MATS = {
    "glass": m_glass("glass"),
    "black": m_simple("black", (0.012, 0.012, 0.013), 0.42, grain=0.03),
    "metal": m_simple("metal", (0.60, 0.61, 0.62), 0.30, metallic=1.0),
    "brass": m_simple("brass", (0.80, 0.60, 0.32), 0.28, metallic=1.0),
    "white": m_paint("white"),
    "ceiling": m_paint("ceiling", tint=(0.83, 0.83, 0.82), r=(0.7, 0.85), grain=0.03),
    "wall": m_paint("wall", tint=(0.80, 0.795, 0.775), r=(0.55, 0.75), grain=0.07),
    "stucco": m_simple("stucco", (0.74, 0.735, 0.72), 0.9, grain=0.35, scale=90.0),
    "siding": m_simple("siding", (0.022, 0.022, 0.024), 0.6, grain=0.1),
    "oak": m_joinery("oak"),
    "woodfloor": m_boards("woodfloor"),
    "tile": m_tile("tile", tint=(0.74, 0.73, 0.71), joint=(0.42, 0.42, 0.41)),
    "stone": m_stone("stone"),
    "porcelain": m_simple("porcelain", (0.84, 0.84, 0.83), 0.08, **{"Coat Weight": 0.5, "Coat Roughness": 0.03}),
    "concrete": m_simple("concrete", (0.36, 0.36, 0.355), 0.75, grain=0.3, scale=30.0),
    "roof": m_simple("roof", (0.62, 0.62, 0.61), 0.8, grain=0.15),
    "fabric": m_fabric("fabric", (0.36, 0.335, 0.30)),
    "timber": m_joinery("timber", dark=(0.45, 0.32, 0.18), light=(0.66, 0.50, 0.32)),
    "ground": m_simple("paving", (0.30, 0.295, 0.285), 0.85, grain=0.3, scale=25.0),
}

# ---------------------------------------------------------------- bake the meshes into place
col = D.collections.new("house")
s.collection.children.link(col)
shift = Matrix.Translation(-origin)
door_z = collections.defaultdict(list); any_z = collections.defaultdict(list)
count = collections.Counter()
for i, it in enumerate(items):
    o = it.obj
    src = o.data
    mat_name = src.materials[0].name if src.materials and src.materials[0] else ""
    cls = finish_class(mat_name, it.cat, it.text)
    key = cls
    if it.cat == "Plumbing fixtures" and cls in ("oak", "timber", "woodfloor") and re.search(r"toilet|bath|tub|lavatory|sink|BM 00|CST", it.text, re.I): key = "porcelain"   # a fixture is never timber
    if cls == "white" and it.cat == "Ceilings": key = "ceiling"
    elif cls == "white" and it.cat == "Walls": key = "wall"
    mw = shift @ o.matrix_world
    me = src.copy()
    me.transform(mw)
    if mw.determinant() < 0:
        me.flip_normals()
    me.name = f"m{i:04d}"
    me.materials.clear()
    me.materials.append(MATS[key])
    if it.cat in ("Roofs", "Floors"):
        # seen from the room below, the underside of a floor or roof build up is a painted ceiling
        me.materials.append(MATS["ceiling"])
        for poly in me.polygons:
            if poly.normal.z < -0.7:
                poly.material_index = 1
    ob = D.objects.new(f"e{i:04d}", me)
    col.objects.link(ob)
    ob["c"] = it.cat; ob["t"] = it.label; ob["l"] = it.level; ob["k"] = key
    count[key] += 1
    if it.level:
        z = min(v.co.z for v in me.vertices) if me.vertices else 0
        any_z[it.level].append(z)
        if it.cat == "Doors":
            door_z[it.level].append(z)

for o in [o for o in s.objects if o.name not in col.objects]:
    D.objects.remove(o, do_unlink=True)
for coll in (D.meshes, D.materials, D.images, D.cameras, D.lights):
    for b in [b for b in coll if b.users == 0]:
        coll.remove(b)
print("TOUR finishes", dict(count.most_common()))

# The export carries a few opening sized pieces of wall that sit exactly where a door or window is
# (infill from another phase). They would blank the glazing, so they are left out of the render.
def box_of(o):
    bb = [Vector(c) for c in o.bound_box]
    return Vector((min(b.x for b in bb), min(b.y for b in bb), min(b.z for b in bb))), Vector((max(b.x for b in bb), max(b.y for b in bb), max(b.z for b in bb)))
openings = [box_of(o) for o in col.objects if o["c"] in ("Doors", "Windows")]
plugs = 0
for o in [o for o in col.objects if o["c"] == "Walls"]:
    lo, hi = box_of(o)
    run = max(hi.x - lo.x, hi.y - lo.y)
    for olo, ohi in openings:
        c = (olo + ohi) / 2
        orun = max(ohi.x - olo.x, ohi.y - olo.y)
        if orun < 0.5 or (ohi.z - olo.z) < 0.8:
            continue
        inside = all(lo[i] - 0.03 <= c[i] <= hi[i] + 0.03 for i in range(3))
        if inside and run <= orun + 0.5 and (hi.z - lo.z) <= (ohi.z - olo.z) + 0.45:
            D.objects.remove(o, do_unlink=True)
            plugs += 1
            break
print("TOUR opening plugs removed", plugs)

elev = {n: (statistics.median(door_z[n]) if door_z.get(n) else min(any_z[n])) for n in any_z}
s["levels"] = json.dumps({k: round(v, 3) for k, v in elev.items()})
s["size"] = json.dumps([round(v, 3) for v in SIZE])
print("TOUR levels", s["levels"])

# ---------------------------------------------------------------- where is the street front
# the curtain wall glazing sits at one end of the long axis (y)
bpy.context.view_layer.update()
gy = [sum((Vector(c) for c in o.bound_box), Vector()).y / 8 for o in col.objects if o["c"] == "Curtain walls"]
FRONT = 1 if (statistics.mean(gy) if gy else 1) > 0 else -1
s["front"] = FRONT
print("TOUR street front at y", "+" if FRONT > 0 else "-", "curtain wall pieces", len(gy))

# ---------------------------------------------------------------- outside: ground, paving, hedge line
set_col = D.collections.new("set")
s.collection.children.link(set_col)
def plane(name, cx, cy, z, sx, sy, mat):
    me = D.meshes.new(name)
    me.from_pydata([(cx - sx, cy - sy, z), (cx + sx, cy - sy, z), (cx + sx, cy + sy, z), (cx - sx, cy + sy, z)], [], [(0, 1, 2, 3)])
    me.materials.append(mat)
    ob = D.objects.new(name, me); set_col.objects.link(ob)
    return ob

def box(name, cx, cy, z0, sx, sy, h, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx * 2, sy * 2, h), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(cx, cy, z0 + h / 2), verts=bm.verts)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = D.objects.new(name, me); set_col.objects.link(ob)
    return ob

# The lot climbs from the street to the back garden, so the set is two levels of lawn that stop at the
# model's own site, a paved street in front and a hedge line at each end to close the horizon.
half = SIZE.y / 2; side = SIZE.x / 2
low_z = (min(elev.values()) if elev else 0.0) - 0.12
site = [o for o in col.objects if o["c"] == "Site"]
back_z = max((max(v.co.z for v in o.data.vertices) for o in site), default=low_z) - 0.03
lawn = m_ground("lawn")
hedge = m_simple("hedge", (0.035, 0.07, 0.022), 0.95, grain=1.0, scale=6.0)
split = -FRONT * (half - 5.0)                              # where the back garden level starts
plane("street", 0, FRONT * (half + 8.0), low_z, 200, 8.0, MATS["ground"])
plane("lawn_front", 0, FRONT * (half + 116.0), low_z, 200, 100.0, lawn)
plane("lawn_back", 0, -FRONT * (half + 100.0), back_z, 200, 100.0, lawn)
for sx in (-1, 1):
    plane(f"lawn_side_low{sx}", sx * (side + 100.0), (split + FRONT * half) / 2, low_z, 100.0, abs(FRONT * half - split) / 2, lawn)
    plane(f"lawn_side_high{sx}", sx * (side + 100.0), (split - FRONT * half) / 2, back_z, 100.0, abs(-FRONT * half - split) / 2, lawn)
box("hedge_front", 0, FRONT * (half + 17.5), low_z, 120, 0.9, 2.8, hedge)
box("hedge_back", 0, -FRONT * (half + 2.2), back_z, 120, 0.9, 2.4, hedge)

# ---------------------------------------------------------------- staging
# The Revit model has the joinery, kitchen, fixtures and beds but no loose furniture. As a studio would for
# a tour, a few plain pieces are placed in the living room and the primary bedroom so the rooms read at
# scale: sofa, rug, low table, dining table and chairs, bedding, bedside tables. Simple shapes, soft edges.
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
stage = D.collections.new("staging")
s.collection.children.link(stage)
FAB_SOFA = m_fabric("sofa_fabric", (0.30, 0.285, 0.26))
FAB_RUG = m_fabric("rug", (0.50, 0.46, 0.40))
FAB_LINEN = m_fabric("linen", (0.74, 0.72, 0.68))
FAB_THROW = m_fabric("throw", (0.33, 0.37, 0.36))
FAB_CHAIR = m_fabric("chair_fabric", (0.42, 0.40, 0.36))

def floor_at(x, y, z):
    ok, loc, *_ = s.ray_cast(dg, Vector((x, y, z + 1.0)), Vector((0, 0, -1)), distance=2.5)
    return loc.z if ok else z

def soft(name, centre, size, mat, r=0.03, rot=0.0, tilt=0.0):
    """A box with rounded edges. centre is the middle of the box, rot turns it about z, tilt about its own x."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    r = min(r, min(size) * 0.45)
    if r > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=r, segments=4, profile=0.5, affect="EDGES")
    for f in bm.faces:
        f.smooth = True
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = D.objects.new(name, me)
    ob.location = centre
    ob.rotation_euler = (tilt, 0, rot)
    stage.objects.link(ob)
    ob["c"] = "Staging"; ob["k"] = mat.name; ob["t"] = name
    return ob

def turn(cx, cy, dx, dy, rot):
    c, sn = math.cos(rot), math.sin(rot)
    return cx + dx * c - dy * sn, cy + dx * sn + dy * c

def sofa(cx, cy, z, rot, w=2.3, d=0.95):
    P = lambda dx, dy, dz: (*turn(cx, cy, dx, dy, rot), z + dz)     # local: seat faces -y, back at +y
    soft("sofa_base", P(0, 0, 0.21), (w, d, 0.22), FAB_SOFA, 0.04, rot)
    soft("sofa_back", P(0, d / 2 - 0.11, 0.50), (w, 0.22, 0.56), FAB_SOFA, 0.06, rot)
    for sx in (-1, 1):
        soft("sofa_arm", P(sx * (w / 2 - 0.11), 0, 0.40), (0.22, d, 0.40), FAB_SOFA, 0.06, rot)
        soft("sofa_seat", P(sx * (w - 0.44) / 4, -0.08, 0.40), ((w - 0.46) / 2, d - 0.34, 0.17), FAB_SOFA, 0.06, rot)
        soft("sofa_cushion", P(sx * (w - 0.44) / 4, d / 2 - 0.30, 0.66), ((w - 0.5) / 2, 0.16, 0.40), FAB_SOFA, 0.07, rot, tilt=-0.16)
    soft("sofa_pillow", P(-w / 2 + 0.42, d / 2 - 0.44, 0.64), (0.42, 0.13, 0.40), FAB_THROW, 0.06, rot + 0.25, tilt=-0.3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            soft("sofa_leg", P(sx * (w / 2 - 0.1), sy * (d / 2 - 0.1), 0.05), (0.05, 0.05, 0.10), MATS["black"], 0.004, rot)

def table(cx, cy, z, rot, w, d, h, top=0.045, leg=0.06, mat=None, legmat=None, inset=0.08):
    mat = mat or MATS["oak"]; legmat = legmat or mat
    P = lambda dx, dy, dz: (*turn(cx, cy, dx, dy, rot), z + dz)
    soft("table_top", P(0, 0, h - top / 2), (w, d, top), mat, 0.008, rot)
    for sx in (-1, 1):
        for sy in (-1, 1):
            soft("table_leg", P(sx * (w / 2 - inset), sy * (d / 2 - inset), (h - top) / 2), (leg, leg, h - top), legmat, 0.006, rot)

def chair(cx, cy, z, rot):
    P = lambda dx, dy, dz: (*turn(cx, cy, dx, dy, rot), z + dz)     # local: sits facing -y
    soft("chair_seat", P(0, 0, 0.45), (0.46, 0.46, 0.06), FAB_CHAIR, 0.025, rot)
    soft("chair_back", P(0, 0.215, 0.70), (0.44, 0.04, 0.36), FAB_CHAIR, 0.018, rot, tilt=-0.1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            soft("chair_leg", P(sx * 0.19, sy * 0.19, 0.21), (0.03, 0.03, 0.42), MATS["black"], 0.004, rot)
        soft("chair_post", P(sx * 0.19, 0.215, 0.62), (0.03, 0.03, 0.42), MATS["black"], 0.004, rot, tilt=-0.1)

LIV = elev.get("Second floor", 5.34)
# living group, facing the fireplace wall: sofa with its back to the street glazing
zf = floor_at(3.2, 6.3, LIV)
soft("rug", (3.1, 6.35, zf + 0.008), (2.6, 3.3, 0.016), FAB_RUG, 0.006)
sofa(3.1, 7.45, zf + 0.016, 0.0)
table(3.1, 6.2, zf + 0.016, 0.0, 1.15, 0.6, 0.36, top=0.04, leg=0.035, legmat=MATS["black"])
# dining, on the kitchen side
zd = floor_at(-2.6, 5.5, LIV)
table(-2.6, 5.5, zd, 0.0, 2.2, 0.95, 0.75)
for i in (-1, 0, 1):
    chair(-2.6 + i * 0.68, 5.5 - 0.62, zd, math.pi)
    chair(-2.6 + i * 0.68, 5.5 + 0.62, zd, 0.0)

# bedding on the beds, bedside tables in the primary bedroom
beds = collections.defaultdict(list)
for o in col.objects:
    if o["c"] == "Furniture" and "bed" in o["t"].lower():
        bb = [Vector(c) for c in o.bound_box]
        cx = sum(b.x for b in bb) / 8; cy = sum(b.y for b in bb) / 8
        beds[(round(cx), round(cy))].append(bb)
for (bx_, by_), groups in beds.items():
    pts = [p for bb in groups for p in bb]
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    top = max(p.z for p in pts)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    head = 1 if cx > 0 else -1                                  # heads stand against the nearer party wall
    L, W = x1 - x0, y1 - y0
    soft("duvet", (cx - head * L * 0.16, cy, top + 0.05), (L * 0.68, W + 0.06, 0.11), FAB_LINEN, 0.05)
    soft("throw", (cx - head * L * 0.38, cy, top + 0.115), (L * 0.2, W + 0.08, 0.03), FAB_THROW, 0.014)
    n = 2 if W > 1.6 else 1
    for i in range(n):
        py = cy + (i - (n - 1) / 2) * (W / n)
        soft("pillow", (cx + head * (L / 2 - 0.26), py, top + 0.09), (0.40, min(0.72, W / n - 0.12), 0.15), FAB_LINEN, 0.07, tilt=0.0)
    if W > 1.6:
        zb = floor_at(cx, y0 - 0.3, top - 0.6)
        for sy, yy in ((-1, y0 - 0.30), (1, y1 + 0.30)):
            soft("bedside", (cx + head * (L / 2 - 0.22), yy, zb + 0.24), (0.42, 0.44, 0.48), MATS["oak"], 0.008)
        soft("bed_rug", (cx - head * 0.45, cy, zb + 0.007), (L + 0.3, W + 0.9, 0.014), m_fabric("bed_rug", (0.20, 0.19, 0.18)), 0.005)
        soft("headboard", (cx + head * (L / 2 + 0.03), cy, top + 0.32), (0.05, W + 1.5, 1.0), MATS["oak"], 0.008)

# a few things on the tables, and globe pendants over the dining table and the kitchen island
soft("book", (2.85, 6.2, zf + 0.016 + 0.375), (0.30, 0.22, 0.03), FAB_THROW, 0.004, 0.2)
soft("book", (2.87, 6.21, zf + 0.016 + 0.402), (0.26, 0.19, 0.024), FAB_SOFA, 0.004, -0.1)
soft("bowl", (-2.6, 5.5, zd + 0.78), (0.34, 0.34, 0.06), MATS["black"], 0.028)
GLOBE = D.materials.new("globe"); GLOBE.use_nodes = True
gnt = GLOBE.node_tree; gnt.nodes.clear()
gout = node(gnt, "ShaderNodeOutputMaterial"); gem = node(gnt, "ShaderNodeEmission")
gem.inputs["Color"].default_value = (1.0, 0.86, 0.68, 1); gem.inputs["Strength"].default_value = ENV("TOUR_GLOBE", "9")
link(gnt, gem.outputs[0], gout.inputs["Surface"])
def pendant(x, y, floor_z, drop_to, radius):
    ok, loc, *_ = s.ray_cast(dg, Vector((x, y, floor_z + 1.9)), Vector((0, 0, 1)), distance=6.0)
    if not ok:
        return
    top = loc.z; zc = floor_z + drop_to
    soft("pendant_cord", (x, y, (top + zc + radius) / 2), (0.008, 0.008, top - zc - radius), MATS["black"], 0.0)
    soft("pendant_cap", (x, y, zc + radius + 0.02), (0.05, 0.05, 0.05), MATS["brass"], 0.01)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=radius)
    for f in bm.faces:
        f.smooth = True
    me = D.meshes.new("pendant_globe"); bm.to_mesh(me); bm.free()
    me.materials.append(GLOBE)
    ob = D.objects.new("pendant_globe", me); ob.location = (x, y, zc)
    stage.objects.link(ob); ob["c"] = "Staging"; ob["k"] = "globe"; ob["t"] = "pendant"
for dx in (-0.55, 0.55):
    pendant(-2.6 + dx, 5.5, zd, 1.62, 0.13)
zk = floor_at(-1.65, 2.6, LIV)
for dx in (-0.8, 0.0, 0.8):
    pendant(-1.65 + dx, 2.6, zk, 1.78, 0.085)

# one plain abstract canvas on a blank wall in the entry and in the primary bedroom (staging, not the model)
def m_canvas(name, seed, tones):
    m, nt, out = fresh(name)
    pos = wpos(nt, (0.9, 0.9, 0.9), (0.4 + seed, 0.2, seed))
    n = noise(nt, pos, 1.1 + seed * 0.3, 2.0, 0.45, 1.6)
    ramp = node(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position = 0.0; els[0].color = (*tones[0], 1)
    els[1].position = 0.42; els[1].color = (*tones[1], 1)
    for p, col in ((0.52, tones[2]), (0.62, tones[3])):
        e = els.new(p); e.color = (*col, 1)
    link(nt, n, ramp.inputs[0])
    weave = noise(nt, wpos(nt), 420.0, 2.0, 0.6)
    principled(nt, out, ramp.outputs[0], 0.85, bump(nt, weave, 0.25, 0.001))
    return m

def canvas(name, start, direction, floor_z, w, h, mat, centre=1.5):
    d = Vector((direction[0], direction[1], 0)).normalized()
    ok, loc, nrm, *_ = s.ray_cast(dg, Vector((start[0], start[1], floor_z + centre)), d, distance=6.0)
    if not ok:
        return
    along_x = abs(d.y) > abs(d.x)                              # the wall runs along x when we look along y
    c = loc - d * 0.02
    size = (w, 0.03, h) if along_x else (0.03, w, h)
    frame = (w + 0.03, 0.022, h + 0.03) if along_x else (0.022, w + 0.03, h + 0.03)
    soft(name + "_frame", tuple(loc - d * 0.011), frame, MATS["black"], 0.002)
    soft(name, tuple(c), size, mat, 0.002)

canvas("canvas_entry", (1.55, 6.3), (-1, 0), floor_at(1.55, 6.3, elev.get("Ground floor", 2.07)), 0.9, 1.2,
       m_canvas("canvas_a", 0.0, [(0.62, 0.58, 0.50), (0.48, 0.20, 0.11), (0.13, 0.19, 0.24), (0.70, 0.66, 0.58)]))
canvas("canvas_bed", (2.1, -5.7), (-1, 0), floor_at(2.1, -5.7, elev.get("Third floor", 6.66)), 1.3, 0.95,
       m_canvas("canvas_b", 1.7, [(0.66, 0.62, 0.55), (0.16, 0.24, 0.26), (0.52, 0.30, 0.18), (0.72, 0.69, 0.62)]), centre=1.45)
print("TOUR staging pieces", len(stage.objects), "beds", len(beds))

# ---------------------------------------------------------------- world: sky and a low warm sun through the street glazing
SUN_AZ = math.radians(ENV("TOUR_SUN_AZ", "24"))       # off the facade normal, so the sun rakes across the floor
SUN_EL = math.radians(ENV("TOUR_SUN_EL", "24"))
SKY = ENV("TOUR_SKY", "0.55")
w = D.worlds.new("tour_sky"); w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
wout = node(nt, "ShaderNodeOutputWorld")
sky = node(nt, "ShaderNodeTexSky")
for kind in ("MULTIPLE_SCATTERING", "NISHITA"):
    try:
        sky.sky_type = kind
        break
    except Exception:
        continue
sky.sun_disc = True
sky.sun_size = math.radians(2.0)
sky.sun_intensity = 0.8
sky.sun_elevation = SUN_EL
# sky rotation is measured from +y towards +x; the sun stands in front of the street facade
sky.sun_rotation = (0.0 if FRONT > 0 else math.pi) + SUN_AZ
try:
    sky.air_density = 1.2; sky.aerosol_density = 1.6; sky.ozone_density = 1.3
except Exception:
    pass
bg = node(nt, "ShaderNodeBackground"); bg.inputs["Strength"].default_value = SKY
link(nt, sky.outputs[0], bg.inputs["Color"]); link(nt, bg.outputs[0], wout.inputs["Surface"])
s.world = w

# ---------------------------------------------------------------- ceiling lights
# Walk a grid through the plan. Wherever a floor has a ceiling over it, hang a small warm disc under the
# ceiling: it reads as a recessed downlight and lifts the rooms that the glazing cannot reach.
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
LAMP_W = ENV("TOUR_LAMP_W", "14")
lamp_col = D.collections.new("lamps")
s.collection.children.link(lamp_col)
ld = D.lights.new("downlight", "AREA")
ld.shape = "DISK"; ld.size = 0.11
ld.energy = LAMP_W
ld.color = (1.0, 0.90, 0.78)
try:
    ld.spread = math.radians(150)
except Exception:
    pass
STEP = 0.3
SPACING = ENV("TOUR_LAMP_GAP", "1.5")
lamps = 0
placed = []
def lamp_ok(p):
    """Not hard against a wall, and not crowding a lamp that is already up on the same ceiling."""
    for q in placed:
        if abs(q.z - p.z) < 0.6 and (q.xy - p.xy).length < SPACING:
            return False
    probe = p - Vector((0, 0, 0.12))
    for i in range(8):
        a = math.pi * i / 4
        ok, loc, *_ = s.ray_cast(dg, probe, Vector((math.sin(a), math.cos(a), 0)), distance=0.34)
        if ok:
            return False
    return True
nx = int(SIZE.x // STEP); ny = int(SIZE.y // STEP)
for ix in range(nx + 1):
    for iy in range(ny + 1):
        x = -nx * STEP / 2 + ix * STEP + 0.11
        y = -ny * STEP / 2 + iy * STEP + 0.07
        z = SIZE.z + 1.0
        hits = []
        for _ in range(60):
            ok, loc, nrm, idx, ob, _m = s.ray_cast(dg, Vector((x, y, z)), Vector((0, 0, -1)))
            if not ok:
                break
            hits.append((loc.z, nrm.z, ob.get("c", ""), ob.name))
            z = loc.z - 0.004
        for i, (hz, hn, hc, _n) in enumerate(hits):
            if hc != "Floors" or hn < 0.5:
                continue
            # the first roof, floor or ceiling above this floor
            above = [h for h in hits[:i] if h[2] in ("Ceilings", "Floors", "Roofs") and h[0] > hz + 0.3]
            if not above:
                continue
            cz = min(h[0] for h in above)
            if not 2.05 < cz - hz < 6.5:
                continue
            p = Vector((x, y, cz - 0.012))
            if not lamp_ok(p):
                continue
            placed.append(p)
            ob = D.objects.new(f"lamp{lamps:03d}", ld)
            ob.location = p
            lamp_col.objects.link(ob)
            lamps += 1
print("TOUR lamps", lamps)

# ---------------------------------------------------------------- render settings
s.render.engine = "CYCLES"
c = s.cycles
c.device = "GPU"
c.samples = 256
c.use_adaptive_sampling = True
c.adaptive_threshold = 0.02
c.use_denoising = True
try:
    c.denoiser = "OPTIX"
except Exception:
    pass
c.max_bounces = 10; c.diffuse_bounces = 5; c.glossy_bounces = 4; c.transmission_bounces = 8; c.transparent_max_bounces = 16
c.caustics_reflective = False; c.caustics_refractive = False
c.sample_clamp_indirect = 6.0
c.use_light_tree = True
s.render.use_stamp = False
vs = s.view_settings
try:
    vs.view_transform = "AgX"; vs.look = "AgX - Medium High Contrast"
except Exception:
    vs.view_transform = "Filmic"; vs.look = "Medium High Contrast"
vs.exposure = ENV("TOUR_EXPOSURE", "-0.45")
s.name = "tour"

# ---------------------------------------------------------------- privacy check, then save
names = [b.name for coll in (D.objects, D.meshes, D.materials, D.collections, D.worlds, D.lights) for b in coll]
names += [str(o.get("t", "")) for o in D.objects]
hits = sorted(set(m.group(0).lower() for m in BANNED.finditer("\n".join(names))))
print("PRIVACY", "FAIL " + str(hits) if hits else "OK")
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
print("TOUR_SCENE_OK", os.path.abspath(OUT), len(col.objects), "meshes", lamps, "lamps")
