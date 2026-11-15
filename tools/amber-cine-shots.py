# The four shots of the amber house film (10 s each, 24 fps, 2.39:1). Used by amber-cine-setup.py (previews),
# amber-cine-render.py (finals) and amber-cine-stills.py.
#   A  low crane up from behind the far verge, through the hedge and grasses, revealing the house
#   B  slow dolly along the near pavement, ornamental grasses and shrubs crossing close to the lens
#   C  detail: rack focus from grass blades to the entry door, then a drift across to the glowing garage panels
#   D  pull back and rise to the wide street as the sun goes down and the lamps take over
import bpy, os, math, time
from mathutils import Vector

FRAMES = 240
RES = (1920, 804)

def _curves(ob):
    act = ob.animation_data.action
    try:
        return list(act.fcurves)
    except Exception:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out

def _ease(ob):
    for fc in _curves(ob):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

def _keys(ob, path, pairs):
    for f, v in pairs:
        setattr(ob, path, v); ob.keyframe_insert(path, frame=f)

def _shake(ob, strength, scale, phase):
    """Handheld / crane float: a slow, small noise on top of the move."""
    for fc in _curves(ob):
        if fc.data_path == "location":
            m = fc.modifiers.new("NOISE"); m.strength = strength; m.scale = scale; m.phase = phase + 7 * fc.array_index; m.depth = 1

SHOTS = {
    "a": dict(lens=45, fstop=2.0,
              cam=[(1, (57.6, 101.0, 22.35)), (240, (54.6, 102.4, 30.2))],
              tgt=[(1, (-15.0, 106.0, 27.4)), (240, (-15.0, 106.0, 30.4))],
              focus=None, shake=(0.035, 60)),
    "b": dict(lens=30, fstop=2.0,
              cam=[(1, (-4.0, 93.5, 23.9)), (240, (-4.3, 104.5, 25.5))],
              tgt=[(1, (-16.5, 101.0, 28.8)), (240, (-17.5, 108.5, 29.6))],
              focus=None, shake=(0.03, 55)),
    "c": dict(lens=40, fstop=1.4,
              cam=[(1, (-8.6, 101.8, 24.9)), (110, (-8.55, 102.4, 25.3)), (240, (-8.4, 105.6, 26.6))],
              tgt=[(1, (-16.6, 102.8, 26.3)), (110, (-16.6, 102.9, 26.3)), (240, (-18.6, 109.2, 26.6))],
              # focus distance in scene units: grass blades at the foot of the steps, pulled to the door, carried to the garage
              focus=[(1, 1.3), (36, 1.3), (96, 8.1), (240, 10.8)], shake=(0.012, 50), exposure=0.25),
    "d": dict(lens=35, fstop=2.8,
              cam=[(1, (11.0, 104.5, 26.4)), (240, (76.0, 91.0, 41.0))],
              tgt=[(1, (-15.0, 106.0, 29.4)), (240, (-20.0, 106.5, 32.0))],
              focus=None, shake=(0.04, 70), dusk=True),
}

def build(shot):
    s = bpy.context.scene
    d = SHOTS[shot]
    cd = bpy.data.cameras.new("cine_" + shot); cam = bpy.data.objects.new("cine_" + shot, cd); s.collection.objects.link(cam)
    tgt = bpy.data.objects.new("cine_tgt_" + shot, None); s.collection.objects.link(tgt)
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.lens = d["lens"]; cd.sensor_width = 36.0; cd.sensor_fit = "HORIZONTAL"
    cd.clip_start = 0.1; cd.clip_end = 5000
    cd.dof.use_dof = True; cd.dof.aperture_fstop = d["fstop"]; cd.dof.aperture_blades = 7; cd.dof.aperture_ratio = 1.15
    _keys(cam, "location", [(f, Vector(v)) for f, v in d["cam"]]); _ease(cam)
    _keys(tgt, "location", [(f, Vector(v)) for f, v in d["tgt"]]); _ease(tgt)
    if d["focus"]:
        _keys(cd.dof, "focus_distance", d["focus"])
        _ease(cd)
    else:
        cd.dof.focus_object = tgt
    _shake(cam, d["shake"][0], d["shake"][1], 3.0)
    _shake(tgt, d["shake"][0] * 0.6, d["shake"][1] * 1.3, 11.0)
    s.camera = cam
    if d.get("exposure"):
        s.view_settings.exposure += d["exposure"]
    if d.get("dusk"):
        dusk()
    return cam

