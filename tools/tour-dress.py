# Second pass on the tour scene: BlenderKit materials, staging, open doors, neighbours and an HDRI.
#
#   blender -b assets-src/amber/tour-base.blend -P tools/tour-dress.py -- assets-src/amber/tour.blend
#
# Reads the free assets fetched by tools/tour-bkit.py (listed in assets-src/amber/tour/bkit-assets.json)
# plus one HDRI from the local BlenderKit cache, and saves tour.blend in place.
#   1. finishes: the procedural finish classes from tour-scene.py are swapped for BlenderKit materials, laid on by
#      world position with box projection at true size (the Revit meshes carry no usable UVs), normal maps
#      turned into bump from the height maps for the same reason
#   2. staging: the simple boxes from tour-scene.py go; BlenderKit furniture, lamps, plants, art, books,
#      bath and kitchen accessories, outdoor furniture take their place. The Revit bed in the primary bedroom
#      is replaced by a dressed bed. Collection instances, so the file stays small
#   3. doors on the tour route lose their leaves, so the arrows point through real openings
#   4. outside: neighbouring houses on both sides, across the street and behind, street and garden trees,
#      a free sunny neighbourhood HDRI (BlenderKit) for sky and far horizon, a sun lamp through the street glazing
# Environment switches: TOUR_HDRI_ROT (degrees), TOUR_HDRI_EV, TOUR_SUN_W, TOUR_FLOOR_SIZE
import bpy, bmesh, os, sys, json, math, glob, re
from mathutils import Vector, Matrix, Euler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = json.load(open(os.path.join(ROOT, "assets-src", "amber", "tour", "bkit-assets.json")))
BYNAME = {v["name"]: v for v in LOG.values()}
ENV = lambda k, d: float(os.environ.get(k, d))
s = bpy.context.scene
D = bpy.data
house = D.collections["house"]
SIZE = Vector(json.loads(s["size"]))
FRONT = s["front"]
elev = json.loads(s["levels"])

def node(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n

# ------------------------------------------------------------------ materials
def load_material(name):
    path = BYNAME[name]["file"]
    with D.libraries.load(path, link=False) as (src, dst):
        dst.materials = list(src.materials)
    mats = [m for m in dst.materials if m]
    return mats[0]

def world_map(mat, size, rot=0.0, bump=0.35, tint=None, tint_fac=0.0, rough_add=0.0):
    """Drive every image of a material by world position at `size` metres per repeat, box projected.
    Normal maps become bump from the height map (no UVs on the model). Optional tint towards a colour."""
    nt = mat.node_tree
    geo = node(nt, "ShaderNodeNewGeometry")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size,) * 3
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
    nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
    height = None
    for n in list(nt.nodes):
        if n.type == "TEX_IMAGE":
            n.projection = "BOX"; n.projection_blend = 0.25
            for l in list(n.inputs["Vector"].links):
                nt.links.remove(l)
            nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
            nm = (n.image.name if n.image else "").lower()
            if any(k in nm for k in ("disp", "height", "bump")):
                height = n
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    # normal maps need tangents from UVs: replace them by a bump from the height map
    for n in list(nt.nodes):
        if n.type == "NORMAL_MAP":
            outs = [l.to_socket for l in n.outputs[0].links]
            for sock in outs:
                if height is not None:
                    b = node(nt, "ShaderNodeBump")
                    b.inputs["Strength"].default_value = bump
                    b.inputs["Distance"].default_value = 0.004 * size
                    nt.links.new(height.outputs["Color"], b.inputs["Height"])
                    nt.links.new(b.outputs["Normal"], sock)
                else:
                    for l in list(sock.links):
                        nt.links.remove(l)
    for n in nt.nodes:                                    # no true displacement in a tour render
        if n.type == "OUTPUT_MATERIAL":
            for l in list(n.inputs["Displacement"].links):
                nt.links.remove(l)
    if bsdf and tint is not None and bsdf.inputs["Base Color"].links:
        src = bsdf.inputs["Base Color"].links[0].from_socket
        mix = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MIX")
        mix.inputs[0].default_value = tint_fac
        mix.inputs[7].default_value = (*tint, 1)
        nt.links.new(src, mix.inputs[6]); nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    if bsdf and rough_add and bsdf.inputs["Roughness"].links:
        src = bsdf.inputs["Roughness"].links[0].from_socket
        m = node(nt, "ShaderNodeMath", operation="ADD", use_clamp=True)
        m.inputs[1].default_value = rough_add
        nt.links.new(src, m.inputs[0]); nt.links.new(m.outputs[0], bsdf.inputs["Roughness"])
    return mat

