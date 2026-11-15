# Turns the studio's own Revit export (FBX) into the small web model used by the
# interactive building on the home page.
#
#   blender -b --factory-startup --python tools/build-model.py -- <in.fbx> <out.glb> <out.json>
#
# What it does:
#   1. imports the FBX exactly as Revit exported it
#   2. gives every element a discipline, a category and a clean type name
#      (addresses, people's names and Revit ids are stripped: nothing that identifies
#      the client, the architect or the site goes to the website)
#   3. joins multi part families into one element and thins very dense fixtures
#      and paints the glass and frames of windows and glazed doors (see below)
#   4. writes a Draco compressed GLB plus a JSON summary of the real element counts
import bpy, sys, json, re, collections
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT_GLB, OUT_JSON = argv[0], argv[1], argv[2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)

# ---------------------------------------------------------------- classification
# (discipline, category, list of name fragments). First match wins.
RULES = [
    ("plumbing", "Plumbing fixtures", ["plumbing", "shower_columns", "shower pan", "water_closet", "hose_bibb", "floor drain", "sink", "lavatory", "faucet", "water heater", "tub"]),
    ("interiors", "Appliances", ["refrigerator", "dishwasher", "range ", "hood", "mirror"]),
    ("mechanical", "Heating and cooling", ["hvac", "air conditioning", "mini split", "condenser"]),
    ("structure", "Foundations", ["wall foundation", "footing", "stem wall", "foundation slab", "pad "]),
    ("structure", "Columns", ["concrete-round-column", "rectangular column", "column"]),
    ("structure", "Framing", ["joist", "beam", "carriage", "stringer", "rafter framing"]),
    ("structure", "Slabs", ["floor concrete"]),
    ("mechanical", "Ventilation", ["exhaust_fan", "wall_vent", "roof_vent", "o039hagin", "vent", "duct", "air terminal"]),
    ("electrical", "Lighting", ["downlight", "lighting", "lumin", "light", "sconce"]),
    ("electrical", "Power and switching", ["electrical", "outlet", "switch", "panelboard"]),
    ("interiors", "Casework", ["cabinet", "counter top", "countertop", "vanity", "casework", "shelf"]),
    ("interiors", "Finishes", ["tile", "glass shower wall", "wood trim", "trim-window-interior"]),
    ("architecture", "Roofs", ["basic roof", "roof", "fascia", "gutter", "downspout", "soffit"]),
    ("architecture", "Stairs and railings", ["stair", "railing", "handrail", "run ", "tread", "landing", "baluster", "top rail"]),
    ("architecture", "Windows", ["window", "casement", "fixed ", "skylight", "berica"]),
    ("architecture", "Doors", ["door", "single-flush", "sliding"]),
    ("architecture", "Ceilings", ["ceiling"]),
    ("architecture", "Floors", ["floor", "surface"]),
    ("architecture", "Walls", ["basic wall", "wall", "curtain", "trim"]),
]
FALLBACK = ("architecture", "Other elements")

# words that must never reach the website (people, client, site, model ids)
SCRUB = re.compile(r"\b(gellert|gelle|bryan|koo|muneeb|chalios|north side|garage|guest|bath 2|3d revit mod|see type catalog)\b", re.I)


