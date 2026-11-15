# Renders stills of the studio's own project model for the service pages:
# clay model, BIM by discipline, MEP x-ray and a plan view.
#   blender -b --factory-startup --python tools/render-shots.py -- public/models/adu.glb assets-src/gellert/shots
import bpy, sys, math, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]

COL = {"architecture": (0.62, 0.62, 0.64, 1), "structure": (0.94, 0.63, 0.12, 1), "electrical": (1, 0.42, 0.37, 1),
       "mechanical": (0.35, 0.78, 0.98, 1), "plumbing": (0.2, 0.78, 0.35, 1), "interiors": (0.73, 0.65, 1, 1)}

mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
centre = (mn + mx) / 2; size = mx - mn
radius = size.length / 2

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w"); scene.world.color = (0, 0, 0)
scene.render.image_settings.file_format = "PNG"
sh = scene.display.shading
sh.light = "STUDIO"; sh.show_shadows = True; sh.show_cavity = True; sh.cavity_type = "BOTH"
scene.display.render_aa = "16"

cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam

def aim(yaw, pitch, dist, ortho=False, lens=70):
    y, p = math.radians(yaw), math.radians(pitch)
    d = radius * dist
    cam.location = centre + Vector((d * math.cos(p) * math.sin(y), -d * math.cos(p) * math.cos(y), d * math.sin(p)))
    look = centre - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam_data.type = "ORTHO" if ortho else "PERSP"
    cam_data.lens = lens
    cam_data.ortho_scale = max(size.x, size.y) * 1.12
    cam_data.clip_end = 5000

def shot(name):
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)

def show(pred):
    for o in meshes:
        o.hide_render = not pred(o)

# 1. clay model
sh.color_type = "SINGLE"; sh.single_color = (0.82, 0.8, 0.76); sh.show_xray = False; sh.show_object_outline = True; sh.object_outline_color = (0.1, 0.1, 0.1)
show(lambda o: o.get("d") in ("architecture", "structure"))
aim(-140, 22, 3.6); shot("model.png")

# 2. BIM by discipline, shell see through
sh.color_type = "OBJECT"; sh.show_xray = True; sh.xray_alpha = 0.55; sh.show_shadows = False; sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)
for o in meshes:
    o.color = COL.get(o.get("d"), (0.6, 0.6, 0.6, 1))
show(lambda o: True)
aim(35, 28, 3.5); shot("bim.png")

# 3. services only: structure, electrical, plumbing, ventilation
show(lambda o: o.get("d") != "interiors" and (o.get("d") != "architecture" or o.get("c") in ("Floors", "Stairs and railings")))
sh.xray_alpha = 0.8
aim(40, 24, 3.4); shot("mep.png")

# 4. drawings: walls, openings, stairs and fixtures only, flat white on black, straight down
PLAN = ("Walls", "Doors", "Windows", "Stairs and railings", "Casework", "Plumbing fixtures", "Columns", "Finishes", "Appliances")
sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (0.96, 0.96, 0.97); sh.show_xray = False; sh.show_shadows = False; sh.show_cavity = False
sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)
show(lambda o: o.get("c") in PLAN and "Tile" not in str(o.get("t")))
aim(0, 89.9, 4, ortho=True); cam_data.ortho_scale = size.x * 1.06; shot("plan.png")

# 5. elevation: straight on, same flat line treatment
show(lambda o: o.get("d") in ("architecture", "structure") and o.get("c") not in ("Floors",))
sh.light = "STUDIO"; sh.single_color = (0.9, 0.9, 0.92); sh.show_cavity = True
aim(180, 0.1, 4, ortho=True); cam_data.ortho_scale = size.x * 1.06; shot("elevation.png")
print("SHOTS_OK")
