# Turns the studio's Revit model, exported through Navisworks as FBX, into the detailed web model
# used by the interactive building on the home page (interiors included).
#
#   blender -b --factory-startup --python tools/build-model-navis.py -- <in.fbx> <out.glb> <out.json>
#   blender -b --factory-startup --python tools/build-model-navis.py -- assets-src/amber/navis/amber.fbx public/models/house.glb src/data/house-model.json
#
# The Navisworks export keeps the real model tree, so nothing is guessed from names:
#   level  >  Revit category  >  family  >  type  >  instance  >  one mesh per material
# (the other top level nodes are saved viewpoints, lights and helpers and are dropped).
#
# What it does:
#   1. imports the FBX and walks that tree
#   2. drops what is not building: saved views, room volumes, level markers, model lines, planting
#      placeholders and anything named as demolition
#   3. joins the meshes of one instance into one pickable part, in metres, around the origin
#   4. keeps the material split inside a part, but as a small shared set of finish classes
#      (glass, oak, tile, metal ...) instead of the export's 1,883 materials
#   5. turns watertight pieces so their faces point out, mirrors included
#   6. thins only very dense pieces (a garage door, a shower door, a few fixtures)
#   7. tags every part: d discipline, c category, t family and type, l level, f floor group (0 to 3)
#      Names are scrubbed: no client, architect, address, person, file name or Revit id leaves here.
#   8. writes a Draco GLB and a JSON summary (the page reads its counts from that file)
import bpy, bmesh, sys, os, json, re, math, collections, statistics
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT_GLB, OUT_JSON = argv[0], argv[1], argv[2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)

# ---------------------------------------------------------------- the tree
def base(name):                                   # Blender's duplicate suffix
    return re.sub(r"\.\d{3}$", "", name)

def mesh_descendants(o):
    out, stack = [], [o]
    while stack:
        x = stack.pop()
        if x.type == "MESH":
            out.append(x)
        stack.extend(x.children)
    return out

# level node name fragment -> (visitor facing name, floor group)
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

# Revit category -> (discipline, visitor facing category)
CATEGORIES = {
    "Walls": ("architecture", "Walls"), "Doors": ("architecture", "Doors"), "Windows": ("architecture", "Windows"),
    "Roofs": ("architecture", "Roofs"), "Fascias": ("architecture", "Fascias"), "Floors": ("architecture", "Floors"),
    "Ceilings": ("architecture", "Ceilings"), "Stairs": ("architecture", "Stairs"),
    "Railings": ("architecture", "Railings"), "Handrails": ("architecture", "Railings"),
    "Top Rails": ("architecture", "Railings"), "Supports": ("architecture", "Railings"),
    "Curtain Panels": ("architecture", "Curtain walls"), "Curtain Wall Mullions": ("architecture", "Curtain walls"),
    "Toposolid": ("architecture", "Site"),
    "Structural Columns": ("structure", "Structural columns"), "Structural Framing": ("structure", "Structural framing"),
    "Casework": ("interiors", "Casework"), "Furniture": ("interiors", "Furniture"),
    "Specialty Equipment": ("interiors", "Specialty equipment"), "Generic Models": ("interiors", "Generic models"),
    "Plumbing Fixtures": ("plumbing", "Plumbing fixtures"), "Pipe Accessories": ("plumbing", "Pipe accessories"),
    "Electrical Equipment": ("electrical", "Electrical equipment"), "Electrical Fixtures": ("electrical", "Electrical fixtures"),
    "Mechanical Equipment": ("mechanical", "Mechanical equipment"), "Duct Accessories": ("mechanical", "Duct accessories"),
}
# not building: room volumes, level markers, sketch lines, empty placeholders
DROP = re.compile(r"^(rooms|levels|<room separation>|model lines|planting|pipes|pipe fittings|lines)$|demo", re.I)

# ---------------------------------------------------------------- privacy
# words that must never reach the website: client, architect, people, street, file names
SCRUB = re.compile(
    r"\b(yoon|leong|morgan|fergus[eo]n|gellert|gelle|jpa|amber|315|peders[eo]n|arnold|caroline|parkway|edward|martin|byron|"
    r"not a type|see type catalog|rfa|dxf|rvt|nwd|nwc|fbx)\b", re.I)
BANNED = re.compile(r"yoon|leong|morgan|fergus|gellert|jpa|amber|\b315\b|peders|arnold|caroline|parkway|edward martin|byron|\.rvt|\.dxf|element id|source file", re.I)
KEEP_UPPER = {"HSS", "TPO", "ACT", "RB", "THK", "IG", "CFM", "RPM", "LB", "SCW", "GM", "EW", "AV200", "MB"}
FIX = {"bifoolding": "Bifolding", "teppered": "tapered", "wout": "without", "amp": "and", "exst": "Existing", "shwr": "Shower"}
GENERIC_TYPE = re.compile(r"^(standard|parametric|generic|default|built in)?( ?\d{1,2})?$", re.I)

