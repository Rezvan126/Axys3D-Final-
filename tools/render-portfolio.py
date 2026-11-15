# New portfolio stills of the residence, rendered in Cycles from the studio's own finished scene.
# Each view is a fresh camera placed relative to the two good cameras already in the file.
#   blender -b <scene.blend> --python tools/render-portfolio.py -- <out folder> [test] [view ...]
#
#   garden   : low among the planting, wide lens, the house rising behind the flowers
#   balcony  : long lens on the balcony and glazing
#   approach : the wide establishing view with the trees either side
#   corner   : three quarter view from the other side of the front
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
TEST = "test" in argv[1:]
ONLY = [a for a in argv[1:] if a != "test"]
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
s.cycles.samples = 24 if TEST else 220
s.cycles.use_adaptive_sampling = True
s.cycles.use_denoising = True
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = (720, 405, 100) if TEST else (2400, 1350, 100)
s.render.image_settings.file_format = "JPEG"; s.render.image_settings.quality = 95
s.render.use_motion_blur = False

def basis(name):
    src = bpy.data.objects[name]
    pos = src.matrix_world.translation.copy()
    q = src.matrix_world.to_quaternion()
    fwd, right = q @ Vector((0, 0, -1)), q @ Vector((1, 0, 0))
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = s.ray_cast(dg, pos, fwd)
    far = (loc - pos).length if hit else 30.0
    return src, pos, fwd, right, far, (loc if hit else pos + fwd * far)

up = Vector((0, 0, 1))
A, a_pos, a_f, a_r, a_far, a_aim = basis("Camera")        # wide establishing camera
B, b_pos, b_f, b_r, b_far, b_aim = basis("Camera.015")    # hero camera
print("FAR", round(a_far, 2), round(b_far, 2))

# name: (position, look at, lens, f-stop, dusk?)
VIEWS = {
    "garden":   (b_pos - up * (b_far * 0.045) - b_r * (b_far * 0.10) + b_f * (b_far * 0.10), b_aim + up * (b_far * 0.03), 30, 2.0, False),
    "balcony":  (b_pos + b_r * (b_far * 0.20) + up * (b_far * 0.02), b_aim + up * (b_far * 0.06) + b_r * (b_far * 0.04), 95, 2.8, False),
    "approach": (a_pos - a_f * (a_far * 0.04) + up * (a_far * 0.01), a_aim, 40, 4.0, False),
    # close studies for service pages and articles: materials, glazing, planting
    "window":   (b_pos + up * (b_far * 0.01), b_aim + up * (b_far * 0.10) - b_r * (b_far * 0.06), 170, 4.0, False),
    "doors":    (b_pos - b_r * (b_far * 0.06) - up * (b_far * 0.02), b_aim - up * (b_far * 0.05), 120, 2.8, False),
    "meadow":   (b_pos - up * (b_far * 0.06) + b_r * (b_far * 0.05) + b_f * (b_far * 0.25), b_aim + up * (b_far * 0.08), 24, 2.0, False),
    "upper":    (a_pos + up * (a_far * 0.02), a_aim + up * (a_far * 0.07) - a_r * (a_far * 0.035), 110, 4.0, False),
    "corner":   (b_pos + b_r * (b_far * 0.55) + b_f * (b_far * 0.12) + up * (b_far * 0.03), b_aim + up * (b_far * 0.02), 38, 2.8, False),
}

def make_cam(name, pos, aim, lens, fstop):
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); s.collection.objects.link(cam)
    cam.location = pos
    cam.rotation_euler = (aim - pos).to_track_quat("-Z", "Y").to_euler()
    cd.lens = lens; cd.sensor_width = B.data.sensor_width; cd.clip_end = 5000
    cd.dof.use_dof = True; cd.dof.focus_distance = (aim - pos).length; cd.dof.aperture_fstop = fstop
    return cam

for name, (pos, aim, lens, fstop, is_dusk) in VIEWS.items():
    if ONLY and name not in ONLY:
        continue
    path = os.path.join(OUT, f"{name}.jpg")
    if not TEST and os.path.exists(path):
        continue
    s.camera = make_cam("pf_" + name, pos, aim, lens, fstop)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("VIEW_OK", name)
