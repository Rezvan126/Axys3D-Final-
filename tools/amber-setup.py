# Turns the owner's amber scene (Workbench, flat light, plastic shaders) into a Cycles golden hour scene.
# Never writes scene.blend. Either saves the improved scene or renders small tests straight from memory.
#   blender --disable-autoexec -b assets-src/amber/scene.blend -P tools/amber-setup.py -- save
#   blender --disable-autoexec -b assets-src/amber/scene.blend -P tools/amber-setup.py -- test <abs out folder> [view ...]
#
# Layout facts (scene units, about 0.46 m each): the street runs along Y and climbs towards +Y,
# the hero house faces +X and sits between y 96.5 and 115, the hill and trees are behind it at -X.
import bpy, sys, os, math, random, time
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "save"

SUN_FROM_NORMAL = math.radians(44)   # sun direction, measured from the facade normal (+X) towards uphill (+Y)
SUN_ELEVATION = math.radians(17.0)
EXPOSURE = float(os.environ.get("AMBER_EXPOSURE", "-3.7"))
SKIP = os.environ.get("AMBER_SKIP", "").split(",")     # fault finding only: leave parts of the set out
HERO_COLL = "Wild White Flower Patch"   # the Revit house landed in a collection with this left-over name

s = bpy.context.scene
D = bpy.data

