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
OPEN = {"e0432", "e0808", "e0811", "e0820", "e0806", "e0831", "e0814", "e0090"}   # e0090: entry to the office

# door frames came through as bare stainless: paint them like real casings
CASING = D.materials["white"]
for o in house.objects:
    if o["c"] == "Doors" and o["k"] == "metal":
        for sl in o.material_slots:
            sl.material = CASING

# the glazing tinted every view out green (four panes deep in places): make it near neutral
g = D.materials.get("glass")
if g:
    for n in g.node_tree.nodes:
        if n.type == "BSDF_GLASS":
            n.inputs["Color"].default_value = (0.995, 0.997, 0.997, 1)
        if n.type == "BSDF_TRANSPARENT":
            n.inputs["Color"].default_value = (0.99, 0.992, 0.992, 1)
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
    """Append a BlenderKit model once into its own collection; returns the collection to instance.
    `name` is the asset name, or its asset base id where two assets share a name."""
    if name in SOURCES:
        return SOURCES[name]
    entry = LOG[name] if name in LOG else BYNAME[name]
    with D.libraries.load(entry["file"], link=False) as (src, dst):
        dst.objects = list(src.objects)
    col = D.collections.new("bk_" + re.sub(r"[^A-Za-z0-9]+", "_", name)[:30])
    lib.children.link(col)
    for o in dst.objects:
        if o:
            col.objects.link(o)                              # keep the asset's own render visibility: helper cages stay hidden
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
for (nm, x, y, rot) in (("Simple Fruit Bowl", -1.25, 2.55, 20), ("Coffee machine", -4.5, 1.25, 90)):
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
place("Outdoor Armchair with Pillows", 1.7, -10.6, DK, rot=-130)   # cushions on, after the third pass review
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

# ================================================================== third pass: the detail a real house has
PAINT = D.materials["white"]                              # satin white paint for skirting, casings, plates
def strip(name, a, b, nrm, h, depth, z0, mat):
    """A board along the floor line from a to b (on a wall face with normal nrm): skirting or a sill."""
    run = (b - a); L = run.length
    if L < 0.12:
        return None
    t = run.normalized(); n = Vector((nrm.x, nrm.y, 0)).normalized()
    c = (a + b) / 2 + n * (depth / 2 + 0.002)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(L, depth, h), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.003, segments=2, affect="EDGES")
    rot = Matrix.Rotation(math.atan2(t.y, t.x), 4, "Z")
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(c.x, c.y, z0 + h / 2), verts=bm.verts)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = D.objects.new(name, me); trim_col.objects.link(ob)
    return ob

trim_col = D.collections.new("trims"); s.collection.children.link(trim_col)

# ---- skirting: every interior wall face (painted plaster or tile) gets a 90 mm board along its floor edges
skirts = 0
for o in house.objects:
    if o["c"] != "Walls":
        continue
    me = o.data
    names = [m.name if m else "" for m in me.materials]
    for p in me.polygons:
        if abs(p.normal.z) > 0.1 or names[p.material_index] not in (PLASTER.name, TILE_WALL.name):
            continue
        zs = [me.vertices[v].co.z for v in p.vertices]
        zmin = min(zs)
        for ek in p.edge_keys:
            a, b = me.vertices[ek[0]].co, me.vertices[ek[1]].co
            if abs(a.z - zmin) > 0.01 or abs(b.z - zmin) > 0.01:
                continue
            mid = (a + b) / 2 + p.normal * 0.05
            fz = top_at(mid.x, mid.y, zmin + 0.3, 0.45)      # a floor right under this edge, inside the room
            if fz is None or abs(fz - zmin) > 0.12:
                continue
            if strip("skirt", Vector((a.x, a.y, 0)), Vector((b.x, b.y, 0)), p.normal, 0.09, 0.014, fz,
                     TILE_WALL if names[p.material_index] == TILE_WALL.name else PAINT):
                skirts += 1
print("DRESS skirting boards", skirts)