def calm(mat, sat=0.7, val=1.0):
    """Take some saturation out of a material's colour (white oak, not orange pine)."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not bsdf or not bsdf.inputs["Base Color"].links:
        return mat
    src = bsdf.inputs["Base Color"].links[0].from_socket
    hs = node(nt, "ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = sat; hs.inputs["Value"].default_value = val
    nt.links.new(src, hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
    return mat

FLOOR = calm(world_map(load_material("Oak Wood Planks"), ENV("TOUR_FLOOR_SIZE", "2.2"), rot=90, bump=0.25), 0.62, 1.12)
JOINERY = calm(world_map(load_material("Oak Wood Natural Clean"), 1.4, rot=0, bump=0.15), 0.6, 1.1)
PLASTER = world_map(load_material("Painted Plaster Wall"), 2.4, bump=0.12, tint=(0.86, 0.85, 0.83), tint_fac=0.72)
TILE_WALL = world_map(load_material("Regular white marble tiles"), 1.2, bump=0.25)
TILE_FLOOR = TILE_WALL.copy(); TILE_FLOOR.name = "tile_floor_grey"
calm(TILE_FLOOR, 0.3, 0.86)                               # the same marble tile, in a warm grey for floors
DECK = FLOOR.copy(); DECK.name = "deck_boards"
calm(DECK, 0.35, 1.15)                                    # weathered, silvered boards outside
BLACK = world_map(load_material("Black matte metal"), 1.0, bump=0.05)
RUG = world_map(load_material("Wool Carpet"), 0.8, bump=0.3, tint=(0.62, 0.58, 0.52), tint_fac=0.35)
# kept from tour-scene.py after a look test: its quartz and brushed steel read better than Marble 01 and the
# BlenderKit steel (the first read as big beige tiles at worktop scale, the second turned the sink black)

swaps = 0
for o in house.objects:
    for slot in o.material_slots:
        m = slot.material
        if not m:
            continue
        new = None
        c = sum((Vector(v) for v in o.bound_box), Vector()) / 8
        outside = o["c"] == "Floors" and c.y * FRONT < -(SIZE.y / 2 - 5.2) and c.z > 6.0   # the back deck
        if m.name == "woodfloor": new = DECK if outside else FLOOR
        elif m.name in ("wall", "white"): new = PLASTER
        elif m.name == "oak": new = JOINERY
        elif m.name == "tile": new = TILE_FLOOR if o["c"] == "Floors" else TILE_WALL
        elif m.name == "black": new = BLACK
        if new:
            slot.material = new; swaps += 1
print("DRESS material swaps", swaps)

# the primary bath is tiled floor to ceiling, as a real one would be: every wall and floor face inside its
# box takes the tile (the model only tiles the shower walls)
BATH_LO, BATH_HI = Vector((1.75, -2.0, 6.55)), Vector((4.95, 1.3, 9.2))
BATH_C = Vector((3.35, -0.35, 7.6))
tiled = 0
for o in house.objects:
    if o["c"] not in ("Walls", "Floors"):
        continue
    me = o.data
    idx = {}
    for i, sl in enumerate(o.material_slots):
        idx[sl.material.name if sl.material else ""] = i
    want = TILE_FLOOR if o["c"] == "Floors" else TILE_WALL
    hit = [p for p in me.polygons if all(BATH_LO[k] <= p.center[k] <= BATH_HI[k] for k in range(3))
           and (abs(p.normal.z) > 0.7) == (o["c"] == "Floors")
           and (o["c"] == "Floors" or (BATH_C - p.center).dot(p.normal) > 0)]   # wall faces that look into the bath
    if not hit:
        continue
    if want.name not in idx:
        me.materials.append(want); idx[want.name] = len(me.materials) - 1
    for p in hit:
        p.material_index = idx[want.name]
    tiled += len(hit)
print("DRESS bath faces tiled", tiled)

# every floor face out on the back deck (behind the bedroom sliders) takes the weathered deck boards
decked = 0
for o in house.objects:
    if o["c"] not in ("Floors", "Roofs"):
        continue
    me = o.data
    hit = [p for p in me.polygons if p.normal.z > 0.7 and p.center.y * FRONT < -8.1 and p.center.z > 6.0]
    if not hit:
        continue
    if DECK.name not in [m.name for m in me.materials if m]:
        me.materials.append(DECK)
    i = [m.name if m else "" for m in me.materials].index(DECK.name)
    for p in hit:
        p.material_index = i
    decked += len(hit)
print("DRESS deck faces", decked)

# ------------------------------------------------------------------ doors on the route: leaves out, frames stay
OPEN = {"e0432", "e0808", "e0811", "e0820", "e0806", "e0831", "e0814"}
for name in OPEN:
    if name in D.objects:
        D.objects[name].hide_render = True; D.objects[name].hide_viewport = True
print("DRESS doors opened", sorted(OPEN))

# ------------------------------------------------------------------ old staging out
old = D.collections.get("staging")
if old:
    for o in list(old.objects):
        D.objects.remove(o, do_unlink=True)
for o in list(house.objects):                            # the Revit bed in the primary bedroom gives way to a dressed bed
    if o["c"] == "Furniture" and "bed" in o["t"].lower():
        c = sum((Vector(v) for v in o.bound_box), Vector()) / 8
        if c.x > 1.5 and c.y < -3 and c.z > 6.0:
            o.hide_render = True; o.hide_viewport = True
stage = old or D.collections.new("staging")
if stage.name not in s.collection.children:
    s.collection.children.link(stage)
lib = D.collections.new("bk_library")                    # instanced sources, not in the scene themselves

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

def floor_at(x, y, z):
    ok, loc, *_ = s.ray_cast(dg, Vector((x, y, z + 1.2)), Vector((0, 0, -1)), distance=2.6)
    return loc.z if ok else z

def top_at(x, y, z_from, reach=1.6):
    """first surface below a point (a counter, a table, a vanity)"""
    ok, loc, *_ = s.ray_cast(dg, Vector((x, y, z_from)), Vector((0, 0, -1)), distance=reach)
    return loc.z if ok else None

def wall_hit(p, d, reach=6.0):
    d = Vector((d[0], d[1], d[2] if len(d) > 2 else 0.0)).normalized()
    ok, loc, nrm, *_ = s.ray_cast(dg, Vector(p), d, distance=reach)
    return (loc, nrm) if ok else (None, None)

SOURCES = {}
def source(name):
    """Append a BlenderKit model once into its own collection; returns the collection to instance."""
    if name in SOURCES:
        return SOURCES[name]
    with D.libraries.load(BYNAME[name]["file"], link=False) as (src, dst):
        dst.objects = list(src.objects)
    col = D.collections.new("bk_" + re.sub(r"[^A-Za-z0-9]+", "_", name)[:30])
    lib.children.link(col)
    for o in dst.objects:
        if o:
            col.objects.link(o)
            o.hide_render = False
    SOURCES[name] = col
    return col

def place(name, x, y, z, rot=0.0, scale=1.0, tilt=(0.0, 0.0)):
    e = D.objects.new("st_" + name[:20], None)
    e.instance_type = "COLLECTION"
    e.instance_collection = source(name)
    e.location = (x, y, z)
    e.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), math.radians(rot))
    e.scale = (scale,) * 3
    stage.objects.link(e)
    return e

def lamp(x, y, z, watts, size=0.12, color=(1.0, 0.82, 0.6)):
    ld = D.lights.new("stage_lamp", "POINT")
    ld.energy = watts; ld.shadow_soft_size = size; ld.color = color
    ob = D.objects.new("stage_lamp", ld); ob.location = (x, y, z)
    stage.objects.link(ob)

def slab(name, cx, cy, z, sx, sy, h, mat, r=0.006):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, h), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=r, segments=3, affect="EDGES")
    bmesh.ops.translate(bm, vec=(cx, cy, z + h / 2), verts=bm.verts)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = D.objects.new(name, me); stage.objects.link(ob)
    return ob

def ceiling_above(x, y, z):
    ok, loc, *_ = s.ray_cast(dg, Vector((x, y, z + 0.5)), Vector((0, 0, 1)), distance=4.0)
    return loc.z if ok else z + 2.44

def on_wall(name, p, d, centre_h, floor_z, depth_axis="y"):
    """Hang a flat piece (art, mirror) on the first wall hit from p along d, centred `centre_h` above the floor.
    The BlenderKit frames lie in x-y with their face up (+z), so they are stood up and turned to face the room."""
    loc, nrm = wall_hit((p[0], p[1], floor_z + centre_h), d)
    if loc is None:
        print("DRESS no wall for", name); return None
    yaw = math.degrees(math.atan2(-nrm.x, nrm.y))          # face +z of the piece along the wall normal
    e = place(name, loc.x + nrm.x * 0.012, loc.y + nrm.y * 0.012, loc.z, rot=yaw + 180, tilt=(90, 0))
    return e

LIV = elev.get("Second floor", 5.34)
zf = floor_at(3.1, 6.3, LIV)
zd = floor_at(-2.6, 5.5, LIV)

# ---- living: sofa with its back to the street glazing, a lounge chair, rug, low oak table, floor lamp, plant, art
slab("rug", 3.0, 6.4, zf, 2.6, 3.0, 0.012, RUG, 0.004)
place("Sofa WOWIN Ingrid", 3.0, 7.6, zf + 0.012, rot=180)       # its front faces +y in the file
place("Reni Lounge Chair", 1.55, 6.1, zf + 0.012, rot=-60)
slab("coffee_top", 3.0, 6.3, zf + 0.37, 1.2, 0.62, 0.035, JOINERY)
for dx in (-0.52, 0.52):
    for dy in (-0.24, 0.24):
        slab("coffee_leg", 3.0 + dx, 6.3 + dy, zf + 0.012, 0.035, 0.035, 0.36, BLACK, 0.003)
place("Stack of books", 2.72, 6.25, zf + 0.405, rot=12)
place("Vase with cotton flowers", 3.35, 6.36, zf + 0.405, rot=40)
place("Oslo Floor Lamp", 4.35, 7.85, zf + 0.012)
lamp(4.35, 7.85, zf + 1.25, 18)
place("Indoor Plant Bird Of ParadiseBird", 4.45, 5.0, zf, rot=30)
art = on_wall("Painting abstract procedural", (-1.6, 5.9), (0, -1), 1.5, zd)

# ---- dining: a table set, two pendants over it, a fig by the window
place("Modern minimal table set", -2.6, 5.5, zd, rot=90)
place("Fiddle Leaf Fig Tree (Medium)", -4.35, 7.6, zd, scale=3.0)
cz = ceiling_above(-2.6, 5.5, zd + 2.0)
for dx in (-0.45, 0.45):
    place("Beatrice Pendant Lamp", -2.6 + dx, 5.5, cz - 0.87, scale=0.75 if dx else 1)
    lamp(-2.6 + dx, 5.5, cz - 0.75, 22, 0.15)

# ---- kitchen: three small pendants over the island, coffee machine, fruit bowl, cutting board
KIT = floor_at(-1.7, 1.5, LIV)
kc = ceiling_above(-1.65, 2.6, KIT + 2.0)
for dx in (-0.8, 0.0, 0.8):
    place("Waveform Pendant", -1.65 + dx, 2.6, kc - 1.04)
    lamp(-1.65 + dx, 2.6, kc - 0.98, 6, 0.04)
for (nm, x, y, rot) in (("Simple Fruit Bowl", -1.25, 2.55, 20), ("Coffee machine", -4.5, 1.25, 90), ("Wooden Cutting Board", -3.2, 3.25, 5)):
    t = top_at(x, y, KIT + 1.4)
    if t and t > KIT + 0.7:
        place(nm, x, y, t, rot=rot)
    else:
        print("DRESS no counter for", nm, t)

# ---- entry: art on the blank wall, a ficus by the stair
ENT = elev.get("Ground floor", 2.07)
EZ = floor_at(1.55, 6.3, ENT)
on_wall("Japanese woodcut print", (1.55, 6.3), (-1, 0), 1.6, EZ)
place("Artificial tree Ficus 110 cm", 2.3, 2.7, floor_at(2.3, 2.7, ENT), rot=10)
# a slim oak console under the print, with books and the cotton vase
loc, nrm = wall_hit((1.55, 6.3, EZ + 0.8), (-1, 0))
if loc is not None:
    cx = loc.x + 0.17
    slab("console_top", cx, 6.3, EZ + 0.78, 0.32, 1.1, 0.04, JOINERY)
    for dy in (-0.5, 0.5):
        slab("console_leg", cx + 0.1, 6.3 + dy, EZ, 0.03, 0.03, 0.78, BLACK, 0.003)
    place("Stack of books", cx, 5.98, EZ + 0.82, rot=95)
    place("Vase with cotton flowers", cx, 6.6, EZ + 0.82, rot=10)

# ---- primary bedroom: dressed king bed with its head to the party wall, night stands, lamps, rug, art
TH = elev.get("Third floor", 6.66)
bed_y = -5.95
bz = floor_at(3.6, bed_y, TH)
slab("bed_rug", 3.15, bed_y, bz, 2.6, 3.1, 0.012, RUG, 0.004)
place("Modern King Bed", 4.86 - 1.18, bed_y, bz + 0.012, rot=-90)
for side in (-1, 1):
    y = bed_y + side * 1.42
    place("Night Stand Modern", 4.55, y, bz + 0.012, rot=-90)
    place("Table Lamp Pletz Bethel", 4.6, y, bz + 0.012 + 0.555)
    lamp(4.6, y, bz + 0.92, 9, 0.06)
on_wall("Black and white japanese aquarelle", (2.1, -5.7), (-1, 0), 1.5, bz)

# ---- primary bath: mirror over the vanity, towels, soap, bath mat
# the model's double vanity runs along the east wall, x 4.27 to 4.83, y -1.51 to 0.31, top 0.9 m up
BA = floor_at(3.4, -0.7, TH)
m = on_wall("Azeen Rectangle Wood Mirror", (3.6, -0.6), (1, 0), 1.62, BA)
if m:
    m.scale = (0.62,) * 3
vt = top_at(4.42, 0.12, BA + 1.3)
if vt and vt > BA + 0.6:
    place("Stack of folded towels (fixed bottom)", 4.42, 0.12, vt, rot=90)
vt = top_at(4.42, -1.3, BA + 1.3)
if vt and vt > BA + 0.6:
    place("Soap Dispenser", 4.42, -1.3, vt, rot=-90)
slab("bath_floor", 3.35, -1.03, BA, 3.0, 1.74, 0.004, TILE_FLOOR, 0.0)   # one tiled floor across the vanity zone
place("Grey bath mat", 3.8, -0.6, BA + 0.006, rot=90)
for o in SOURCES["Grey bath mat"].objects:                 # the mat reads as a dark shag in the foreground: lift it
    for sl in getattr(o, "material_slots", []):
        if sl.material and sl.material.node_tree:
            calm(sl.material, 0.4, 1.9)

# ---- back deck: outdoor sofa and chair, planter boxes, a small table
DK = floor_at(0.0, -9.6, TH)
place("Outdoor Lounge Sofa 3 Seat", -2.2, -8.75, DK, rot=0)
place("Outdoor Lounge Armchair", 1.7, -10.6, DK, rot=-130)
slab("deck_table", -2.2, -9.85, DK, 0.55, 0.55, 0.42, JOINERY)
place("Vase with cotton flowers", -2.2, -9.85, DK + 0.42, rot=30)
for (x, y, r) in ((-4.2, -10.6, 90), (3.9, -8.8, 90)):
    if floor_at(x, y, DK) > DK - 0.1:
        place("Planter Box 01", x, y, floor_at(x, y, DK), rot=r)
        place("Fiddle Leaf Fig Tree (Medium)", x, y - 0.18, floor_at(x, y, DK) + 0.3, scale=2.4, rot=r * 2)
        place("Fiddle Leaf Fig Tree (Medium)", x, y + 0.2, floor_at(x, y, DK) + 0.3, scale=2.0, rot=r * 3)
# the outdoor sofa and chair come in dark navy: re-cover them in a warm off white outdoor fabric
for m in D.materials:
    if m.name.startswith("Fabric") and m.node_tree and any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes):
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for l in list(b.inputs["Base Color"].links):
            m.node_tree.links.remove(l)
        b.inputs["Base Color"].default_value = (0.62, 0.58, 0.52, 1)

# ------------------------------------------------------------------ neighbours and trees
half = SIZE.y / 2; side = SIZE.x / 2
low = min(elev.values()) - 0.12
site = [o for o in house.objects if o["c"] == "Site"]
backz = max((max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in site), default=low) - 0.03
HX = 9.47
for sx in (-1, 1):                                        # party wall neighbours, as on a real infill street
    place("Brick House 135", sx * (side + 0.2 + HX / 2), 1.0, low, rot=0)
for x in (-11.0, 0.0, 11.0):                              # across the street, facing it
    place("Brick House 135", x, FRONT * (half + 30.0), low, rot=180 if FRONT > 0 else 0)
for x in (-12.0, 0.0, 12.0):                              # behind the back gardens
    place("Brick House 135", x, -FRONT * (half + 40.0), backz, rot=0 if FRONT > 0 else 180)
for (x, y, sc, r) in ((-7.0, -FRONT * (half + 15), 1.0, 0), (6.0, -FRONT * (half + 21), 0.85, 70), (16.0, -FRONT * (half + 12), 0.9, 140)):
    place("European Maple Acer Campreste", x, y, backz, rot=r, scale=sc)
for (x, r) in ((-8.5, 0), (2.5, 80), (12.0, 200)):
    place("Tree Yellow Birch Betula Alleghaniensis", x, FRONT * (half + 3.2), low, rot=r, scale=1.3)
for o in [o for o in D.objects if o.name.startswith("hedge_")]:
    D.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------ world: free sunny neighbourhood HDRI, sun lamp through the street glazing
hdr = glob.glob(os.path.join(os.path.expanduser("~"), "blenderkit_data", "hdrs", "neighborhood-par_*", "*.exr"))[0]
w = s.world
nt = w.node_tree; nt.nodes.clear()
out = node(nt, "ShaderNodeOutputWorld")
tc = node(nt, "ShaderNodeTexCoord")
mp = node(nt, "ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(ENV("TOUR_HDRI_ROT", "0")))
env = node(nt, "ShaderNodeTexEnvironment"); env.image = D.images.load(hdr, check_existing=True)
bg = node(nt, "ShaderNodeBackground"); bg.inputs["Strength"].default_value = 2 ** ENV("TOUR_HDRI_EV", "0")
nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
hs = node(nt, "ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = ENV("TOUR_HDRI_SAT", "0.72")
nt.links.new(env.outputs["Color"], hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs[0], out.inputs["Surface"])
sun = D.lights.new("sun", "SUN")
sun.energy = ENV("TOUR_SUN_W", "3.2"); sun.angle = math.radians(1.2); sun.color = (1.0, 0.9, 0.76)
so = D.objects.new("sun", sun); s.collection.objects.link(so)
az, el = math.radians(24), math.radians(24)                # as tour-scene.py: in front of the street glazing, low
d = Vector((math.sin(az), FRONT * math.cos(az), math.sin(el))).normalized()  # direction towards the sun
so.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()

s.cycles.max_bounces = 10; s.cycles.diffuse_bounces = 6
print("DRESS staging pieces", len(stage.objects), "sources", len(SOURCES))
# same privacy words as tools/build-model-navis.py: nothing from the client, the architect or the site
BANNED = re.compile(r"yoon|leong|morgan|fergus|gellert|jpa|amber|\b315\b|peders|arnold|caroline|parkway|edward martin|byron|\.rvt|\.dxf|element id|source file", re.I)
names = [b.name for coll in (D.objects, D.meshes, D.materials, D.collections, D.worlds, D.lights, D.images) for b in coll]
hits = sorted(set(m.group(0).lower() for m in BANNED.finditer("\n".join(names))))
print("PRIVACY", "FAIL " + str(hits) if hits else "OK")
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
print("DRESS_OK")
