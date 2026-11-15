# Cinematic clips of the amber house from the improved scene (Cycles), same film treatment as the ADU clips:
# 24 frames a second, 2.39:1, shallow depth of field, motion blur. Grade and encode happen in make-amber.sh.
#   blender --disable-autoexec -b assets-src/amber/scene-v2.blend -P tools/amber-clip.py -- <abs out folder> <hero|wide|detail> [test]
#
#   hero   : slow push in on the street front from the far pavement, camera level
#   wide   : sideways slide along the far verge, hedge and grasses passing close to the lens
#   detail : long lens drift up from the garage and entry to the upper windows and fascia
import bpy, sys, os, time
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, SHOT = os.path.abspath(argv[0]), argv[1]
TEST = len(argv) > 2
FRAMES = 120          # five seconds
os.makedirs(OUT, exist_ok=True)

s = bpy.context.scene
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
s.cycles.device = "GPU"
s.cycles.samples = 24 if TEST else 72
s.cycles.use_adaptive_sampling = True
s.cycles.use_denoising = True
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = (800, 334, 100) if TEST else (1720, 720, 100)
s.render.image_settings.file_format = "JPEG"; s.render.image_settings.quality = 95
s.render.fps = 24
s.render.use_motion_blur = not TEST
s.render.motion_blur_shutter = 0.5
s.render.use_persistent_data = True      # only the camera moves: keep the scene on the GPU between frames
s.frame_start, s.frame_end = 1, FRAMES

cd = bpy.data.cameras.new("amber_clipcam"); cam = bpy.data.objects.new("amber_clipcam", cd); s.collection.objects.link(cam)
tgt = bpy.data.objects.new("amber_cliptarget", None); s.collection.objects.link(tgt)
s.camera = cam
cd.sensor_width = 36.0
cd.clip_start = 0.3; cd.clip_end = 5000
cd.dof.use_dof = True
cd.dof.focus_object = tgt

def key(ob, path, value, frame):
    setattr(ob, path, value); ob.keyframe_insert(path, frame=frame)

def level(pos, aim):
    """Rotation for a camera that looks towards aim but stays level, so verticals stay upright."""
    a = Vector(aim); a.z = pos[2]
    return (a - Vector(pos)).to_track_quat("-Z", "Y").to_euler()

if SHOT == "hero":
    cd.lens = 44; cd.dof.aperture_fstop = 1.4; cd.shift_y = 0.115
    aim = (-15.0, 106.0, 29.6)
    a, b = (49.6, 97.0, 23.3), (40.5, 98.5, 23.7)
    cam.rotation_euler = level(a, aim)
    key(cam, "location", a, 1); key(cam, "location", b, FRAMES)
    key(tgt, "location", aim, 1)
elif SHOT == "wide":
    cd.lens = 42; cd.dof.aperture_fstop = 1.2; cd.shift_y = 0.05
    aim = (-15.0, 106.0, 29.6)
    a, b = (55.4, 98.5, 22.85), (54.9, 110.5, 24.75)
    cam.rotation_euler = level(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, a[2]), aim)
    key(cam, "location", a, 1); key(cam, "location", b, FRAMES)
    key(tgt, "location", aim, 1)
else:
    cd.lens = 85; cd.dof.aperture_fstop = 1.4
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    key(cam, "location", (13.0, 114.0, 25.2), 1); key(cam, "location", (14.5, 111.0, 28.6), FRAMES)
    key(tgt, "location", (-17.0, 107.5, 26.6), 1); key(tgt, "location", (-14.2, 104.5, 33.6), FRAMES)

for ob in (cam, tgt):
    if not ob.animation_data or not ob.animation_data.action:
        continue
    act = ob.animation_data.action
    curves = []
    try:
        curves = list(act.fcurves)
    except Exception:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves.extend(bag.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

frames = [1, 60, 120] if TEST else range(1, FRAMES + 1)
t0 = time.time()
for f in frames:
    path = os.path.join(OUT, f"{f:04d}.jpg")
    if not TEST and os.path.exists(path):
        continue
    s.frame_set(f)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
print("CLIP_OK", SHOT, round(time.time() - t0, 1), "s", flush=True)