def dusk():
    """Shot D: the sun sinks behind the street, the sky cools, the lamps carry the house."""
    s = bpy.context.scene
    sky = next(n for n in s.world.node_tree.nodes if n.type == "TEX_SKY")
    sky.sun_elevation = math.radians(12.5); sky.keyframe_insert("sun_elevation", frame=1)
    sky.sun_elevation = math.radians(4.0); sky.keyframe_insert("sun_elevation", frame=240)
    vs = s.view_settings
    e0 = vs.exposure
    vs.exposure = e0; vs.keyframe_insert("exposure", frame=1)
    vs.exposure = e0 + 0.8; vs.keyframe_insert("exposure", frame=240)
    for o in s.objects:
        if o.type == "LIGHT" and o.name.startswith("amber_"):
            e = o.data.energy
            o.data.keyframe_insert("energy", frame=1)
            o.data.energy = e * 1.8; o.data.keyframe_insert("energy", frame=240)
            o.data.energy = e

def setup_render(preview, samples=None, res=None):
    s = bpy.context.scene
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(x.type == kind for x in prefs.devices):
                for x in prefs.devices: x.use = x.type == kind
                break
        except Exception:
            continue
    s.render.engine = "CYCLES"
    s.cycles.device = "GPU"
    s.cycles.samples = samples or (16 if preview else 56)
    w, h = res or ((640, 268) if preview else RES)
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.fps = 24
    s.render.use_motion_blur = not preview
    s.render.motion_blur_shutter = 0.5
    s.render.use_persistent_data = True
    s.render.image_settings.file_format = "JPEG"; s.render.image_settings.quality = 96
    s.render.use_stamp = False
    s.frame_start, s.frame_end = 1, FRAMES
    # test overrides: AMBER_SKY="air,aerosol,sun intensity,elevation deg", AMBER_EXPOSURE
    if os.environ.get("AMBER_SKY"):
        air, aer, si, el = (float(v) for v in os.environ["AMBER_SKY"].split(","))
        sky = next(n for n in s.world.node_tree.nodes if n.type == "TEX_SKY")
        sky.air_density, sky.aerosol_density, sky.sun_intensity, sky.sun_elevation = air, aer, si, math.radians(el)
    for name in filter(None, os.environ.get("AMBER_HIDE", "").split(",")):
        c = bpy.data.collections.get(name)
        if c: c.hide_render = True
        o = bpy.data.objects.get(name)
        if o: o.hide_render = True
    if os.environ.get("AMBER_EXPOSURE"):
        s.view_settings.exposure = float(os.environ["AMBER_EXPOSURE"])

def render_shot(out, shot, preview=False, frames=None, samples=None):
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    setup_render(preview, samples)
    build(shot)
    s = bpy.context.scene
    if frames is None:
        frames = [1, 30, 60, 90, 120, 150, 180, 210, 240] if preview else range(1, FRAMES + 1)
    t0 = time.time()
    for f in frames:
        path = os.path.join(out, f"{f:04d}.jpg")
        if not preview and os.path.exists(path):
            continue
        s.frame_set(f)
        s.render.filepath = path
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("FRAME", shot, f, round(time.time() - t, 1), "s", flush=True)
    print("SHOT_OK", shot, round(time.time() - t0, 1), "s", flush=True)
