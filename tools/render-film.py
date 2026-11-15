# Renders the "one building, every stage" film from the studio's own project model.
# One continuous camera move; the same frames are rendered in four looks (sketch, clay model,
# BIM by discipline, materials) so they can be dissolved into each other afterwards with ffmpeg.
#   blender -b --factory-startup --python tools/render-film.py -- public/models/adu.glb <out folder> [pass ...]
import bpy, sys, math, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
ONLY = argv[2:]
FPS, TOTAL = 24, 336          # 14 seconds of camera move
# frame ranges per look; neighbours overlap by 24 frames for the dissolves
PASSES = {"sketch": (0, 96), "clay": (72, 180), "bim": (156, 264), "mat": (240, 336)}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]

# frame on the building itself (walls and roofs), not on stray site elements
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    if o.get("c") not in ("Walls", "Roofs"):
        continue
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
centre = (mn + mx) / 2; size = mx - mn
radius = size.length / 2
target = Vector((centre.x, centre.y, mn.z + size.z * 0.42))

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.render.fps = FPS
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.004, 0.004, 0.005)
scene.render.image_settings.file_format = "JPEG"; scene.render.image_settings.quality = 95
scene.display.render_aa = "16"
sh = scene.display.shading

cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam_data.lens = 38; cam_data.clip_end = 5000

def ease(t):  # smooth start and stop
    return t * t * (3 - 2 * t)

def place(frame):
    t = ease(frame / (TOTAL - 1))
    yaw = math.radians(-150 + 118 * t)          # a slow arc round the front of the building
    pitch = math.radians(26 - 17 * t)           # starts high, settles to eye level
    dist = radius * (3.2 - 0.45 * t)           # and pushes in
    cam.location = target + Vector((dist * math.cos(pitch) * math.sin(yaw), -dist * math.cos(pitch) * math.cos(yaw), dist * math.sin(pitch)))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

DISC = {"architecture": (0.62, 0.62, 0.64, 1), "structure": (0.94, 0.63, 0.12, 1), "electrical": (1, 0.42, 0.37, 1),
        "mechanical": (0.35, 0.78, 0.98, 1), "plumbing": (0.2, 0.78, 0.35, 1), "interiors": (0.73, 0.65, 1, 1)}

def finish(o):
    c, t, d = str(o.get("c")), str(o.get("t")).lower(), str(o.get("d"))
    siding, stucco, roof, glass, trim = (0.30, 0.32, 0.34, 1), (0.72, 0.68, 0.62, 1), (0.03, 0.025, 0.02, 1), (0.02, 0.035, 0.05, 1), (0.85, 0.84, 0.8, 1)
    metal, wood, concrete, white = (0.03, 0.03, 0.035, 1), (0.36, 0.2, 0.09, 1), (0.34, 0.34, 0.33, 1), (0.9, 0.9, 0.88, 1)
    if c == "Roofs": return trim if any(k in t for k in ("fascia", "gutter", "downspout")) else roof
    if c in ("Windows", "Doors"): return trim if any(k in t for k in ("trim", "flush", "panel", "bifold", "garage")) else glass
    if c == "Stairs and railings": return wood if any(k in t for k in ("stair", "run", "tread", "landing")) else metal
    if c == "Walls": return stucco if any(k in t for k in ("stucco", "partition", "cement")) else trim if "trim" in t else siding
    if c in ("Framing", "Floors"): return wood
    if d == "structure": return metal if "rectangular" in t else concrete
    return white

def setup(name):
    shell = lambda o: o.get("d") in ("architecture", "structure")
    sh.show_xray = False; sh.show_shadows = False; sh.show_cavity = True; sh.cavity_type = "BOTH"; sh.light = "STUDIO"
    sh.show_object_outline = True
    if name == "sketch":      # white line drawing on black
        sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (0.012, 0.012, 0.014)
        sh.object_outline_color = (0.95, 0.95, 0.96)
        sh.cavity_type = "SCREEN"; sh.cavity_ridge_factor = 2.5; sh.cavity_valley_factor = 0.0
        for o in meshes: o.hide_render = not shell(o)
    elif name == "clay":
        sh.color_type = "SINGLE"; sh.single_color = (0.74, 0.72, 0.68); sh.object_outline_color = (0.05, 0.05, 0.05)
        sh.show_shadows = True; sh.shadow_intensity = 0.55
        for o in meshes: o.hide_render = not shell(o)
    elif name == "bim":
        sh.color_type = "OBJECT"; sh.show_xray = True; sh.xray_alpha = 0.5; sh.object_outline_color = (0, 0, 0)
        for o in meshes:
            o.hide_render = False; o.color = DISC.get(o.get("d"), (0.6, 0.6, 0.6, 1))
    else:
        sh.color_type = "OBJECT"; sh.object_outline_color = (0.02, 0.02, 0.02)
        sh.show_shadows = True; sh.shadow_intensity = 0.6
        for o in meshes:
            o.hide_render = o.get("d") in ("electrical", "mechanical") and o.get("c") != "Lighting"
            o.color = finish(o)
    scene.display.light_direction = (0.45, 0.35, 0.82)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0 if name == "sketch" else 1.1 if name == "clay" else 0.9

for name, (a, b) in PASSES.items():
    if ONLY and name not in ONLY:
        continue
    setup(name)
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    for f in range(a, b):
        place(f)
        scene.render.filepath = os.path.join(d, f"{f:04d}.jpg")
        bpy.ops.render.render(write_still=True)
    print("PASS_OK", name)