# ---- window casings and sills on the room side of every punched window (not the curtain wall glazing)
cased = 0
for o in house.objects:
    if o["c"] != "Windows" or o["k"] != "black" or "curtain wall" in o["t"].lower():   # curtain wall units have no casing
        continue
    lo = Vector([min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)])
    hi = Vector([max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for i in range(3)])
    size = hi - lo
    if max(size.x, size.y) > 2.4 or size.z < 0.4 or size.z > 2.6:
        continue
    if min(size.x, size.y) > 0.3:                            # on the angled street facade a box casing would float off the glass
        continue
    thin = 0 if size.x < size.y else 1
    for sign in (-1, 1):
        nrm = Vector((sign, 0, 0)) if thin == 0 else Vector((0, sign, 0))
        face = (lo[thin] if sign < 0 else hi[thin])
        probe = (lo + hi) / 2; probe[thin] = face + sign * 0.5
        up = ceiling_above(probe.x, probe.y, lo.z)
        if up - lo.z > 3.2:                                   # nothing overhead: this is the outside face
            continue
        fz = top_at(probe.x, probe.y, lo.z + 0.05, 3.0)       # glazing down to the floor is a door: no sill or casing
        if fz is None or lo.z - fz < 0.3:
            continue
        a = Vector((lo.x, lo.y, 0)); b = Vector((hi.x, hi.y, 0)); a[thin] = b[thin] = face
        strip("sill", a - (b - a).normalized() * 0.06, b + (b - a).normalized() * 0.06, nrm, 0.03, 0.12, lo.z - 0.03, PAINT)
        strip("head", a - (b - a).normalized() * 0.06, b + (b - a).normalized() * 0.06, nrm, 0.07, 0.016, hi.z, PAINT)
        for e in (a, b):
            post = strip("jamb", e, e + Vector((0, 0, 0)) + (b - a).normalized() * 0.0001, nrm, 0.0, 0.0, 0.0, PAINT) if False else None
            bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
            sx, sy = (0.016, 0.07) if thin == 0 else (0.07, 0.016)
            bmesh.ops.scale(bm, vec=(sx, sy, size.z), verts=bm.verts)
            off = nrm * 0.01
            bmesh.ops.translate(bm, vec=(e.x + off.x, e.y + off.y, lo.z + size.z / 2), verts=bm.verts)
            me = D.meshes.new("jamb"); bm.to_mesh(me); bm.free(); me.materials.append(PAINT)
            jo = D.objects.new("jamb", me); trim_col.objects.link(jo)
        cased += 1
print("DRESS windows cased", cased)

# ---- light switches and sockets: plain white plates at real heights on the walls each room looks at
def plate(p, nrm, w, h, kind):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    n = Vector((nrm.x, nrm.y, 0)).normalized()
    bmesh.ops.scale(bm, vec=(w if abs(n.y) > abs(n.x) else 0.009, 0.009 if abs(n.y) > abs(n.x) else w, h), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.0025, segments=2, affect="EDGES")
    c = p + n * 0.0045
    bmesh.ops.translate(bm, vec=(c.x, c.y, c.z), verts=bm.verts)
    me = D.meshes.new(kind); bm.to_mesh(me); bm.free(); me.materials.append(PAINT)
    ob = D.objects.new(kind, me); trim_col.objects.link(ob)
