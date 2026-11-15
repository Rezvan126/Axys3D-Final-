# Builds the film scene for the amber house: scene-v2.blend in, scene-v3.blend out (scene.blend is never touched).
#   blender --disable-autoexec -b assets-src/amber/scene-v2.blend -P tools/amber-cine-setup.py -- save
#   blender --disable-autoexec -b assets-src/amber/scene-v2.blend -P tools/amber-cine-setup.py -- preview <abs out> <shot> [frames]
#
# What it adds on top of v2:
#   - BlenderKit materials from the local BlenderKit cache (nothing is downloaded), mapped in world metres
#   - low golden hour sun placed so swaying maples across the street throw leaf shadow over the facade
#   - a thin haze volume, layered planting with real grass blades, a parked car with blank plates
# Scene units are about 0.467 m (a 2.1 m door is 4.5 units).
import bpy, sys, os, math, random, time
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "save"
SKIP = os.environ.get("AMBER_SKIP", "").split(",")

BK = os.path.join(os.path.expanduser("~"), "blenderkit_data")
M_PER_UNIT = 0.467
SUN_FROM_NORMAL = math.radians(40)
SUN_ELEVATION = math.radians(12.5)
FAR_CURB = 44.3
D = bpy.data
s = bpy.context.scene
USED = []          # BlenderKit assets actually used, for HANDOFF.md

# ------------------------------------------------------------------ helpers
def node(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n

def sun_vec(elev=SUN_ELEVATION, az=SUN_FROM_NORMAL):
    c = math.cos(elev)
    return Vector((math.cos(az) * c, math.sin(az) * c, math.sin(elev)))

def ground_z(x, y):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = s.ray_cast(dg, Vector((x, y, 300)), Vector((0, 0, -1)))
    return loc.z if hit else None

def bk_file(folder_prefix, kind="materials"):
    base = os.path.join(BK, kind)
    for d in sorted(os.listdir(base)):
        if d.startswith(folder_prefix):
            for f in os.listdir(os.path.join(base, d)):
                if f.endswith(".blend"):
                    return os.path.join(base, d, f), d.split("_")[-1]
    raise FileNotFoundError(folder_prefix)

def bk_material(folder_prefix, licence_hint=""):
    path, asset_id = bk_file(folder_prefix)
    with D.libraries.load(path, link=False) as (src, dst):
        dst.materials = list(src.materials)
    mats = [m for m in dst.materials if m is not None]
    m = mats[-1] if len(mats) > 1 else mats[0]
    lic = ""
    if m.asset_data:
        lic = getattr(m.asset_data, "license", "") or ""
    if not lic:
        try:
            lic = m["asset_data"]["license"]
        except Exception:
            lic = licence_hint
    USED.append((m.name, asset_id, lic or "royalty_free (BlenderKit free asset)"))
    print("AMBER bk material", m.name, asset_id, lic, flush=True)
    return m

def worldify(mat, metres_per_tile=1.0):
    """Drives every texture lookup from world position in metres (box projected), so the Revit meshes'
    arbitrary UVs no longer matter and every surface gets the asset's real world scale."""
    nt = mat.node_tree
    geo = node(nt, "ShaderNodeNewGeometry")
    sc = node(nt, "ShaderNodeVectorMath", operation="SCALE")
    sc.inputs["Scale"].default_value = M_PER_UNIT / metres_per_tile
    nt.links.new(geo.outputs["Position"], sc.inputs[0])
    src = sc.outputs[0]
    for l in list(nt.links):
        if l.from_node.type in ("TEX_COORD", "UVMAP") and l.to_socket.type == "VECTOR":
            to = l.to_socket
            nt.links.remove(l)
            nt.links.new(src, to)
    for n in nt.nodes:
        if n.type == "TEX_IMAGE":
            n.projection = "BOX"; n.projection_blend = 0.3
            if not n.inputs["Vector"].is_linked:
                nt.links.new(src, n.inputs["Vector"])
        if n.type in ("TEX_NOISE", "TEX_VORONOI", "TEX_MUSGRAVE", "TEX_WAVE") and not n.inputs["Vector"].is_linked:
            nt.links.new(src, n.inputs["Vector"])
    # displacement stays as bump: true displacement on Revit walls would tear
    mat.displacement_method = "BUMP"
    return mat

def principled_of(mat):
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)