def clean(name):
    t = base(name)
    t = re.sub(r"\[\d+\]", "", t)                    # Revit element ids
    t = re.sub(r"_[0-9a-f]{7,8}\b", "", t)           # truncated hash suffixes
    t = re.sub(r"_\d{4,6}\b", "", t)                 # family library numbers
    t = re.sub(r"(\d)quot", r"\1 in", t)              # a leftover &quot;
    t = re.sub(r"\.\d+$", "", t)
    t = t.replace("&", " and ").replace("_", " ").replace("''", '"')
    t = re.sub(r"\((\d+)\)", "", t)
    t = SCRUB.sub(" ", t)
    t = re.sub(r"\.(?=[a-z])", " ", t, flags=re.I)
    t = re.sub(r"(?<![0-9])-|-(?![0-9])", " ", t)     # dashes between words
    t = t.replace("-", " ")                           # and the rest: no dashes in visible text
    t = re.sub(r"[^ -~]", "", t)
    t = re.sub(r"\(\s*\)", "", t)
    words = []
    for w in t.split():
        core = re.sub(r"[^A-Za-z]", "", w)
        if core.lower() in FIX:
            w = FIX[core.lower()]
        elif core and core == w and core not in KEEP_UPPER and len(core) > 2 and (core.isupper() or (core[0].islower() and core[1:].isupper())):
            w = core.capitalize()
        words.append(w)
    words = [w for i, w in enumerate(words) if i == 0 or w.lower() != words[i - 1].lower()]
    t = " ".join(words).strip(" -_.,'")
    t = re.sub(r"^and\s+", "", t)
    t = re.sub(r"(?<=[A-Za-z\"])\s+\d$", "", t)        # a trailing copy number
    return t

def type_label(family, typ):
    f, t = clean(family), clean(typ)
    f = re.sub(r"(?<=[a-z])\d$", "", f)               # "Timber1", "Facade Trim2"
    fw = f.lower().split()
    if not t or GENERIC_TYPE.match(t) or t.lower() == f.lower() or t.lower().startswith(f.lower()):
        out = t if t.lower().startswith(f.lower()) and len(t) > len(f) else f
    elif len(t.split()) >= 2 and all(w in fw for w in t.lower().split()[:2]):
        out = f                                       # the type only repeats the family
    elif not f:
        out = t
    else:
        out = f"{f}, {t}"
    out = re.sub(r"\s{2,}", " ", out).strip(" ,")
    if len(out) > 78:
        out = out[:78].rsplit(" ", 1)[0].strip(" ,")
    out = out or "Element"
    return out[0].upper() + out[1:]

# ---------------------------------------------------------------- finish classes
# One small shared material set. The website gives each class its real finish.
CLASSES = ["glass", "black", "metal", "brass", "white", "stucco", "siding", "oak", "woodfloor", "tile", "stone",
           "porcelain", "concrete", "roof", "fabric", "timber", "ground"]
CLASS_COLOR = {
    "glass": (0.55, 0.72, 0.80), "black": (0.03, 0.03, 0.035), "metal": (0.62, 0.64, 0.66), "brass": (0.72, 0.55, 0.30),
    "white": (0.90, 0.90, 0.88), "stucco": (0.86, 0.86, 0.84), "siding": (0.10, 0.10, 0.11), "oak": (0.66, 0.52, 0.36),
    "woodfloor": (0.60, 0.46, 0.30), "tile": (0.72, 0.72, 0.70), "stone": (0.88, 0.88, 0.86), "porcelain": (0.94, 0.94, 0.93),
    "concrete": (0.50, 0.50, 0.50), "roof": (0.85, 0.85, 0.84), "fabric": (0.82, 0.79, 0.73), "timber": (0.74, 0.60, 0.40),
    "ground": (0.42, 0.42, 0.42),
}
# export material name fragments, first match wins
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
            # a cabinet front in a kitchen is oak here, a "wood" door leaf is painted
            return cls
    return by_category(cat, text)