plates = 0
for (cx, cy, fz) in ((1.55, 5.2, None), (0.2, 5.9, None), (-1.7, 1.5, None), (2.2, -6.7, None), (3.6, -0.95, None), (4.0, 5.8, None)):
    z0 = floor_at(cx, cy, 2.07 if cy > 4.5 and cx > 1 and cx < 2 else (5.34 if cy > 0 else 6.66))
    hits = []
    for i in range(16):
        a = 2 * math.pi * i / 16
        d = Vector((math.sin(a), math.cos(a), 0))
        ok, loc, nrm, idx, ob, _m = s.ray_cast(dg, Vector((cx, cy, z0 + 0.3)), d, distance=4.0)
        if ok and ob.get("c") == "Walls" and abs(nrm.z) < 0.1 and (loc - Vector((cx, cy, z0 + 0.3))).length > 0.8:
            hits.append((loc, nrm))
    for loc, nrm in hits[::5][:2]:                          # two sockets 300 mm up
        plate(loc, nrm, 0.085, 0.12, "socket"); plates += 1
    if hits:                                                 # one switch at 1.1 m
        loc, nrm = hits[len(hits) // 2]
        plate(Vector((loc.x, loc.y, z0 + 1.1)), nrm, 0.085, 0.12, "switch"); plates += 1
print("DRESS switch and socket plates", plates)

# ---- ceiling fittings: a white trim ring and a lit lens under every ceiling light from tour-scene.py
LENS = D.materials.new("downlight_lens"); LENS.use_nodes = True
lnt = LENS.node_tree; lnt.nodes.clear()
lo_ = node(lnt, "ShaderNodeOutputMaterial"); le = node(lnt, "ShaderNodeEmission")
le.inputs["Color"].default_value = (1.0, 0.9, 0.78, 1); le.inputs["Strength"].default_value = 30.0
lnt.links.new(le.outputs[0], lo_.inputs["Surface"])
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.062, radius2=0.062, depth=0.012)
bmesh.ops.translate(bm, vec=(0, 0, -0.004), verts=bm.verts)
ring = D.meshes.new("downlight"); bm.to_mesh(ring); bm.free()
ring.materials.append(PAINT); ring.materials.append(LENS)
for p in ring.polygons:
    if p.normal.z < -0.9:
        p.material_index = 1
fit = 0
for o in D.collections["lamps"].objects:
    ob = D.objects.new("downlight", ring); ob.location = o.location + Vector((0, 0, 0.004)); trim_col.objects.link(ob)
    o.location.z -= 0.012                                     # the light sits just under its lens
    fit += 1
print("DRESS downlight fittings", fit)

# ---- curtains: sheer linen panels stacked at both ends of the big glazing, rail to floor
def curtains(a, b, inward, floor_z, ceil_z, width=0.62):
    """Stacks at both ends of an opening running a to b (floor plan points); inward points into the room."""
    t = (b - a).normalized(); yaw = math.degrees(math.atan2(t.y, t.x))
    h = ceil_z - floor_z - 0.03
    for end, sgn in ((a, 1), (b, -1)):
        c = end + t * sgn * (width / 2 - 0.05) + inward * 0.16
        e = place("Curtain Parametric", c.x, c.y, floor_z + 0.17 * h / 2.84, rot=yaw)
        e.scale = (width / 3.27, 0.55, h / 2.84)
LZ = floor_at(1.5, 7.6, LIV)
curtains(Vector((-0.30, 8.05)), Vector((4.25, 9.03)), Vector((0.21, -0.98)), LZ, ceiling_above(1.5, 7.9, LZ + 2.0))
curtains(Vector((-4.32, 6.86)), Vector((-1.30, 7.44)), Vector((0.19, -0.98)), LZ, ceiling_above(-2.8, 6.9, LZ + 2.0))
BZ = floor_at(2.7, -7.6, TH)
curtains(Vector((1.62, -8.05)), Vector((4.55, -8.05)), Vector((0, 1)), BZ, ceiling_above(2.7, -7.6, BZ + 2.0))
# the parametric curtain's sheer reads best a little warmer and a touch translucent
for m in D.materials:
    if m.name.startswith("Voilage") and m.node_tree:
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b:
            for l in list(b.inputs["Base Color"].links):
                m.node_tree.links.remove(l)
            b.inputs["Base Color"].default_value = (0.86, 0.83, 0.77, 1)

# ---- primary bedroom: an oak sideboard under the print on the long blank wall, a plant, a reading lamp
loc, nrm = wall_hit((2.1, -5.7, bz + 0.5), (-1, 0))
if loc is not None:
    place("Geome Sideboard", loc.x + 0.27, -5.7, bz + 0.012, rot=90)
    place("Vase with cotton flowers", loc.x + 0.25, -6.15, bz + 0.79, rot=20)
    place("Stack of books", loc.x + 0.25, -5.25, bz + 0.79, rot=80)
place("Potted Plant 02", 1.1, -7.5, bz + 0.012, rot=40)   # the snake plant model rendered as two floating leaves
place("Oslo Floor Lamp", 1.05, -4.0, bz + 0.012)
lamp(1.05, -4.0, bz + 1.25, 14)