def tint(mat, rgb, fac=1.0):
    """Multiplies the base colour (to set the paint colour of a white plaster asset, or a neighbour's tone)."""
    nt = mat.node_tree
    p = principled_of(mat)
    if p is None:
        return
    sock = p.inputs["Base Color"]
    mx = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mx.inputs[0].default_value = fac
    mx.inputs[7].default_value = (*rgb, 1.0)
    if sock.is_linked:
        nt.links.new(sock.links[0].from_socket, mx.inputs[6])
    else:
        mx.inputs[6].default_value = sock.default_value
    nt.links.new(mx.outputs[2], sock)

def replace_material(old_names, new):
    for o in D.objects:
        if o.type != "MESH":
            continue
        for sl in o.material_slots:
            if sl.material and sl.material.name in old_names:
                sl.material = new

# ------------------------------------------------------------------ light
def setup_light():
    w = s.world
    sky = next(n for n in w.node_tree.nodes if n.type == "TEX_SKY")
    sky.sun_elevation = SUN_ELEVATION
    sky.sun_rotation = math.pi / 2 - SUN_FROM_NORMAL
    sky.sun_size = math.radians(0.75)          # crisper leaf dapple than v2
    sky.sun_intensity = 1.0
    sky.air_density = 1.0; sky.aerosol_density = 1.2      # thicker air (tried 1.4 / 3.0) dimmed the low sun too much
    vs = s.view_settings
    vs.view_transform = "AgX"
    vs.look = "AgX - Medium High Contrast"
    vs.exposure = float(os.environ.get("AMBER_EXPOSURE", "-3.55"))
    c = s.cycles
    c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02
    c.use_denoising = True
    try: c.denoiser = "OPTIX"
    except Exception: pass
    c.volume_bounces = 0
    c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 3; c.transparent_max_bounces = 16
    s.render.use_persistent_data = True

