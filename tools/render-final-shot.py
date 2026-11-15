# The hero shot of the building film, rendered in Cycles from the studio's own finished scene.
# Ten seconds, 24 frames a second, 2.39:1 widescreen:
#   a slow crane up and push in from low among the foreground planting,
#   shallow depth of field with a focus pull from the plants to the building,
#   and real motion blur. The colour grade, bloom and grain are added afterwards in ffmpeg.
#
#   blender -b <scene.blend> --python tools/render-final-shot.py -- <out folder> <camera name> [test]
import bpy, sys, os, time
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, CAM = argv[0], argv[1]
TEST = len(argv) > 2
FRAMES = 240
os.makedirs(OUT, exist_ok=True)

s = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == kind
            print("GPU", kind)
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
s.render.motion_blur_shutter = 0.5          # the classic 180 degree shutter
s.frame_start, s.frame_end = 1, FRAMES

cam = bpy.data.objects[CAM]
s.camera = cam
cam.animation_data_clear()
for c in list(cam.constraints): cam.constraints.remove(c)
end_pos = cam.location.copy()
q = cam.matrix_world.to_quaternion()
forward, right, up = q @ Vector((0, 0, -1)), q @ Vector((1, 0, 0)), Vector((0, 0, 1))

# how far away is the building along the lens axis?
dg = bpy.context.evaluated_depsgraph_get()
hit, loc, *_ = s.ray_cast(dg, end_pos, forward)
far = (loc - end_pos).length if hit else 30.0
print("BUILDING_DISTANCE", round(far, 2))

# the move: start back, low and to the left; finish on the scene's own framing, a little closer
start_pos = end_pos - forward * (far * 0.13) - right * (far * 0.035) - up * (far * 0.032)
final_pos = end_pos + forward * (far * 0.15) + right * (far * 0.06) + up * (far * 0.012)
cam.location = start_pos; cam.keyframe_insert("location", frame=1)
cam.location = final_pos; cam.keyframe_insert("location", frame=FRAMES)

# lens: a longer lens compresses the building against the trees; wide open for soft foreground
cd = cam.data
cd.lens = max(cd.lens, 50) * 1.0
cd.dof.use_dof = True
cd.dof.focus_object = None
cd.dof.aperture_fstop = 0.55
cd.dof.aperture_blades = 0
cd.dof.aperture_ratio = 1.6                 # slightly oval highlights, like an anamorphic lens
near = far * 0.5
cd.dof.focus_distance = near; cd.dof.keyframe_insert("focus_distance", frame=1)
cd.dof.focus_distance = near; cd.dof.keyframe_insert("focus_distance", frame=60)
cd.dof.focus_distance = far * 1.05; cd.dof.keyframe_insert("focus_distance", frame=150)
cd.dof.focus_distance = far * 0.88; cd.dof.keyframe_insert("focus_distance", frame=FRAMES)

# ease in and out on everything
for ob in (cam, cd):
    ad = ob.animation_data
    if not ad or not ad.action: continue
    act = ad.action
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

frames = [1, 60, 120, 180, 240] if TEST else range(1, FRAMES + 1)
for f in frames:
    path = os.path.join(OUT, f"{f:04d}.jpg")
    if not TEST and os.path.exists(path):
        continue                                # lets an interrupted render pick up where it stopped
    s.frame_set(f)
    s.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("FRAME", f, round(time.time() - t0, 1), "s")
print("SHOT_OK")