# ------------------------------------------------------------------ helpers
def node(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n

def link(nt, a, b):
    nt.links.new(a, b)

def clear(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    return nt, out

def world_pos(nt, scale=(1, 1, 1)):
    g = node(nt, "ShaderNodeNewGeometry")
    m = node(nt, "ShaderNodeMapping")
    m.inputs["Scale"].default_value = scale
    link(nt, g.outputs["Position"], m.inputs["Vector"])
    return m.outputs["Vector"]

def noise_tex(nt, vec, scale, detail=4.0, rough=0.55, distortion=0.0):
    n = node(nt, "ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = distortion
    link(nt, vec, n.inputs["Vector"])
    return n.outputs[0]

def remap(nt, val, lo, hi, a=0.0, b=1.0):
    m = node(nt, "ShaderNodeMapRange")
    m.inputs["From Min"].default_value = lo; m.inputs["From Max"].default_value = hi
    m.inputs["To Min"].default_value = a; m.inputs["To Max"].default_value = b
    link(nt, val, m.inputs["Value"])
    return m.outputs["Result"]

def mixc(nt, fac, a, b, mode="MIX"):
    m = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type=mode)
    for sock, v in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
        if hasattr(v, "is_linked"):
            link(nt, v, sock)
        elif isinstance(v, (int, float)):
            sock.default_value = v
        else:
            sock.default_value = (*v, 1.0) if len(v) == 3 else v
    return m.outputs[2]

def math_node(nt, op, a, b=None):
    m = node(nt, "ShaderNodeMath", operation=op)
    for sock, v in ((m.inputs[0], a), (m.inputs[1], b)):
        if v is None:
            continue
        if hasattr(v, "is_linked"):
            link(nt, v, sock)
        else:
            sock.default_value = v
    return m.outputs[0]

def bump(nt, height, strength, distance=0.05, normal=None):
    b = node(nt, "ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    link(nt, height, b.inputs["Height"])
    if normal is not None:
        link(nt, normal, b.inputs["Normal"])
    return b.outputs["Normal"]

def principled(nt, out, base=None, rough=None, normal=None, **vals):
    p = node(nt, "ShaderNodeBsdfPrincipled")
    for name, v in (("Base Color", base), ("Roughness", rough), ("Normal", normal)):
        if v is None:
            continue
        if hasattr(v, "is_linked"):
            link(nt, v, p.inputs[name])
        elif isinstance(v, (int, float)):
            p.inputs[name].default_value = v
        else:
            p.inputs[name].default_value = (*v, 1.0)
    for k, v in vals.items():
        p.inputs[k].default_value = v
    link(nt, p.outputs[0], out.inputs["Surface"])
    return p

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t

# ------------------------------------------------------------------ street profile
ROAD_PTS = [(46.5, 13.2), (96.9, 21.1), (117.3, 24.4), (159.4, 34.1)]
def street_z(y):
    if y <= ROAD_PTS[0][0]:
        return ROAD_PTS[0][1] + (y - ROAD_PTS[0][0]) * 0.155
    if y >= ROAD_PTS[-1][0]:
        return ROAD_PTS[-1][1] + (y - ROAD_PTS[-1][0]) * 0.15
    for (y0, z0), (y1, z1) in zip(ROAD_PTS, ROAD_PTS[1:]):
        if y0 <= y <= y1:
            return lerp(z0, z1, (y - y0) / (y1 - y0))

CURB_PTS = [(96.9, -5.3), (115.1, -10.9), (158.3, -18.0), (200.0, -22.0)]
def curb_x(y):
    if y <= CURB_PTS[0][0]:
        return CURB_PTS[0][1]
    if y >= CURB_PTS[-1][0]:
        return CURB_PTS[-1][1]
    for (y0, x0), (y1, x1) in zip(CURB_PTS, CURB_PTS[1:]):
        if y0 <= y <= y1:
            return lerp(x0, x1, (y - y0) / (y1 - y0))

FAR_CURB = 44.3

def terrain_z(x, y):
    sz = street_z(y)
    n = noise.noise(Vector((x * 0.02, y * 0.02, 0.3))) * 2.2 + noise.noise(Vector((x * 0.07, y * 0.07, 1.7))) * 0.7
    if x > FAR_CURB + 4:
        d = x - FAR_CURB - 4
        return sz - 0.45 - 0.2 * d + n * smooth(d / 40)
    base = sz - 0.8
    if x > -36:
        return base
    hill_line = 22.5 + 0.045 * y - 2.5
    w = smooth((y - 132) / 40) if y > 132 else (smooth((-40 - y) / 40) if y < -40 else 0.0)
    foot = lerp(hill_line, base + 1.0, w)
    b = lerp(base, foot, smooth((-36 - x) / 10))
    rise = 34 * smooth((-36 - x) / 62) + max(0.0, -98 - x) * 0.06
    return b + rise + n * smooth((-36 - x) / 30)

# ------------------------------------------------------------------ render settings
def setup_render():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == kind
                break
        except Exception:
            continue
    s.render.engine = "CYCLES"
    c = s.cycles
    c.device = "GPU"
    c.samples = 220
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.012
    c.use_denoising = True
    try:
        c.denoiser = "OPTIX"
    except Exception:
        pass
    c.max_bounces = 10
    c.diffuse_bounces = 4
    c.glossy_bounces = 4
    c.transmission_bounces = 8
    c.transparent_max_bounces = 24
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 8.0
    c.film_exposure = 1.0
    s.render.film_transparent = False
    s.render.use_motion_blur = False
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 2400, 1350, 100
    s.render.fps = 24
    vs = s.view_settings
    try:
        vs.view_transform = "AgX"
        vs.look = "AgX - Medium High Contrast"
    except Exception as e:
        print("AMBER view transform fallback", e)
        vs.view_transform = "Filmic"; vs.look = "Medium High Contrast"
    vs.exposure = EXPOSURE
    vs.gamma = 1.0
    s.render.image_settings.file_format = "JPEG"
    s.render.image_settings.quality = 95
    # nothing that could carry a name into the output
    s.render.use_stamp = False

# ------------------------------------------------------------------ visibility
def setup_visibility():
    for c in D.collections:
        if c.hide_render and c.name in ("A tree", "Cotoneáster", "scene"):
            c.hide_render = False
    hero = D.collections[HERO_COLL]
    centre = Vector((-20, 105, 30))
    for o in s.objects:
        # stray pieces the export left hundreds of units away from the site
        # (Revit origins are far from the geometry, so judge by the bounding box, not the origin)
        if o.type == "MESH" and o.name not in hero.objects:
            continue
        if o.type == "MESH":
            bc = sum((o.matrix_world @ Vector(c) for c in o.bound_box), Vector()) / 8
            if (bc - centre).length > 250:
                o.hide_render = True
    # a zero area duplicate and an empty road strip
    for name in ("ROAD.001",):
        if name in D.objects:
            D.objects[name].hide_render = True
    # the blackout curtain drawn right across the square upper window rendered as a blank white panel
    for o in D.objects:
        if o.name.startswith("Grey Blackout Curtain") and abs(o.matrix_world.translation.y - 111.1) < 1.5:
            o.hide_render = True

# ------------------------------------------------------------------ world
def sun_vector():
    ch = math.cos(SUN_ELEVATION)
    return Vector((math.cos(SUN_FROM_NORMAL) * ch, math.sin(SUN_FROM_NORMAL) * ch, math.sin(SUN_ELEVATION)))

def setup_world():
    w = D.worlds.new("amber_golden_hour")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld")
    sky = node(nt, "ShaderNodeTexSky")
    try:
        sky.sky_type = "MULTIPLE_SCATTERING"
    except Exception:
        sky.sky_type = "NISHITA"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.2)          # a slightly larger disc: softer shadow edges
    sky.sun_intensity = 0.6                    # a hazier sun: the sky fills the shadows more
    sky.sun_elevation = SUN_ELEVATION
    sky.sun_rotation = math.pi / 2 - SUN_FROM_NORMAL
    sky.altitude = 120
    sky.air_density = 1.25
    sky.aerosol_density = 2.2
    sky.ozone_density = 1.6
    # thin high cloud, only where the camera looks: stretched noise, brightest towards the sun
    tc = node(nt, "ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 4.5)
    mp.inputs["Rotation"].default_value = (0.0, 0.0, 0.6)
    link(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    cl = noise_tex(nt, mp.outputs["Vector"], 2.6, detail=7.0, rough=0.62, distortion=0.35)
    cl = remap(nt, cl, 0.52, 0.78, 0.0, 1.0)
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, tc.outputs["Generated"], sep.inputs[0])
    horizon = remap(nt, sep.outputs["Z"], 0.02, 0.22, 0.0, 1.0)     # fade the cloud out at the horizon
    cl = math_node(nt, "MULTIPLY", cl, horizon)
    cl = math_node(nt, "MULTIPLY", cl, 0.5)
    tint = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="ADD")
    link(nt, cl, tint.inputs[0])
    link(nt, sky.outputs[0], tint.inputs[6])
    tint.inputs[7].default_value = (0.55, 0.42, 0.36, 1.0)
    lp = node(nt, "ShaderNodeLightPath")
    pick = node(nt, "ShaderNodeMix", data_type="RGBA")
    link(nt, lp.outputs["Is Camera Ray"], pick.inputs[0])
    link(nt, sky.outputs[0], pick.inputs[6])
    link(nt, tint.outputs[2], pick.inputs[7])
    bg = node(nt, "ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    link(nt, pick.outputs[2], bg.inputs["Color"])
    link(nt, bg.outputs[0], out.inputs["Surface"])
    s.world = w
    try:
        w.cycles_visibility.camera = True
    except Exception:
        pass

# ------------------------------------------------------------------ materials
def mat_plaster(mat, tint=(0.80, 0.785, 0.76), grain=1.0):
    """Painted stucco: off white, fine grain bump, a little trowel waviness, faint weather streaks."""
    nt, out = clear(mat)
    pos = world_pos(nt)
    fine = noise_tex(nt, pos, 42.0, detail=6.0, rough=0.7)
    mid = noise_tex(nt, pos, 9.0, detail=3.0, rough=0.5)
    wide = noise_tex(nt, pos, 0.55, detail=3.0, rough=0.5)
    streak = noise_tex(nt, world_pos(nt, (2.2, 2.2, 0.14)), 3.0, detail=4.0, rough=0.6)
    col = mixc(nt, remap(nt, wide, 0.3, 0.7, 0.0, 0.28), tint, tuple(c * 0.93 for c in tint))
    col = mixc(nt, remap(nt, streak, 0.45, 0.8, 0.0, 0.16), col, tuple(c * 0.86 for c in tint))
    col = mixc(nt, remap(nt, fine, 0.3, 0.75, 0.0, 0.10), col, tuple(c * 0.9 for c in tint))
    rough = remap(nt, mid, 0.25, 0.75, 0.72, 0.9)
    trowel = noise_tex(nt, world_pos(nt, (1.0, 1.0, 2.2)), 3.2, detail=3.0, rough=0.55, distortion=0.9)
    h = math_node(nt, "ADD", math_node(nt, "MULTIPLY", fine, 1.0), math_node(nt, "MULTIPLY", mid, 0.8))
    nrm = bump(nt, h, 0.34 * grain, 0.035)
    nrm = bump(nt, trowel, 0.06 * grain, 0.12, nrm)
    nrm = bump(nt, wide, 0.05, 0.4, nrm)
    principled(nt, out, col, rough, nrm)

def mat_black_metal(mat):
    """Powder coated black aluminium: dark, satin, a thin clear coat for the edge sheen."""
    nt, out = clear(mat)
    pos = world_pos(nt)
    n = noise_tex(nt, pos, 14.0, detail=4.0, rough=0.6)
    wide = noise_tex(nt, pos, 1.3, detail=2.0)
    col = mixc(nt, remap(nt, wide, 0.3, 0.7, 0.0, 1.0), (0.008, 0.008, 0.009), (0.014, 0.014, 0.014))
    rough = remap(nt, n, 0.2, 0.8, 0.58, 0.70)
    nrm = bump(nt, n, 0.035, 0.02)
    p = principled(nt, out, col, rough, nrm)
    p.inputs["Metallic"].default_value = 0.0
    p.inputs["Specular IOR Level"].default_value = 0.3     # satin, not gloss: low sun on gloss black reads as brown

def mat_glass(mat, tint=(0.90, 0.95, 0.93), reflect=2.0):
    """Thin architectural glazing for single plane panes: clear to look through, mirror like at glancing angles.
    Light passes straight through, so rooms behind are lit by the sun and by their own lamps."""
    nt, out = clear(mat)
    fr = node(nt, "ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.52
    fac = node(nt, "ShaderNodeMath", operation="MULTIPLY", use_clamp=True)
    link(nt, fr.outputs[0], fac.inputs[0]); fac.inputs[1].default_value = reflect
    tr = node(nt, "ShaderNodeBsdfTransparent"); tr.inputs[0].default_value = (*tint, 1.0)
    gl = node(nt, "ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.015
    gl.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    mx = node(nt, "ShaderNodeMixShader")
    link(nt, fac.outputs[0], mx.inputs[0]); link(nt, tr.outputs[0], mx.inputs[1]); link(nt, gl.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], out.inputs["Surface"])

def mat_frosted(mat):
    """Frosted garage panels: milky, lets the garage light glow through, soft reflection of the sky."""
    nt, out = clear(mat)
    pos = world_pos(nt)
    n = noise_tex(nt, pos, 3.0, detail=2.0)
    rough = remap(nt, n, 0.3, 0.7, 0.28, 0.36)
    tl = node(nt, "ShaderNodeBsdfTranslucent"); tl.inputs["Color"].default_value = (0.80, 0.86, 0.86, 1.0)
    df = node(nt, "ShaderNodeBsdfDiffuse"); df.inputs["Color"].default_value = (0.62, 0.68, 0.69, 1.0)
    m1 = node(nt, "ShaderNodeMixShader"); m1.inputs[0].default_value = 0.45
    link(nt, tl.outputs[0], m1.inputs[1]); link(nt, df.outputs[0], m1.inputs[2])
    gl = node(nt, "ShaderNodeBsdfGlossy"); link(nt, rough, gl.inputs["Roughness"])
    fr = node(nt, "ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.5
    fac = node(nt, "ShaderNodeMath", operation="MULTIPLY", use_clamp=True)
    link(nt, fr.outputs[0], fac.inputs[0]); fac.inputs[1].default_value = 1.6
    m2 = node(nt, "ShaderNodeMixShader")
    link(nt, fac.outputs[0], m2.inputs[0]); link(nt, m1.outputs[0], m2.inputs[1]); link(nt, gl.outputs[0], m2.inputs[2])
    link(nt, m2.outputs[0], out.inputs["Surface"])

def mat_asphalt(mat, dark=1.0):
    """Asphalt in world coordinates so the added street lengths join without a seam:
    aggregate speckle, patch repairs, drier and damper areas with their own roughness."""
    nt, out = clear(mat)
    pos = world_pos(nt)
    speck = noise_tex(nt, pos, 55.0, detail=5.0, rough=0.75)
    grit = noise_tex(nt, pos, 14.0, detail=4.0, rough=0.6)
    wide = noise_tex(nt, pos, 0.11, detail=4.0, rough=0.6, distortion=0.6)
    damp = noise_tex(nt, world_pos(nt, (1.0, 0.45, 1.0)), 0.085, detail=5.0, rough=0.62, distortion=1.2)
    damp = remap(nt, damp, 0.60, 0.72, 0.0, 1.0)
    a = tuple(c * dark for c in (0.095, 0.092, 0.090)); b = tuple(c * dark for c in (0.155, 0.150, 0.142))
    col = mixc(nt, remap(nt, wide, 0.3, 0.72, 0.0, 1.0), a, b)
    col = mixc(nt, remap(nt, speck, 0.62, 0.8, 0.0, 0.5), col, tuple(c * dark for c in (0.27, 0.26, 0.25)))
    col = mixc(nt, math_node(nt, "MULTIPLY", damp, 0.55), col, tuple(c * dark for c in (0.050, 0.050, 0.052)))
    rough = math_node(nt, "SUBTRACT", remap(nt, grit, 0.2, 0.8, 0.62, 0.86), math_node(nt, "MULTIPLY", damp, 0.3))
    h = math_node(nt, "ADD", speck, math_node(nt, "MULTIPLY", grit, 0.7))
    flat = math_node(nt, "SUBTRACT", 1.0, math_node(nt, "MULTIPLY", damp, 0.8))
    nrm = bump(nt, math_node(nt, "MULTIPLY", h, flat), 0.5, 0.02)
    principled(nt, out, col, rough, nrm)

def mat_concrete(mat, joint=4.2, tint=(0.46, 0.44, 0.41)):
    """Broom finished pavement with control joints across the walk and stains."""
    nt, out = clear(mat)
    pos = world_pos(nt)
    fine = noise_tex(nt, pos, 60.0, detail=4.0, rough=0.7)
    stain = noise_tex(nt, pos, 0.5, detail=5.0, rough=0.65, distortion=0.5)
    slab = noise_tex(nt, world_pos(nt, (0.0, 1.0 / joint, 0.0)), 1.0, detail=0.0)   # a different tone per slab
    g = node(nt, "ShaderNodeNewGeometry")
    sep = node(nt, "ShaderNodeSeparateXYZ"); link(nt, g.outputs["Position"], sep.inputs[0])
    fy = math_node(nt, "FRACT", math_node(nt, "DIVIDE", sep.outputs["Y"], joint))
    line = math_node(nt, "ABSOLUTE", math_node(nt, "SUBTRACT", fy, 0.5))
    line = remap(nt, line, 0.0, 0.012, 1.0, 0.0)                      # 1 on the joint
    col = mixc(nt, remap(nt, stain, 0.3, 0.75, 0.0, 0.5), tint, tuple(c * 0.72 for c in tint))
    col = mixc(nt, remap(nt, fine, 0.3, 0.7, 0.0, 0.18), col, tuple(c * 1.25 for c in tint))
    col = mixc(nt, line, col, (0.06, 0.06, 0.06))
    rough = remap(nt, stain, 0.2, 0.8, 0.78, 0.94)
    h = math_node(nt, "SUBTRACT", math_node(nt, "MULTIPLY", fine, 0.6), math_node(nt, "MULTIPLY", line, 3.0))
    nrm = bump(nt, h, 0.4, 0.03)
    principled(nt, out, col, rough, nrm)

def mat_paint(mat, tint, rough=0.7, grain=0.5):
    """Plain painted render for the neighbours: enough surface to not look unfinished, quiet enough to stay background."""
    mat_plaster(mat, tint, grain)

def mat_ground(mat):
    """Hillside and verge ground under the grass: dry golden grass tones, not lawn green."""
    nt, out = clear(mat)
    pos = world_pos(nt)
    wide = noise_tex(nt, pos, 0.045, detail=5.0, rough=0.6, distortion=0.8)
    mid = noise_tex(nt, pos, 0.6, detail=5.0, rough=0.7)
    fine = noise_tex(nt, pos, 18.0, detail=5.0, rough=0.75)
    col = mixc(nt, remap(nt, wide, 0.3, 0.7, 0.0, 1.0), (0.085, 0.105, 0.035), (0.17, 0.15, 0.06))
    col = mixc(nt, remap(nt, mid, 0.35, 0.75, 0.0, 0.6), col, (0.05, 0.07, 0.025))
    col = mixc(nt, remap(nt, fine, 0.4, 0.8, 0.0, 0.35), col, (0.20, 0.18, 0.09))
    h = math_node(nt, "ADD", fine, math_node(nt, "MULTIPLY", mid, 2.0))
    principled(nt, out, col, 0.92, bump(nt, h, 0.9, 0.25))

def tame_green(mat, sat=0.72, val=0.78, hue=0.488, vary=0.0):
    """Pulls an existing foliage or grass material away from toy green: less saturation, darker, a touch towards olive.
    With vary > 0 every scattered instance gets its own slight shift."""
    nt = mat.node_tree
    if not nt:
        return False
    done = False
    for p in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        sock = p.inputs["Base Color"]
        if not sock.is_linked:
            continue
        src = sock.links[0].from_socket
        hs = node(nt, "ShaderNodeHueSaturation")
        hs.inputs["Hue"].default_value = hue
        hs.inputs["Saturation"].default_value = sat
        hs.inputs["Value"].default_value = val
        link(nt, src, hs.inputs["Color"])
        res = hs.outputs[0]
        if vary:
            oi = node(nt, "ShaderNodeObjectInfo")
            dry = mixc(nt, remap(nt, oi.outputs["Random"], 0.0, 1.0, 0.0, vary), res, (0.21, 0.17, 0.07))
            res = dry
        link(nt, res, sock)
        if p.inputs["Metallic"].default_value > 0 and not p.inputs["Metallic"].is_linked:
            p.inputs["Metallic"].default_value = 0.0
        done = True
    return done

def setup_materials():
    M = D.materials
    mat_plaster(M["Plaster"])
    for n in ("Black Metal", "Black Metal.001", "Metal black"):
        mat_black_metal(M[n])
    mat_glass(M["Glass.002"])
    mat_frosted(M["Procedural frosted glass"])
    mat_asphalt(M["Asphalt Black"])
    mat_asphalt(M["Dark street or road asphalt"], dark=0.8)
    mat_concrete(M["Concrete pavement"])
    mat_concrete(M["Dry concrete"], joint=6.0, tint=(0.40, 0.385, 0.36))
    # white vertical siding at the entry was partly metallic, which reads as plastic
    wp = M["Wood 45 White Wall Panelling"]
    for p in [n for n in wp.node_tree.nodes if n.type == "BSDF_PRINCIPLED"]:
        p.inputs["Metallic"].default_value = 0.0
    # the lace panels were opaque white sheets that blew out in the sun: let the rooms show through them
    lace = M["Curtain-Lace"]
    lo = next(n for n in lace.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    src = lo.inputs["Surface"].links[0].from_socket
    tr = node(lace.node_tree, "ShaderNodeBsdfTransparent")
    mx = node(lace.node_tree, "ShaderNodeMixShader"); mx.inputs[0].default_value = 0.42
    link(lace.node_tree, tr.outputs[0], mx.inputs[1]); link(lace.node_tree, src, mx.inputs[2])
    link(lace.node_tree, mx.outputs[0], lo.inputs["Surface"])
    # grass and planting
    tame_green(M["Grass"], sat=0.62, val=0.72, hue=0.478)
    for n in ("Default", "Default_1"):
        tame_green(M[n], sat=0.7, val=0.9, hue=0.474, vary=0.55)
    for n in ("Cotoneáster leaf 1", "Cotoneáster leaf 2", "Cotoneáster leaf 3", "Cotoneáster fake bush"):
        tame_green(M[n], sat=0.8, val=0.8, hue=0.49)
    tame_green(M["1-1.001"], sat=0.85, val=1.0, hue=0.492)
    # neighbours: the flat grey placeholders become quiet painted render in two muted colours, so the white
    # house between them stands out and nothing in frame looks unfinished
    def plain(m):
        if m is None:
            return 0.28
        if not m.name.startswith("Material.0") or not m.node_tree:
            return None
        p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if p is None or p.inputs["Base Color"].is_linked:
            return None
        return max(tuple(p.inputs["Base Color"].default_value)[:3])
    dark = M.new("amber_neighbour_dark"); mat_black_metal(dark)
    for cname, body, trim in (("Left Neighbour", (0.27, 0.30, 0.32), (0.56, 0.55, 0.52)), ("Right Neighbour", (0.40, 0.35, 0.29), (0.58, 0.56, 0.52))):
        mb = M.new("amber_paint_" + cname.split()[0].lower()); mat_paint(mb, body)
        mt = M.new("amber_trim_" + cname.split()[0].lower()); mat_paint(mt, trim, grain=0.3)
        for o in D.collections[cname].all_objects:
            if o.type != "MESH":
                continue
            if not o.material_slots:
                o.data.materials.append(mt if "frame" in o.name.lower() else mb)
                continue
            for sl in o.material_slots:
                v = plain(sl.material)
                if v is None:
                    continue
                sl.material = dark if v < 0.08 else (mt if v > 0.33 else mb)
    # the hero's own interior was exported without materials: a soft warm white so the rooms bounce light
    inner = M.new("amber_interior"); nt, out = clear(inner); principled(nt, out, (0.30, 0.28, 0.25), 0.8)
    for o in D.collections[HERO_COLL].all_objects:
        if o.type == "MESH" and not o.material_slots:
            o.data.materials.append(inner)

# ------------------------------------------------------------------ environment
def new_mesh_object(name, verts, faces, mat, coll):
    me = D.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = D.objects.new(name, me)
    coll.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob

def strip(name, ys, x_left, x_right, z_of, mat, coll, thick=0.0):
    """A ribbon along the street between two x lines (functions of y)."""
    verts, faces = [], []
    for y in ys:
        verts.append((x_left(y), y, z_of(y)))
        verts.append((x_right(y), y, z_of(y)))
    for i in range(len(ys) - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    return new_mesh_object(name, verts, faces, mat, coll)

def frange(a, b, step):
    out = []
    v = a
    while v < b - 1e-6:
        out.append(v); v += step
    out.append(b)
    return out

def scatter_group(name):
    """Geometry nodes: instance one object on every vertex, turned and scaled by per point attributes."""
    ng = D.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Object", in_out="INPUT", socket_type="NodeSocketObject")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    m2p = ng.nodes.new("GeometryNodeMeshToPoints")
    oi = ng.nodes.new("GeometryNodeObjectInfo"); oi.transform_space = "ORIGINAL"
    oi.inputs["As Instance"].default_value = True
    iop = ng.nodes.new("GeometryNodeInstanceOnPoints")
    rot = ng.nodes.new("GeometryNodeInputNamedAttribute"); rot.data_type = "FLOAT"; rot.inputs["Name"].default_value = "spin"
    scl = ng.nodes.new("GeometryNodeInputNamedAttribute"); scl.data_type = "FLOAT"; scl.inputs["Name"].default_value = "size"
    comb = ng.nodes.new("ShaderNodeCombineXYZ")
    ng.links.new(gi.outputs["Geometry"], m2p.inputs["Mesh"])
    ng.links.new(gi.outputs["Object"], oi.inputs["Object"])
    ng.links.new(m2p.outputs["Points"], iop.inputs["Points"])
    ng.links.new(oi.outputs["Geometry"], iop.inputs["Instance"])
    ng.links.new(rot.outputs["Attribute"], comb.inputs["Z"])
    ng.links.new(comb.outputs["Vector"], iop.inputs["Rotation"])
    ng.links.new(scl.outputs["Attribute"], iop.inputs["Scale"])
    ng.links.new(iop.outputs["Instances"], go.inputs["Geometry"])
    return ng

def scatter(name, points, source, group, coll):
    """points: list of (x, y, z, spin, size). The source keeps its own modifiers and is instanced, not copied."""
    me = D.meshes.new(name)
    me.from_pydata([p[:3] for p in points], [], [])
    a = me.attributes.new("spin", "FLOAT", "POINT"); b = me.attributes.new("size", "FLOAT", "POINT")
    for i, p in enumerate(points):
        a.data[i].value = p[3]; b.data[i].value = p[4]
    ob = D.objects.new(name, me)
    coll.objects.link(ob)
    mod = ob.modifiers.new("scatter", "NODES")
    mod.node_group = group
    key = next(i.identifier for i in group.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == "Object")
    mod[key] = source
    return ob

def setup_environment():
    coll = D.collections.new("amber_set")
    s.collection.children.link(coll)
    M = D.materials
    asphalt, walk = M["Asphalt Black"], M["Concrete pavement"]
    ground = M.new("amber_ground"); mat_ground(ground)
    kerb = M.new("amber_kerb"); mat_concrete(kerb, joint=3.0, tint=(0.40, 0.39, 0.37))

    # 1. the street carried on both ways, and a pavement on the far side
    road_lo = frange(-260.0, 46.6, 12.0); road_hi = frange(160.3, 460.0, 12.0)
    for nm, ys in (("amber_road_down", road_lo), ("amber_road_up", road_hi)):
        strip(nm, ys, lambda y: curb_x(y) - 0.2, lambda y: FAR_CURB, lambda y: street_z(y) + 0.04, asphalt, coll)
    full = frange(-260.0, 460.0, 6.0)
    strip("amber_walk_far", full, lambda y: FAR_CURB - 0.05, lambda y: FAR_CURB + 4.2, lambda y: street_z(y) + 0.32, walk, coll)
    strip("amber_kerb_far", full, lambda y: FAR_CURB - 0.06, lambda y: FAR_CURB - 0.05, lambda y: street_z(y) - 0.2, kerb, coll)
    # near side pavement beyond the modelled length
    for nm, ys in (("amber_walk_down", frange(-260.0, 76.9, 6.0)), ("amber_walk_up", frange(132.7, 460.0, 6.0))):
        strip(nm, ys, lambda y: curb_x(y) - 3.6, lambda y: curb_x(y) + 0.05, lambda y: street_z(y) + 0.34, walk, coll)

    # 2. terrain: fills the void around the modelled patch, hill behind, land falling away across the street
    nx, ny = 150, 150
    x0, x1, y0, y1 = -520.0, 420.0, -420.0, 620.0
    verts, faces = [], []
    for j in range(ny + 1):
        # denser rows near the site
        ty = j / ny; y = y0 + (y1 - y0) * ty
        for i in range(nx + 1):
            tx = i / nx; x = x0 + (x1 - x0) * tx
            verts.append((x, y, terrain_z(x, y)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    new_mesh_object("amber_terrain", verts, faces, ground, coll)

    # 3. trees: instances of the scene's own tree, on the hill behind and thinly across the street
    grp = scatter_group("amber_scatter")
    tree = D.objects["tree.008"]
    rnd = random.Random(7)
    pts = []
    tries = 0
    while len(pts) < 110 and tries < 6000:
        tries += 1
        x = rnd.uniform(-330, -52); y = rnd.uniform(-330, 520)
        if -45 < y < 135 and x > -100:
            continue                       # the owner's own hill and trees stay as they are
        if any((x - p[0]) ** 2 + (y - p[1]) ** 2 < 24 ** 2 for p in pts):
            continue
        pts.append((x, y, terrain_z(x, y) - 1.0, rnd.uniform(0, 6.28), rnd.uniform(0.55, 1.0)))
    # a few more on the owner's hill crest so the skyline behind the roof is not bare
    for (x, y, sc) in ((-88, 20, 0.8), (-92, 70, 0.9), (-90, 118, 0.85), (-84, -22, 0.75), (-70, 132, 0.8), (-74, 96, 0.7),
                       (-66, 72, 0.75), (-80, 44, 0.9), (-64, 122, 0.65), (-96, 100, 1.0), (-60, 30, 0.7), (-52, 128, 0.6)):
        pts.append((x, y, terrain_z(x, y) + 1.5, rnd.uniform(0, 6.28), sc))
    for k in range(26):
        x = rnd.uniform(-99, -62); y = rnd.uniform(-45, 150)
        pts.append((x, y, terrain_z(x, y) + 1.5, rnd.uniform(0, 6.28), rnd.uniform(0.45, 0.85)))
    if "trees" not in SKIP:
        scatter("amber_trees_hill", pts, tree, grp, coll)
    far = []
    tries = 0
    while len(far) < 34 and tries < 4000:
        tries += 1
        x = rnd.uniform(78, 330); y = rnd.uniform(-330, 520)
        if any((x - p[0]) ** 2 + (y - p[1]) ** 2 < 30 ** 2 for p in far):
            continue
        far.append((x, y, terrain_z(x, y) - 1.0, rnd.uniform(0, 6.28), rnd.uniform(0.5, 0.9)))
    if "trees" not in SKIP:
        scatter("amber_trees_far", far, tree, grp, coll)

    # 4. street trees that throw the long dappled shadows: placed up sun from the facade
    # one in a tree well on the near pavement just above the house (it shades the garage side and screens the
    # neighbour), one on the far pavement up the hill (its shadow lies across the road in front of the house)
    y1 = 121.5
    gobo = [(curb_x(y1) - 1.0, y1, street_z(y1) + 0.2, 1.3, 0.46),
            (FAR_CURB + 2.6, 150.0, street_z(150.0) + 0.2, 4.0, 0.66),
            (FAR_CURB + 3.0, 212.0, street_z(212.0) + 0.2, 2.2, 0.7)]
    soil = M.new("amber_soil"); nt, out = clear(soil)
    principled(nt, out, (0.035, 0.028, 0.02), 0.95, bump(nt, noise_tex(nt, world_pos(nt), 9.0, detail=5.0), 1.0, 0.1))
    for i, (x, y, z, _r, _s) in enumerate(gobo):
        h = 1.3
        zz = street_z(y) + 0.37
        new_mesh_object(f"amber_tree_well_{i}", [(x - h, y - h, zz), (x + h, y - h, zz), (x + h, y + h, zz), (x - h, y + h, zz)], [(0, 1, 2, 3)], soil, coll)
    if "gobo" not in SKIP:
        scatter("amber_trees_street", gobo, tree, grp, coll)

    # 5. the street carries on: copies of the two neighbours further down and up the hill, as instances
    # (linked copies of the objects: instancing the whole collection stalls Cycles on its nested grass scatters)
    def place(cname, y_shift, tag):
        src = D.collections[cname]
        meshes = [o for o in src.all_objects if o.type == "MESH" and not o.hide_render]
        ys = [o.matrix_world.translation.y for o in meshes]
        yc = (min(ys) + max(ys)) / 2
        off = Vector((curb_x(yc + y_shift) - curb_x(yc), y_shift, street_z(yc + y_shift) - street_z(yc)))
        sub = D.collections.new(f"amber_{tag}"); coll.children.link(sub)
        for o in meshes:
            c = o.copy()
            sub.objects.link(c)
            c.parent = None
            m = o.matrix_world.copy(); m.translation = m.translation + off
            c.matrix_world = m
    if "houses" not in SKIP:
        place("Right Neighbour", -56.6, "house_down_1")     # below the left neighbour
        place("Left Neighbour", -38.2, "house_down_2")
        place("Left Neighbour", 56.6, "house_up_1")          # above the right neighbour
        place("Right Neighbour", 38.2, "house_up_2")

    # 6. planting on the far pavement edge: something close to the lens for the sliding shots
    hedge = D.objects["Cotoneáster.002"]
    grass = D.objects["Wild Grass Patch 2"]
    hp = []
    for y in (62.0, 71.0, 80.0, 131.0, 140.0, 149.0):
        hp.append((FAR_CURB + 6.4, y, street_z(y) - 0.2, math.pi / 2 + rnd.uniform(-0.1, 0.1), rnd.uniform(1.0, 1.25)))
    # a low clipped row opposite the house: the cameras on the far verge look over it
    y = 90.0
    while y < 121.0:
        hp.append((FAR_CURB + 7.2, y, street_z(y) - 0.1, math.pi / 2 + rnd.uniform(-0.06, 0.06), rnd.uniform(0.78, 0.86)))
        y += 4.0
    if "hedge" not in SKIP:
        scatter("amber_hedge_far", hp, hedge, grp, coll)
    gp = []
    for k in range(900):
        y = rnd.uniform(40, 175); x = FAR_CURB + 4.4 + abs(rnd.gauss(0, 2.2))
        gp.append((x, y, terrain_z(max(x, FAR_CURB + 4.01), y) - 0.05, rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.9)))
    # verge on the near side beyond the modelled gardens, so the copied houses do not stand on bare ground
    for k in range(2600):
        y = rnd.choice((rnd.uniform(-90, 37), rnd.uniform(173, 290)))
        x = rnd.uniform(curb_x(y) - 16, curb_x(y) - 3.8)
        gp.append((x, y, terrain_z(x, y) - 0.05, rnd.uniform(0, 6.28), rnd.uniform(0.9, 1.8)))
    if "verge" not in SKIP:
        scatter("amber_grass_verge", gp, grass, grp, coll)
    return coll

# ------------------------------------------------------------------ lights inside the house
def setup_interior():
    coll = D.collections.new("amber_lights")
    s.collection.children.link(coll)
    def lamp(name, loc, watts, radius=0.9, colour=(1.0, 0.74, 0.47)):
        ld = D.lights.new(name, "POINT")
        ld.energy = watts; ld.color = colour; ld.shadow_soft_size = radius
        ob = D.objects.new(name, ld); ob.location = loc
        coll.objects.link(ob)
        return ob
    # upper floor rooms behind the three tall windows and the square one
    lamp("amber_room_a", (-19.5, 100.5, 35.6), 5000)
    lamp("amber_room_b", (-20.5, 104.5, 35.6), 4500)
    lamp("amber_room_c", (-21.5, 111.3, 35.6), 1800)
    # ground floor: the room by the entry and the garage behind the frosted door
    lamp("amber_entry_room", (-18.5, 99.4, 28.6), 4500)
    lamp("amber_garage", (-23.0, 109.7, 28.6), 4500, colour=(1.0, 0.80, 0.58))
    # the two wall sconces by the door: light washing down and up the white boards
    for i, (x, y, z) in enumerate(((-15.37, 104.01, 28.0), (-18.1, 104.88, 28.0))):
        for dz in (-0.62, 0.62):
            lamp(f"amber_sconce_{i}_{'u' if dz > 0 else 'd'}", (x + 0.25, y, z + dz), 500, radius=0.07, colour=(1.0, 0.66, 0.36))
    return coll

def apply():
    skip = SKIP
    for step in (setup_render, setup_visibility, setup_world, setup_materials, setup_environment, setup_interior):
        if step.__name__ in skip:
            continue
        t = time.time()
        step()
        print("AMBER", step.__name__, round(time.time() - t, 1), "s", flush=True)

if __name__ == "__main__":
    apply()
    if MODE == "save":
        # one image in the file points at a texture that no longer exists anywhere; nothing visible uses it
        for im in list(D.images):
            if im.source == "FILE" and not im.packed_file and not os.path.exists(bpy.path.abspath(im.filepath)):
                print("AMBER dropping missing image", im.name, "users", im.users)
                D.images.remove(im)
        target = os.path.join(ROOT, "assets-src", "amber", "scene-v2.blend")
        assert not target.endswith("scene.blend")
        bpy.ops.wm.save_as_mainfile(filepath=target, compress=True, copy=False)
        print("AMBER_SAVED", target)
    elif MODE == "test":
        import importlib.util
        spec = importlib.util.spec_from_file_location("amber_views", os.path.join(HERE, "amber-views.py"))
        av = importlib.util.module_from_spec(spec); spec.loader.exec_module(av)
        av.render_stills(os.path.abspath(argv[1]), argv[2:], test=True)