def setup_gobo():
    """Leaf cookie: the maples across the street are 80+ units from the house, so their shadow arrives as one soft
    edge. A shadow-only plane of leaf clusters on the sun line, 22 units out from the facade, gives the dappled light
    a canopy just out of frame would give. The camera and reflections never see it; the leaf mask churns slowly
    (4D noise) like leaves moving in a breeze."""
    sv = sun_vec()
    centre = Vector((-14.5, 106.0, 28.5)) + sv * float(os.environ.get("AMBER_GOBO_DIST", "22"))
    w, h = 54.0, 36.0
    me = D.meshes.new("amber_leaf_cookie")
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    ob = D.objects.new("amber_leaf_cookie", me); s.collection.objects.link(ob)
    ob.location = centre
    ob.rotation_euler = sv.to_track_quat("Z", "Y").to_euler()
    for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
        setattr(ob, attr, False)
    ob.visible_shadow = True
    mat = D.materials.new("amber_leaf_cookie"); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    tc = node(nt, "ShaderNodeTexCoord")
    big = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")
    big.inputs["Scale"].default_value = 0.16; big.inputs["Detail"].default_value = 4.0
    big.inputs["Roughness"].default_value = 0.55; big.inputs["Distortion"].default_value = 0.6
    leaf = node(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="4D", feature="SMOOTH_F1")
    leaf.inputs["Scale"].default_value = 1.6; leaf.inputs["Randomness"].default_value = 1.0
    fine = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")
    fine.inputs["Scale"].default_value = 1.1; fine.inputs["Detail"].default_value = 8.0; fine.inputs["Roughness"].default_value = 0.7
    for n in (big, leaf, fine):
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    # clusters of foliage (big), broken into leaf sized holes (voronoi + fine noise)
    r1 = node(nt, "ShaderNodeMapRange"); r1.inputs["From Min"].default_value = 0.40; r1.inputs["From Max"].default_value = 0.52
    nt.links.new(big.outputs[0], r1.inputs["Value"])
    lv = node(nt, "ShaderNodeMath", operation="ADD")
    nt.links.new(leaf.outputs["Distance"], lv.inputs[0])
    fm = node(nt, "ShaderNodeMath", operation="MULTIPLY"); fm.inputs[1].default_value = 0.45
    nt.links.new(fine.outputs[0], fm.inputs[0]); nt.links.new(fm.outputs[0], lv.inputs[1])
    r2 = node(nt, "ShaderNodeMapRange"); r2.inputs["From Min"].default_value = 0.62; r2.inputs["From Max"].default_value = 0.70
    r2.inputs["To Min"].default_value = 1.0; r2.inputs["To Max"].default_value = 0.0
    nt.links.new(lv.outputs[0], r2.inputs["Value"])
    opaque = node(nt, "ShaderNodeMath", operation="MULTIPLY", use_clamp=True)
    nt.links.new(r1.outputs[0], opaque.inputs[0]); nt.links.new(r2.outputs[0], opaque.inputs[1])
    # fade the cookie out towards its edges so it never draws a straight shadow line
    sep = node(nt, "ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ex = node(nt, "ShaderNodeMath", operation="ABSOLUTE"); nt.links.new(sep.outputs["X"], ex.inputs[0])
    ey = node(nt, "ShaderNodeMath", operation="ABSOLUTE"); nt.links.new(sep.outputs["Y"], ey.inputs[0])
    fx = node(nt, "ShaderNodeMapRange"); fx.inputs["From Min"].default_value = w / 2 - 8; fx.inputs["From Max"].default_value = w / 2
    fx.inputs["To Min"].default_value = 1.0; fx.inputs["To Max"].default_value = 0.0
    nt.links.new(ex.outputs[0], fx.inputs["Value"])
    fy = node(nt, "ShaderNodeMapRange"); fy.inputs["From Min"].default_value = h / 2 - 6; fy.inputs["From Max"].default_value = h / 2
    fy.inputs["To Min"].default_value = 1.0; fy.inputs["To Max"].default_value = 0.0
    nt.links.new(ey.outputs[0], fy.inputs["Value"])
    e1 = node(nt, "ShaderNodeMath", operation="MULTIPLY"); nt.links.new(fx.outputs[0], e1.inputs[0]); nt.links.new(fy.outputs[0], e1.inputs[1])
    cov = node(nt, "ShaderNodeMath", operation="MULTIPLY", use_clamp=True)
    nt.links.new(opaque.outputs[0], cov.inputs[0]); nt.links.new(e1.outputs[0], cov.inputs[1])
    tr = node(nt, "ShaderNodeBsdfTransparent")
    df = node(nt, "ShaderNodeBsdfDiffuse"); df.inputs["Color"].default_value = (0.02, 0.03, 0.01, 1)
    mx = node(nt, "ShaderNodeMixShader")
    nt.links.new(cov.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(df.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    me.materials.append(mat)
    # breeze: the leaf pattern churns slowly and drifts a little
    for n, w0, w1 in ((big, 0.0, 0.35), (leaf, 0.0, 1.6), (fine, 0.0, 1.2)):
        sock = n.inputs["W"]
        sock.default_value = w0; sock.keyframe_insert("default_value", frame=1)
        sock.default_value = w1; sock.keyframe_insert("default_value", frame=240)
    act = nt.animation_data.action
    try:
        curves = list(act.fcurves)
    except Exception:
        curves = [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.extrapolation = "LINEAR"

def setup_comp():
    """Depth haze from the mist pass in the compositor. (A haze volume was tried first: across the ~500 units the
    low sun travels through it, it took more than half the sunlight off the house, filled the rooms with noise and
    pushed frames past 30 s. The mist pass gives the same falloff into warm air at no render cost.)"""
    vl = bpy.context.view_layer
    vl.use_pass_mist = True
    ms = s.world.mist_settings
    ms.start = float(os.environ.get("AMBER_MIST_START", "30")); ms.depth = float(os.environ.get("AMBER_MIST_DEPTH", "420")); ms.falloff = "QUADRATIC"
    ng = D.node_groups.new("amber_comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers"); rl.scene = s; rl.layer = vl.name
    out = ng.nodes.new("NodeGroupOutput")
    mul = ng.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.use_clamp = True
    mul.inputs[1].default_value = float(os.environ.get("AMBER_MIST", "0.5"))
    ng.links.new(rl.outputs["Mist"], mul.inputs[0])
    mix = ng.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    ng.links.new(mul.outputs[0], mix.inputs["Factor"])
    ng.links.new(rl.outputs["Image"], mix.inputs[6])
    mix.inputs[7].default_value = (3.4, 3.0, 2.45, 1.0)     # warm air, in scene light (exposure is applied after)
    ng.links.new(mix.outputs[2], out.inputs[0])
    s.compositing_node_group = ng
    s.render.use_compositing = True

def setup_haze_volume():
    """Thin haze over the whole street: depth falls back into warm air, the sun gets a little shaft and bloom.
    Built last, so the ground ray casts of the other steps do not hit it."""
    me = D.meshes.new("amber_haze")
    x0, x1, y0, y1, z0, z1 = -260, 420, -260, 460, 8, 140
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f)
    ob = D.objects.new("amber_haze", me); s.collection.objects.link(ob)
    mat = D.materials.new("amber_haze"); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    vol = node(nt, "ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = float(os.environ.get("AMBER_HAZE", "0.0016"))
    vol.inputs["Color"].default_value = (0.92, 0.88, 0.82, 1.0)
    vol.inputs["Anisotropy"].default_value = 0.55
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(mat)
    ob.visible_shadow = False      # the haze must not shade the sun itself

# ------------------------------------------------------------------ BlenderKit materials
def setup_materials():
    M = D.materials
    # plaster: fine stipple stucco, warmed slightly to a painted off white
    pl = worldify(bk_material("white-wall-frost_"), 0.9)
    tint(pl, (0.97, 0.95, 0.91))
    replace_material({"Plaster"}, pl)
    # large dark planes (low garden wall, steps, the slab edge): charcoal stucco, not metal
    dark_walls = ('Basic Wall Generic - 3"', 'Floor Concrete 10"', 'Monolithic Run 3/4" Nosing', 'Floor Concrete 6" Thick new [1792510]')
    ds = worldify(bk_material("dark-stucco-wall_"), 1.0)
    tint(ds, (0.55, 0.55, 0.56))
    for o in D.objects:
        if o.type == "MESH" and o.name.startswith(dark_walls) and "Thick new [1792510]" not in o.name:
            for sl in o.material_slots:
                if sl.material and sl.material.name in ("Black Metal", "Black Metal.001", "Metal black"):
                    sl.material = ds
    # black fascia, frames, railings, canopy: satin black metal, kept very dark so it reads as ink black with a sheen
    bm = worldify(bk_material("satin-black-meta_"), 1.0)
    tint(bm, (0.6, 0.6, 0.63))
    replace_material({"Black Metal", "Black Metal.001", "Metal black", "amber_neighbour_dark"}, bm)
    # glazing and garage panels stay on the v2 shaders: the BlenderKit architectural glass rendered speckled through
    # the haze and the BlenderKit frosted glass read as metal blinds (both tried in preview round 1)
    # street
    asph = worldify(bk_material("asphalt-tarmac-r_31"), 2.0)
    replace_material({"Asphalt Black", "Dark street or road asphalt"}, asph)
    walk = worldify(bk_material("concrete-tiles_37"), 1.2)
    replace_material({"Concrete pavement", "Dry concrete", "amber_kerb"}, walk)
    soil = worldify(bk_material("potting-soil_"), 0.8)
    replace_material({"amber_soil"}, soil)
    lawn = worldify(bk_material("green-grass-lawn_"), 1.5)
    tint(lawn, (0.78, 0.74, 0.55))
    replace_material({"Procedural Grass"}, lawn)
    # neighbours: grey stucco in two tones, so they read as real render but stay quieter than the white house
    for key, rgb in (("left", (0.62, 0.68, 0.74)), ("right", (0.86, 0.76, 0.64))):
        m = worldify(bk_material("stucco-grey-wall_"), 1.2)
        tint(m, rgb)
        replace_material({f"amber_paint_{key}"}, m)
        mt = worldify(bk_material("white-plaster_"), 1.0)
        tint(mt, (0.82, 0.80, 0.76))
        replace_material({f"amber_trim_{key}"}, mt)

# ------------------------------------------------------------------ trees across the street, on the sun line
def append_collection(path, name_hint=None):
    with D.libraries.load(path, link=False) as (src, dst):
        dst.collections = list(src.collections)
    cols = [c for c in dst.collections if c is not None]
    # the asset's own collection is the one with the most geometry (others are particle sources such as twigs)
    def weight(c):
        return sum(len(o.data.polygons) for o in c.all_objects if o.type == "MESH")
    return max(cols, key=weight), cols

def setup_trees():
    path, asset_id = bk_file("ahorn-tree_", "models")
    top, cols = append_collection(path)
    for c in cols:
        if c.name not in [x.name for x in s.collection.children_recursive]:
            pass
    holder = D.collections.new("amber_bk_src"); s.collection.children.link(holder)
    holder.hide_render = True; holder.hide_viewport = True
    for c in cols:
        holder.children.link(c)
    USED.append(("Ahorn tree (maple)", asset_id, "cc_zero"))
    # canopy height above the asset origin, in the asset's metres
    lo = 1e9; hi = -1e9
    for o in top.all_objects:
        if o.type == "MESH" and "leaf" in o.name.lower():
            for c in o.bound_box:
                z = (o.matrix_world @ Vector(c)).z
                lo = min(lo, z); hi = max(hi, z)
    if lo > hi:
        lo, hi = 3.0, 9.8
    canopy = (lo + hi) / 2
    print("AMBER maple canopy", round(lo, 2), round(hi, 2), flush=True)
    # remove v2's stamped street trees; keep its tree pits
    for n in ("amber_trees_street",):
        if n in D.objects:
            D.objects[n].hide_render = True; D.objects[n].hide_viewport = True
    coll = D.collections.new("amber_cine_trees"); s.collection.children.link(coll)
    sv = sun_vec()
    # two trees, each placed so the sun line from the facade passes through the EDGE of its canopy (a full canopy
    # puts the whole front in shade; the edge breaks the light into moving patches)
    side = Vector((-sv.y, sv.x, 0)).normalized()
    # offsets found with the coverage map in amber-cine-debug.py (about half the front in broken shade)
    edges = [float(v) for v in os.environ.get("AMBER_EDGES", "21,-23").split(",")]
    targets = [(-13.6, 102.5, 33.0, 0.0, edges[0]), (-15.8, 107.5, 27.8, 3.0, edges[1])][:len(edges)]
    rnd = random.Random(11)
    trees = []
    for i, (x, y, z, jit, off) in enumerate(targets):
        T = Vector((x, y, z))
        t = (FAR_CURB + 6.5 + jit - x) / sv.x
        R = T + sv * t + side * off
        gz = ground_z(R.x, R.y) or 30.0
        scale = (R.z - gz) / (canopy / M_PER_UNIT)
        scale = max(0.75, min(scale, 1.7))
        base = Vector((R.x, R.y, gz - 0.3))
        e = D.objects.new(f"amber_maple_{i}", None)
        e.instance_type = "COLLECTION"; e.instance_collection = top
        e.location = base
        e.scale = (scale / M_PER_UNIT,) * 3
        e.rotation_euler = (0, 0, rnd.uniform(0, 6.28))
        coll.objects.link(e)
        trees.append(e)
        print("AMBER maple", i, tuple(round(v, 1) for v in base), "scale", round(scale, 2), flush=True)
    # one more in the tree pit on the near pavement above the house (frames shots B and C from above)
    e = D.objects.new("amber_maple_pit", None)
    e.instance_type = "COLLECTION"; e.instance_collection = top
    # moved downhill into the near planting bed: its shadow falls away from the house and it screens the left neighbour
    e.location = (-7.4, 85.0, (ground_z(-7.4, 85.0) or 20.0) - 0.2); e.scale = (0.85 / M_PER_UNIT,) * 3
    e.rotation_euler = (0, 0, 2.1)
    coll.objects.link(e); trees.append(e)
    # wind: slow sway about the trunk base, different phase per tree
    for k, e in enumerate(trees):
        e.keyframe_insert("rotation_euler", frame=1)
        fcs = e.animation_data.action
        curves = []
        try:
            curves = list(fcs.fcurves)
        except Exception:
            for layer in fcs.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        curves.extend(bag.fcurves)
        for fc in curves:
            if fc.array_index in (0, 1):
                mod = fc.modifiers.new("NOISE")
                mod.scale = 46.0; mod.strength = 0.022; mod.phase = 13.0 * k + 5 * fc.array_index; mod.depth = 1
    return top

# ------------------------------------------------------------------ planting
def scatter_on(name, target, sources, density, scale_rng, seed, coll, hue_vary=True):
    """Geometry nodes scatter of a few source objects over one surface, random pick, turn and size."""
    ng = D.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes; L = ng.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    oi = N.new("GeometryNodeObjectInfo"); oi.transform_space = "RELATIVE"
    oi.inputs["Object"].default_value = target
    dist = N.new("GeometryNodeDistributePointsOnFaces"); dist.distribute_method = "RANDOM"
    dist.inputs["Density"].default_value = density; dist.inputs["Seed"].default_value = seed
    ci = N.new("GeometryNodeCollectionInfo")
    sc = D.collections.new(name + "_src")
    for o in sources:
        sc.objects.link(o)
    ci.inputs["Collection"].default_value = sc
    ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
    ci.transform_space = "ORIGINAL"
    iop = N.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    rv = N.new("FunctionNodeRandomValue"); rv.data_type = "INT"; rv.inputs["Min"].default_value = 0; rv.inputs["Max"].default_value = 100
    rr = N.new("FunctionNodeRandomValue"); rr.data_type = "FLOAT_VECTOR"
    rr.inputs["Min"].default_value = (-0.08, -0.08, 0.0); rr.inputs["Max"].default_value = (0.08, 0.08, 6.283)
    rs = N.new("FunctionNodeRandomValue"); rs.data_type = "FLOAT"
    rs.inputs[2].default_value = scale_rng[0]; rs.inputs[3].default_value = scale_rng[1]
    rs.inputs["Seed"].default_value = seed + 3
    L.new(oi.outputs["Geometry"], dist.inputs["Mesh"])
    L.new(dist.outputs["Points"], iop.inputs["Points"])
    L.new(ci.outputs[0], iop.inputs["Instance"])
    L.new(rv.outputs[2], iop.inputs["Instance Index"])
    L.new(rr.outputs[0], iop.inputs["Rotation"])
    L.new(rs.outputs[1], iop.inputs["Scale"])
    L.new(iop.outputs[0], go.inputs[0])
    holder = D.meshes.new(name); ob = D.objects.new(name, holder); coll.objects.link(ob)
    mod = ob.modifiers.new("scatter", "NODES"); mod.node_group = ng
    return ob

def strip_mesh(name, pts, coll, mat=None):
    """A flat planting bed from a polygon outline [(x, y)], dropped onto the ground under it."""
    verts = [(x, y, (ground_z(x, y) or 22.0) + 0.05) for x, y in pts]
    me = D.meshes.new(name); me.from_pydata(verts, [], [tuple(range(len(verts)))]); me.update()
    ob = D.objects.new(name, me); coll.objects.link(ob)
    if mat: me.materials.append(mat)
    return ob

def vary_leaf_colour(mat, amount=0.25):
    """Per instance colour shift in a foliage material so scattered copies never look stamped."""
    nt = mat.node_tree
    for p in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        sock = p.inputs["Base Color"]
        if not sock.is_linked:
            continue
        src = sock.links[0].from_socket
        oi = node(nt, "ShaderNodeObjectInfo")
        hs = node(nt, "ShaderNodeHueSaturation")
        mr = node(nt, "ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.5 - amount * 0.12; mr.inputs["To Max"].default_value = 0.5 + amount * 0.08
        nt.links.new(oi.outputs["Random"], mr.inputs["Value"])
        nt.links.new(mr.outputs[0], hs.inputs["Hue"])
        mv = node(nt, "ShaderNodeMapRange"); mv.inputs["To Min"].default_value = 1 - amount; mv.inputs["To Max"].default_value = 1 + amount * 0.6
        nt.links.new(oi.outputs["Random"], mv.inputs["Value"])
        nt.links.new(mv.outputs[0], hs.inputs["Value"])
        nt.links.new(src, hs.inputs["Color"]); nt.links.new(hs.outputs[0], sock)

def setup_planting():
    coll = D.collections.new("amber_cine_planting"); s.collection.children.link(coll)
    G = {n: D.objects[n] for n in ("GS Grass 01", "GS Grass 02", "GS Grass tiny 01", "GS type B small", "GS Forest clover 01",
                                    "GS Grass Wild Clump 01", "GS Grass Wild Clump 02", "GS Grass Wild Clump Dry 01", "GS Dryland clump low")}
    for o in G.values():
        print("AMBER gs", o.name, tuple(round(v, 2) for v in o.dimensions), flush=True)
        for sl in o.material_slots:
            if sl.material:
                vary_leaf_colour(sl.material, 0.22)
    for n in ("Cotoneáster leaf 1", "Cotoneáster leaf 2", "Cotoneáster leaf 3"):
        vary_leaf_colour(D.materials[n], 0.3)
    lawn_src = [G["GS Grass 01"], G["GS Grass 02"], G["GS Grass tiny 01"], G["GS type B small"], G["GS Forest clover 01"]]
    tall_src = [G["GS Grass Wild Clump 01"], G["GS Grass Wild Clump 02"], G["GS Grass Wild Clump Dry 01"], G["GS Dryland clump low"]]
    # the GS assets are modelled in metres: bring them to scene units
    k = 1.0 / M_PER_UNIT
    # 1. real blades on the house's own lawn strips
    for i, n in enumerate(("Toposolid Toposolid 1 [1794106]", "Toposolid Toposolid 1 [1794097]", 'Basic Wall Generic - 3" [5021574].001')):
        if n in D.objects:
            scatter_on(f"amber_lawn_{i}", D.objects[n], lawn_src, 26.0, (0.8 * k, 1.3 * k), 31 + i, coll)
    # 2. a planted verge on the near pavement edge, below the house and the left neighbour:
    #    ornamental grass clumps and low shrubs that pass close to the lens in shots B and C
    bed = strip_mesh("amber_bed_near", [(-7.8, 84.0), (-6.4, 84.0), (-6.9, 100.2), (-8.4, 100.2)], coll, D.materials.get("Potting soil"))
    scatter_on("amber_bed_tall", bed, tall_src, 0.8, (1.4 * k, 2.4 * k), 41, coll)
    scatter_on("amber_bed_low", bed, lawn_src, 14.0, (0.8 * k, 1.2 * k), 43, coll)
    # 3. the far verge (camera side for A and D): longer meadow grass under the hedge row
    far = strip_mesh("amber_bed_far", [(FAR_CURB + 4.3, 84.0), (FAR_CURB + 11.0, 84.0), (FAR_CURB + 11.0, 128.0), (FAR_CURB + 4.3, 128.0)], coll, D.materials.get("Potting soil"))
    scatter_on("amber_far_tall", far, tall_src, 0.9, (2.0 * k, 3.2 * k), 51, coll)
    scatter_on("amber_far_low", far, lawn_src, 8.0, (0.9 * k, 1.4 * k), 53, coll)
    # 3b. two grass clumps at the foot of the entry steps: the near focus plane of shot C
    for i, (x, y, sc, rz) in enumerate(((-9.45, 101.25, 2.4, 0.4), (-9.6, 100.7, 2.0, 2.2), (-9.3, 101.6, 1.6, 4.0))):
        c = G["GS Grass Wild Clump 01" if i != 1 else "GS Grass Wild Clump Dry 01"].copy(); coll.objects.link(c)
        c.location = (x, y, (ground_z(x, y) or 22.0) - 0.05); c.rotation_euler = (0, 0, rz); c.scale = (sc * k,) * 3
    # 4. shrubs layered in front of the garden wall and by the near bed (instances of the scene's cotoneaster)
    shrub = D.objects["Cotoneáster.002"]
    rnd = random.Random(5)
    for i, (x, y, sc, rz) in enumerate(((-7.3, 86.5, 0.7, 1.4), (-7.6, 92.0, 0.55, 1.7), (-7.2, 96.8, 0.65, 1.5), (-10.4, 116.8, 0.6, 1.6))):
        c = shrub.copy(); coll.objects.link(c)
        c.location = (x, y, (ground_z(x, y) or 22.0) - 0.2)
        c.rotation_euler = (0, 0.05, rz + rnd.uniform(-0.2, 0.2)); c.scale = (sc, sc * 1.1, sc * rnd.uniform(0.9, 1.2))
    return coll

# ------------------------------------------------------------------ parked car
def setup_car():
    path, asset_id = bk_file("volkswagen-t-roc_0a", "models")
    top, cols = append_collection(path)
    holder = D.collections.get("amber_bk_src")
    for c in cols:
        holder.children.link(c)
    USED.append(("Volkswagen T-Roc R-Line 2026", asset_id, "royalty_free (BlenderKit)"))
    # privacy: no plate text anywhere
    for o in top.all_objects:
        for sl in getattr(o, "material_slots", []):
            if sl.material and "plate" in sl.material.name.lower():
                blank = D.materials.new("amber_blank_plate"); blank.use_nodes = True
                p = principled_of(blank); p.inputs["Base Color"].default_value = (0.75, 0.75, 0.72, 1); p.inputs["Roughness"].default_value = 0.5
                sl.material = blank
    # paint: a quiet dark grey so it never pulls the eye from the house
    e = D.objects.new("amber_car", None); e.instance_type = "COLLECTION"; e.instance_collection = top
    y = 78.0; x = FAR_CURB - 4.2
    e.location = (x, y, (ground_z(x, y) or 15.0)); e.scale = (1 / M_PER_UNIT,) * 3
    e.rotation_euler = (0.155, 0, math.pi)   # nose uphill (+y) along the slope
    s.collection.objects.link(e)
    return e

def setup_misc():
    # the interior lights read too hot against the darker exposure of the film: keep them warm and low
    for o in D.objects:
        if o.type == "LIGHT" and o.name.startswith("amber_sconce"):
            o.data.energy *= 0.7

def apply():
    for step in (setup_light, setup_materials, setup_trees, setup_planting, setup_car, setup_misc, setup_gobo, setup_comp):
        if step.__name__ in SKIP:
            continue
        t = time.time()
        step()
        print("AMBER", step.__name__, round(time.time() - t, 1), "s", flush=True)
    s["amber_bk_used"] = "\n".join(" | ".join(u) for u in USED)
    print("AMBER BK USED\n" + s["amber_bk_used"], flush=True)

if __name__ == "__main__":
    apply()
    if MODE == "save":
        target = os.path.join(ROOT, "assets-src", "amber", "scene-v3.blend")
        assert target.endswith("scene-v3.blend")
        bpy.ops.wm.save_as_mainfile(filepath=target, compress=True, copy=False)
        print("AMBER_SAVED", target, flush=True)
    elif MODE == "preview":
        import importlib.util
        spec = importlib.util.spec_from_file_location("cine", os.path.join(HERE, "amber-cine-shots.py"))
        cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
        cs.render_shot(argv[1], argv[2], preview=True, frames=[int(f) for f in argv[3].split(",")] if len(argv) > 3 else None)