# ---- entry: runner, round mirror over a bouclette bench, a snake plant, a pendant; the office door stands open
RUNNER = world_map(load_material("Modern runner rug"), 2.6, rot=90, bump=0.2)
slab("runner", 1.6, 5.75, EZ, 0.85, 3.0, 0.01, RUNNER, 0.003)
loc, nrm = wall_hit((1.55, 6.15, EZ + 1.5), (1, 0))
if loc is not None:
    m = place("Round mirror", loc.x - 0.012, 6.15, loc.z, rot=90, tilt=(90, 0))
    place("c7e93d6a-65f4-4f93-83e1-15fdfbd11ee8", loc.x - 0.24, 6.15, EZ + 0.01, rot=-90)   # the 1.04 m bouclette bench
    place("Snake Plant | Potted Indoor Plant", loc.x - 0.16, 6.95, EZ + 0.01, scale=1.4)
ec = ceiling_above(1.6, 6.15, EZ + 2.0)
place("Beatrice Pendant Lamp", 1.6, 6.15, ec - 0.87 * 0.8, scale=0.8)
lamp(1.6, 6.15, ec - 0.6, 18, 0.15)
# the office beyond the open door: a white desk, a task chair, a plant, its own lamp
OZ = floor_at(4.0, 5.0, ENT)
place("Modern white wooden desk", 4.55, 5.0, OZ, rot=-90)
place("HM Embody Chair White/Black", 3.95, 5.0, OZ, rot=90)
place("Potted Plant 01", 4.45, 6.1, OZ, rot=15)
lamp(4.3, 5.0, OZ + 2.0, 30, 0.3)

# ---- primary bath: the shower pony wall tiled all round with a glass screen and black profile on top,
#      a heated towel rail with towels, a small plant
for name in ("e1035", "e1056"):
    o = D.objects.get(name)
    if o:
        o.data.materials.clear(); o.data.materials.append(TILE_WALL)
PW_LO, PW_HI = Vector((2.07, -0.71, 6.66)), Vector((3.20, -0.59, 7.86))
SCREEN = D.materials.new("shower_glass"); SCREEN.use_nodes = True
snt = SCREEN.node_tree; snt.nodes.clear()
so_ = node(snt, "ShaderNodeOutputMaterial"); sg = node(snt, "ShaderNodeBsdfGlass")
sg.inputs["IOR"].default_value = 1.5; sg.inputs["Roughness"].default_value = 0.0; sg.inputs["Color"].default_value = (0.97, 0.985, 0.985, 1)
st_ = node(snt, "ShaderNodeBsdfTransparent"); st_.inputs["Color"].default_value = (0.96, 0.98, 0.98, 1)
lp = node(snt, "ShaderNodeLightPath"); mx = node(snt, "ShaderNodeMixShader")
mxv = node(snt, "ShaderNodeMath", operation="MAXIMUM")
snt.links.new(lp.outputs["Is Shadow Ray"], mxv.inputs[0]); snt.links.new(lp.outputs["Is Diffuse Ray"], mxv.inputs[1])
snt.links.new(mxv.outputs[0], mx.inputs[0]); snt.links.new(sg.outputs[0], mx.inputs[1]); snt.links.new(st_.outputs[0], mx.inputs[2])
snt.links.new(mx.outputs[0], so_.inputs["Surface"])
cy_ = (PW_LO.y + PW_HI.y) / 2; L_ = PW_HI.x - PW_LO.x; top = PW_HI.z
slab("shower_screen", (PW_LO.x + PW_HI.x) / 2, cy_, top + 0.02, L_ - 0.03, 0.008, 0.82, SCREEN, 0.0)
slab("screen_shoe", (PW_LO.x + PW_HI.x) / 2, cy_, top, L_, 0.03, 0.03, BLACK, 0.002)
slab("screen_cap", (PW_LO.x + PW_HI.x) / 2, cy_, top + 0.83, L_, 0.02, 0.02, BLACK, 0.002)
slab("screen_post", PW_HI.x - 0.012, cy_, top, 0.024, 0.024, 0.85, BLACK, 0.002)
loc, nrm = wall_hit((2.73, -1.0, BA + 1.05), (0, -1))
if loc is not None:
    place("Bathroom heated towel rail", loc.x, loc.y + 0.02, loc.z, rot=180, tilt=(90, 0))   # front (its +z) to the room