# ---------------------------------------------------------------- collect parts from the tree
Part = collections.namedtuple("Part", "level floor disc cat label text sources")
parts, skipped = [], collections.Counter()
roots = [o for o in bpy.context.scene.objects if o.parent is None]
level_nodes = [r for r in roots if r.type == "EMPTY" and mesh_descendants(r)]
for lv in level_nodes:
    lvl = level_of(lv.name)                                    # None for "<No level>": placed by height below
    for cat_node in lv.children:
        rc = base(cat_node.name)
        if DROP.search(rc) or rc not in CATEGORIES:
            skipped[rc] += len(mesh_descendants(cat_node))
            continue
        disc, cat = CATEGORIES[rc]
        for fam in cat_node.children:
            if DROP.search(base(fam.name)):
                continue
            if fam.type == "MESH":
                skipped[rc + " (loose)"] += 1
                continue
            for typ in fam.children:
                label = type_label(fam.name, typ.name)
                text = f"{base(fam.name)} {base(typ.name)}"
                instances = [typ] if typ.type == "MESH" else list(typ.children)
                for inst in instances:
                    src = mesh_descendants(inst)
                    if src:
                        parts.append(Part(lvl[0] if lvl else None, lvl[1] if lvl else None, disc, cat, label, text, src))
print("TREE levels", len(level_nodes), "parts", len(parts), "skipped", dict(skipped))

# ---------------------------------------------------------------- thin only the very dense pieces
def tri_count(me):
    me.calc_loop_triangles()
    return len(me.loop_triangles)

thinned = 0
seen_data = {}
for p in parts:
    for o in p.sources:
        me = o.data
        if me.name in seen_data:
            o.data = seen_data[me.name]
            continue
        t = tri_count(me)
        cap = t if t <= 12000 else (12000 + (t - 12000) * 0.4 if t <= 40000 else 30000)
        if cap < t:
            o.data = me.copy()
            m = o.modifiers.new("thin", "DECIMATE")
            m.ratio = cap / t
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier="thin")
            thinned += 1
        seen_data[me.name] = o.data
print("THINNED", thinned)

# ---------------------------------------------------------------- size, origin, level heights
bpy.context.view_layer.update()
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for p in parts:
    for o in p.sources:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
origin = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))

def z_range(sources):
    zs = [(o.matrix_world @ Vector(c)).z for o in sources for c in o.bound_box]
    return min(zs), max(zs)

# a level's height is where its doors stand (floors and walls are less reliable: they have offsets)
door_z = collections.defaultdict(list); any_z = collections.defaultdict(list)
for p in parts:
    if p.level:
        any_z[p.level].append(z_range(p.sources)[0])
        if p.cat == "Doors":
            door_z[p.level].append(z_range(p.sources)[0])
elev = {}
for name in any_z:
    elev[name] = statistics.median(door_z[name]) if door_z.get(name) else min(any_z[name])
floor_of = {label: floor for _, label, floor in LEVELS}
def place(sources, cat):                                       # parts Revit holds on no level
    lo = z_range(sources)[0]
    names = [n for n in elev if n != "Roof" or cat in ("Fascias", "Roofs")]
    under = [n for n in names if elev[n] <= lo + 0.2]
    name = max(under, key=lambda n: elev[n]) if under else min(names, key=lambda n: elev[n])
    return name, floor_of[name]

# ---------------------------------------------------------------- build one mesh per part
mats = {}
for cls in CLASSES:
    m = bpy.data.materials.new(cls)
    m.diffuse_color = (*CLASS_COLOR[cls], 1.0)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*CLASS_COLOR[cls], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    mats[cls] = m

col = bpy.data.collections.new("house")
bpy.context.scene.collection.children.link(col)
closed = turned = pieces = 0
built = []
summary = collections.OrderedDict()
types = collections.defaultdict(collections.Counter)
level_count = collections.Counter(); class_tris = collections.Counter()
total_tris = 0

