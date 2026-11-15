# Extra cinematic clips from the studio's own finished scene (Cycles), same film treatment as the hero shot:
# 24 frames a second, 2.39:1, shallow depth of field, motion blur. Grade is added afterwards in ffmpeg.
#   blender -b <scene.blend> --python tools/render-clip.py -- <out folder> <wide|detail|garden> [test]
#
#   wide   : the establishing view from the scene's first camera, a slow sideways slide with a gentle push in
#   detail : a long lens close on the facade from the hero angle, rising from the planting to the balcony
#   garden : low and wide among the flowers, sliding sideways
import bpy, sys, os, time
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, SHOT = argv[0], argv[1]
TEST = len(argv) > 2
FRAMES = 192          # eight seconds
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
s.frame_start, s.frame_end = 1, FRAMES

src = bpy.data.objects["Camera" if SHOT == "wide" else "Camera.015"]
base_pos = src.matrix_world.translation.copy()
q = src.matrix_world.to_quaternion()
forward, right, up = q @ Vector((0, 0, -1)), q @ Vector((1, 0, 0)), Vector((0, 0, 1))
dg = bpy.context.evaluated_depsgraph_get()
hit, loc, *_ = s.ray_cast(dg, base_pos, forward)
far = (loc - base_pos).length if hit else 30.0
aim = loc if hit else base_pos + forward * far
print("DISTANCE", round(far, 2))

# a fresh camera that always looks at a moving target
cd = bpy.data.cameras.new("clipcam"); cam = bpy.data.objects.new("clipcam", cd); s.collection.objects.link(cam)
tgt = bpy.data.objects.new("cliptarget", None); s.collection.objects.link(tgt)
con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
s.camera = cam
cd.sensor_width = src.data.sensor_width
cd.clip_end = 5000
cd.dof.use_dof = True
cd.dof.focus_object = tgt
cd.dof.aperture_ratio = 1.6

def key(ob, path, value, frame):
    setattr(ob, path, value); ob.keyframe_insert(path, frame=frame)

if SHOT == "wide":
    cd.lens = src.data.lens * 1.15
    cd.dof.aperture_fstop = 1.4
    key(cam, "location", base_pos - right * (far * 0.05) - forward * (far * 0.02), 1)
    key(cam, "location", base_pos + right * (far * 0.07) + forward * (far * 0.10) + up * (far * 0.012), FRAMES)
    key(tgt, "location", aim - up * (far * 0.01), 1)
    key(tgt, "location", aim + up * (far * 0.02), FRAMES)
elif SHOT == "garden":
    # low among the planting, a slow slide past the flowers with the house behind them
    cd.lens = 30
    cd.dof.aperture_fstop = 1.2
    start = base_pos - up * (far * 0.05) - right * (far * 0.16) + forward * (far * 0.10)
    key(cam, "location", start, 1)
    key(cam, "location", start + right * (far * 0.17) + forward * (far * 0.03) + up * (far * 0.012), FRAMES)
    key(tgt, "location", aim + up * (far * 0.02), 1)
    key(tgt, "location", aim + up * (far * 0.05), FRAMES)
else:
    cd.lens = src.data.lens * 1.9
    cd.dof.aperture_fstop = 1.1
    start = base_pos + right * (far * 0.16) - up * (far * 0.03) + forward * (far * 0.04)
    key(cam, "location", start, 1)
    key(cam, "location", start + up * (far * 0.05) + right * (far * 0.05) + forward * (far * 0.05), FRAMES)
    key(tgt, "location", aim - up * (far * 0.11) + right * (far * 0.02), 1)       # the planting at the foot of the wall
    key(tgt, "location", aim + up * (far * 0.07) + right * (far * 0.05), FRAMES)  # up to the balcony

for ob in (cam, tgt):
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

frames = [1, 64, 128, 192] if TEST else range(1, FRAMES + 1)
for f in frames:
    path = os.path.join(OUT, f"{f:04d}.jpg")
    if not TEST and os.path.exists(path):
        continue
    s.frame_set(f)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
print("CLIP_OK", SHOT)