def clean_type(name: str) -> str:
    t = re.sub(r"\[\d+\]", "", name)                 # Revit element ids
    t = re.sub(r"_[0-9a-f]{6,8}\b", "", t)            # truncated hash suffixes
    t = re.sub(r"\.\d{3}$", "", t)                    # Blender duplicate suffix
    t = re.sub(r"_\d{3,6}\b", "", t)                  # family library numbers
    t = SCRUB.sub("", t)
    t = t.replace("_", " ").replace("O039", "")
    t = re.sub(r"\s*-\s*", " ", t)                    # no dashes in visible text
    t = re.sub(r"\(\d+\)", "", t)
    t = re.sub(r"[^ -~]", "", t)
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -_.")
    # repeated family / type halves ("Shower columns Shower columns")
    w = t.split(" ")
    h = len(w) // 2
    if h and w[:h] == w[h:2 * h]:
        t = " ".join(w[h:])
    t = re.sub(r"\bamp\b", "and", t)                 # a leftover "&amp;"
    t = re.sub(r"\b3d revit\b.*$", "", t, flags=re.I).strip()
    # Revit's export cuts long names off mid word (about 55 characters): drop the broken last word
    if len(t) >= 53 and " " in t:
        t = t.rsplit(" ", 1)[0]
    t = re.sub(r"\s+\d$", "", t)                      # a trailing copy number
    # shouted words read badly in the call out; leave short codes and anything with a digit alone
    t = " ".join(w.capitalize() if w.isupper() and w.isalpha() and len(w) > 3 else w for w in t.split(" "))
    t = re.sub(r"\s{2,}", " ", t).strip(" -_.,")
    return t[:70] or "Element"


def classify(name: str):
    n = name.lower()
    for disc, cat, keys in RULES:
        if any(k in n for k in keys):
            return disc, cat
    return FALLBACK


def phase(name: str) -> str:
    return "Existing" if re.search(r"\bexist", name, re.I) else "New"


# ---------------------------------------------------------------- join multi part families
def descendants(o):
    out = []
    for c in o.children:
        out.append(c); out.extend(descendants(c))
    return out

for cam in [o for o in bpy.data.objects if o.type == "CAMERA"]:
    bpy.data.objects.remove(cam, do_unlink=True)

roots = [o for o in bpy.data.objects if o.type == "EMPTY" and (o.parent is None or o.parent.type != "EMPTY")]
for root in roots:
    kids = [c for c in descendants(root) if c.type == "MESH"]
    if not kids:
        continue
    bpy.ops.object.select_all(action="DESELECT")
    for k in kids:
        k.select_set(True)
    bpy.context.view_layer.objects.active = kids[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    if len(kids) > 1:
        bpy.ops.object.join()
    bpy.context.view_layer.objects.active.name = root.name

for e in [o for o in bpy.data.objects if o.type == "EMPTY"]:
    bpy.data.objects.remove(e, do_unlink=True)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]

# ---------------------------------------------------------------- thin dense fixtures
def tri_count(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)

LIMIT = {"architecture": 5000, "structure": 1400}
by_data = collections.defaultdict(list)
for o in meshes:
    by_data[o.data.name].append(o)
for users in by_data.values():
    o = users[0]
    disc, _ = classify(o.name)
    cap = LIMIT.get(disc, 900)
    t = tri_count(o)
    if t > cap:
        # repeated families share one mesh: thin it once, then hand it back to every copy
        o.data = o.data.copy()
        m = o.modifiers.new("thin", "DECIMATE")
        m.ratio = max(cap / t, 0.008)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="thin")
        for other in users[1:]:
            other.data = o.data

# ---------------------------------------------------------------- recentre, drop materials, tag
mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
centre = (mn + mx) / 2
for o in meshes:
    o.location.x -= centre.x
    o.location.y -= centre.y
    o.location.z -= mn.z

# ---------------------------------------------------------------- face orientation
# Revit exports some faces pointing inwards. Every watertight piece is turned so its faces point out.
# Pieces that are open sheets (the site surface, thinned fixtures, railing cables) have no inside or
# outside to work from, so they are left as exported and the website draws them on both sides.
import bmesh
fixed_faces = 0; closed = 0; seen = set()
for o in meshes:
    me = o.data
    if me.name in seen:
        continue
    seen.add(me.name)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    # weld a copy to judge whether the piece is watertight (the export splits vertices at sharp edges)
    probe = bm.copy()
    bmesh.ops.remove_doubles(probe, verts=probe.verts, dist=1e-5)
    watertight = len(probe.faces) > 3 and all(len(e.link_faces) == 2 for e in probe.edges)
    probe.free()
    if watertight:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        before = [f.normal.copy() for f in bm.faces]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        turned = [i for i, (f, b) in enumerate(zip(bm.faces, before)) if f.normal.dot(b) < 0]
        fixed_faces += len(turned)
        closed += 1
        if turned:
            # flip the same faces on the untouched mesh, so its split edges and shading stay as exported
            if len(me.polygons) == len(before):
                for i in turned:
                    me.polygons[i].flip()
                me.update()
    bm.free()