place("Snake Plant | Potted Indoor Plant", 4.55, -1.72, BA + 0.006, rot=30)

# ---- back deck: a rug, lanterns, a string of lights, more planting; chair with cushions
slab("deck_rug", -2.2, -9.75, DK, 2.4, 1.5, 0.01, RUG, 0.003)
for (x, y) in ((-3.55, -9.45), (-0.95, -8.45)):
    place("Lantern 01", x, y, DK, scale=2.2)
    lamp(x, y, DK + 0.3, 6, 0.04, (1.0, 0.7, 0.4))
for (nm2, x, y, sc, r) in (("Potted Plant 01", 4.1, -10.3, 1.1, 30), ("Potted Plant 02", -3.4, -8.45, 1.1, 60),
                           ("Monestera Plant Small Potted", 3.2, -8.45, 1.0, 200)):
    if floor_at(x, y, DK) > DK - 0.1:
        place(nm2, x, y, floor_at(x, y, DK), rot=r, scale=sc)
BULB = D.materials.new("bulb_warm"); BULB.use_nodes = True
bnt = BULB.node_tree; bnt.nodes.clear()
bo = node(bnt, "ShaderNodeOutputMaterial"); be = node(bnt, "ShaderNodeEmission")
be.inputs["Color"].default_value = (1.0, 0.66, 0.36, 1); be.inputs["Strength"].default_value = 14.0
bnt.links.new(be.outputs[0], bo.inputs["Surface"])
def festoon(a, b, sag, n):
    """A sagging wire with warm bulbs between a and b (world points)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t); p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    cu = D.curves.new("festoon", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.003
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for sp_pt, p in zip(sp.points, pts):
        sp_pt.co = (p.x, p.y, p.z, 1)
    cu.materials.append(BLACK)
    co = D.objects.new("festoon", cu); stage.objects.link(co)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.02)
    bme = D.meshes.new("bulb"); bm.to_mesh(bme); bm.free(); bme.materials.append(BULB)
    for p in pts[1:-1:2]:
        bo_ = D.objects.new("bulb", bme); bo_.location = p - Vector((0, 0, 0.04)); stage.objects.link(bo_)
# along the house wall and the two party walls, never straight over the deck camera
festoon(Vector((-4.6, -8.25, DK + 2.35)), Vector((4.6, -8.25, DK + 2.35)), 0.30, 46)
festoon(Vector((-4.55, -8.3, DK + 2.35)), Vector((-4.45, -11.2, DK + 2.0)), 0.22, 20)
festoon(Vector((4.55, -8.3, DK + 2.35)), Vector((4.45, -9.9, DK + 2.1)), 0.15, 12)
print("DRESS third pass done")

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
for (x, r) in ((-8.5, 0), (7.2, 80), (13.5, 200)):        # none straight in front of the living room glazing
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
bg = node(nt, "ShaderNodeBackground"); bg.inputs["Strength"].default_value = 2 ** ENV("TOUR_HDRI_EV", "0.35")   # brighter view out
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
# Blender's duplicate suffix (".315") can spell out a banned number by accident: pad every one of them
for coll in (D.objects, D.meshes, D.curves, D.materials, D.lights, D.collections):
    for b in list(coll):
        mt = re.search(r"\.(\d{3,})$", b.name)
        if mt:
            b.name = f"{b.name[:mt.start()]}_{int(mt.group(1)):05d}"
names = [b.name for coll in (D.objects, D.meshes, D.materials, D.collections, D.worlds, D.lights, D.images) for b in coll]
hits = sorted(set(m.group(0).lower() for m in BANNED.finditer("\n".join(names))))
print("PRIVACY", "FAIL " + str(hits) if hits else "OK")
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True)
print("DRESS_OK")