for i, p in enumerate(parts):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in p.sources:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    centre = (lo + hi) / 2
    used = []                                                  # finish classes in this part, in slot order
    bm = bmesh.new()
    for o in p.sources:
        me = o.data
        mat_name = me.materials[0].name if me.materials and me.materials[0] else o.name
        cls = finish_class(mat_name, p.cat, p.text)
        if cls not in used:
            used.append(cls)
        piece = bmesh.new(); piece.from_mesh(me)
        pieces += 1
        # the export splits vertices at sharp edges: weld, then a watertight piece can be turned face out
        bmesh.ops.remove_doubles(piece, verts=piece.verts, dist=1e-4)
        if len(piece.faces) > 3 and all(len(e.link_faces) == 2 for e in piece.edges):
            before = [f.normal.copy() for f in piece.faces]
            bmesh.ops.recalc_face_normals(piece, faces=piece.faces)
            turned += sum(1 for f, b in zip(piece.faces, before) if f.normal.dot(b) < 0)
            closed += 1
            mirrored = False                                   # already facing out, whatever the mirror did
        else:
            mirrored = o.matrix_world.determinant() < 0
        bmesh.ops.transform(piece, matrix=Matrix.Translation(-centre) @ o.matrix_world, verts=piece.verts)
        if mirrored or (o.matrix_world.determinant() < 0 and not mirrored):
            # a mirrored instance turns every face inside out once it is baked into place
            bmesh.ops.reverse_faces(piece, faces=piece.faces)
        slot = used.index(cls)
        for f in piece.faces:
            f.material_index = slot
            f.smooth = True
        tmp = bpy.data.meshes.new("tmp")
        piece.to_mesh(tmp); piece.free()
        bm.from_mesh(tmp)
        # from_mesh keeps the source's slot numbers, so set them again on the faces just added
        bm.faces.ensure_lookup_table()
        for f in bm.faces[len(bm.faces) - len(tmp.polygons):]:
            f.material_index = slot
        bpy.data.meshes.remove(tmp)
    name = f"e{i:04d}"
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for cls in used:
        me.materials.append(mats[cls])
    me.set_sharp_from_angle(angle=math.radians(38))
    ob = bpy.data.objects.new(name, me)
    ob.location = centre - origin
    col.objects.link(ob)
    level, floor = (p.level, p.floor) if p.level else place(p.sources, p.cat)
    if p.cat in ("Roofs", "Fascias") and level == "Roof":
        floor = 3
    ob["d"] = p.disc; ob["c"] = p.cat; ob["t"] = p.label; ob["l"] = level; ob["f"] = floor
    t = tri_count(me)
    total_tris += t
    for poly in me.polygons:
        class_tris[used[poly.material_index]] += max(len(poly.vertices) - 2, 1)
    s = summary.setdefault(p.disc, {"elements": 0, "tris": 0, "categories": collections.Counter()})
    s["elements"] += 1; s["tris"] += t; s["categories"][p.cat] += 1
    types[p.cat][p.label] += 1
    level_count[level] += 1
    built.append(ob)
print("ORIENT watertight pieces", closed, "of", pieces, "faces turned", turned)

# everything that came from the export goes: only the clean parts are written
for o in [o for o in bpy.context.scene.objects if o.name not in col.objects]:
    bpy.data.objects.remove(o, do_unlink=True)

# level heights for the website (metres above the lowest point of the model)
order = ["Ground floor", "Second floor", "Mezzanine", "Third floor", "Roof"]
levels = [{"n": n, "f": floor_of[n], "e": round(elev[n] - mn.z, 2), "parts": level_count[n]} for n in order if n in elev]
bpy.context.scene["levels"] = json.dumps([[l["n"], l["f"], l["e"]] for l in levels])
bpy.context.scene.name = "house"

bpy.ops.object.select_all(action="DESELECT")
for o in built:
    o.select_set(True)
bpy.context.view_layer.objects.active = built[0]
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB, export_format="GLB", use_selection=True,
    export_extras=True, export_apply=False, export_yup=True,
    export_materials="EXPORT", export_texcoords=False, export_normals=True,
    export_vertex_color="NONE", export_image_format="NONE",
    export_cameras=False, export_lights=False, export_animations=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
    export_draco_position_quantization=13, export_draco_normal_quantization=8,
)

report = {
    "elements": len(built), "triangles": total_tris,
    "size": [round(v, 2) for v in (mx - mn)],
    "bytes": os.path.getsize(OUT_GLB),
    "levels": levels,
    "disciplines": {k: {"elements": v["elements"], "triangles": v["tris"], "categories": dict(v["categories"])} for k, v in summary.items()},
    "finishes": dict(class_tris.most_common()),
    "types": {c: dict(t.most_common()) for c, t in sorted(types.items())},
}
text = json.dumps(report, indent=1)
with open(OUT_JSON, "w", encoding="utf8") as f:
    f.write(text)

# ---------------------------------------------------------------- privacy check on what was written
with open(OUT_GLB, "rb") as f:
    f.seek(12)
    n = int.from_bytes(f.read(4), "little"); f.read(4)
    glb_json = f.read(n).decode("utf8", "replace")
def strings(x):                                              # every name and value that is text, not numbers
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
words = "\n".join(strings(json.loads(glb_json))) + "\n" + "\n".join(strings(report))
hits = sorted(set(m.group(0).lower() for m in BANNED.finditer(words)))
print("PRIVACY", "FAIL " + str(hits) if hits else "OK")
print("MODEL_OK", len(built), "parts", total_tris, "tris", round(report["bytes"] / 1e6, 2), "MB")