# the site surface is a sheet: make sure it faces the sky
for o in meshes:
    if "surface" in o.name.lower():
        me = o.data
        up = sum(p.area * (o.matrix_world.to_3x3() @ p.normal).z for p in me.polygons)
        if up < 0:
            me.flip_normals(); me.update()
            print("SURFACE_FLIPPED", o.name[:30])
print("ORIENT watertight pieces", closed, "of", len(seen), "faces turned", fixed_faces)

# ---------------------------------------------------------------- glass and frames
# The Revit export carries no materials, so glazing is found by shape: a pane is a broad face
# (not a thin strip) lying in the plane of the opening. Each face of a window or glazed door is
# painted as glass, light frame or dark frame; the website reads that paint as the finish colour.
GLASS = (0.30, 0.42, 0.50, 1.0)
LIGHT_FRAME = (0.90, 0.90, 0.88, 1.0)
DARK_FRAME = (0.035, 0.035, 0.04, 1.0)
painted = 0
for o in meshes:
    disc, cat = classify(o.name)
    n = o.name.lower()
    if cat == "Windows":
        frame = LIGHT_FRAME
    elif cat == "Doors" and any(k in n for k in ("sliding", "glass", "french", "patio", "bifold")):
        frame = DARK_FRAME
    else:
        continue
    me = o.data
    if me.users > 1:
        me = o.data = me.copy()
    dims = sorted(o.dimensions / max(o.scale.x, 1e-9))          # local size, thinnest first
    thin_axis = min(range(3), key=lambda i: (o.dimensions[i] / max(o.scale[i], 1e-9)))
    face_area = max(dims[1] * dims[2], 1e-9)
    col = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly in me.polygons:
        vs = [me.vertices[i].co for i in poly.vertices]
        ext = sorted(max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3))
        broad = ext[2] > 0 and ext[1] / ext[2] > 0.22          # not a thin strip
        in_plane = abs(poly.normal[thin_axis]) > 0.9
        is_glass = broad and in_plane and poly.area / face_area > 0.025
        c = GLASS if is_glass else frame
        for li in poly.loop_indices:
            col.data[li].color = c
    me.color_attributes.active_color = col
    painted += 1
print("PAINTED", painted)

summary = collections.OrderedDict()
types = collections.defaultdict(collections.Counter)
total_tris = 0
for i, o in enumerate(sorted(meshes, key=lambda m: m.name)):
    disc, cat = classify(o.name)
    typ = clean_type(o.name)
    o.data.materials.clear()
    for k in list(o.keys()):
        del o[k]
    o["d"] = disc; o["c"] = cat; o["t"] = typ; o["p"] = phase(o.name)
    o.name = f"e{i:04d}"
    t = tri_count(o)
    total_tris += t
    s = summary.setdefault(disc, {"elements": 0, "tris": 0, "categories": collections.Counter()})
    s["elements"] += 1; s["tris"] += t; s["categories"][cat] += 1
    types[cat][typ] += 1

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB, export_format="GLB", use_selection=True,
    export_extras=True, export_apply=True, export_yup=True,
    export_materials="NONE", export_texcoords=False, export_normals=True,
    export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True,
    export_cameras=False, export_lights=False, export_animations=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
    export_draco_position_quantization=13, export_draco_normal_quantization=8,
)

report = {
    "elements": len(meshes), "triangles": total_tris,
    "size": [round(v, 2) for v in (mx - mn)],
    "disciplines": {k: {"elements": v["elements"], "triangles": v["tris"], "categories": dict(v["categories"])} for k, v in summary.items()},
    "types": {c: dict(t.most_common()) for c, t in types.items()},
}
with open(OUT_JSON, "w", encoding="utf8") as f:
    json.dump(report, f, indent=1)
print("MODEL_OK", len(meshes), "elements", total_tris, "tris")
