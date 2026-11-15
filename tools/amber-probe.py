# First look at the amber scene in Cycles, as the file stands (only the render-disabled collections switched on).
#   blender --disable-autoexec -b assets-src/amber/scene.blend -P tools/amber-probe.py -- <out folder>
import bpy, sys, os, time, math
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
s = bpy.context.scene
print("PROBE scene", s.name, "world", s.world.name if s.world else None)
for sc in bpy.data.scenes:
    print("PROBE SCENE", sc.name, "objects", len(sc.objects), "camera", sc.camera.name if sc.camera else None)

# node groups used by the grouped materials and the geometry node modifiers
def dump_tree(nt, depth=0, seen=None):
    seen = seen if seen is not None else set()
    if nt.name in seen:
        return
    seen.add(nt.name)
    for n in nt.nodes:
        extra = ""
        if n.type == "TEX_IMAGE" and n.image:
            extra = n.image.name
        if n.type == "GROUP" and n.node_tree:
            extra = "-> " + n.node_tree.name
        if n.type in ("OBJECT_INFO", "COLLECTION_INFO"):
            for i in n.inputs:
                if hasattr(i, "default_value") and i.default_value is not None and hasattr(i.default_value, "name"):
                    extra += " " + i.default_value.name
        print("PROBE", "  " * depth, n.type, "|", n.name, "|", extra)
        if n.type == "GROUP" and n.node_tree:
            dump_tree(n.node_tree, depth + 1, seen)

for mn in ("Glass.002", "Plaster", "Procedural Grass", "White Plastic", "Spacer mesh", "Procedural frosted glass", "Grass"):
    m = bpy.data.materials.get(mn)
    if m and m.node_tree:
        print("PROBE MATERIAL", mn)
        dump_tree(m.node_tree, 1)
for on in ("Cube", "Toposolid Toposolid 1 [1794106].001", "Grid.002", "FF walls.007", "FF walls.001", "Cylinder"):
    o = bpy.data.objects.get(on)
    if not o:
        continue
    for m in o.modifiers:
        if m.type == "NODES" and m.node_group and "Smooth" not in m.node_group.name:
            print("PROBE GEONODES", on, m.node_group.name)
            dump_tree(m.node_group, 1)
            for k in m.keys():
                try:
                    v = m[k]
                    print("PROBE    input", k, v.name if hasattr(v, "name") else v)
                except Exception:
                    pass

w = s.world
for n in w.node_tree.nodes:
    if n.type == "TEX_ENVIRONMENT" and n.image:
        print("PROBE HDRI", n.image.name, list(n.image.size), "packed", n.image.packed_file is not None)
    if n.type == "BACKGROUND":
        print("PROBE BG strength", n.inputs[1].default_value)
    if n.type == "MAPPING":
        print("PROBE MAP rot", list(n.inputs["Rotation"].default_value))

# switch on what was disabled for render
for c in bpy.data.collections:
    if c.hide_render:
        print("PROBE enabling", c.name)
        c.hide_render = False
for o in s.objects:
    if o.hide_render:
        print("PROBE object hidden for render:", o.name)

prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == kind
            print("PROBE device", kind, [d.name for d in prefs.devices if d.use])
            break
    except Exception as e:
        print("PROBE device fail", kind, e)
s.render.engine = "CYCLES"
s.cycles.device = "GPU"
s.cycles.samples = 24
s.cycles.use_adaptive_sampling = True
s.cycles.use_denoising = True
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 720, 405, 100
s.render.image_settings.file_format = "JPEG"; s.render.image_settings.quality = 92
s.render.use_motion_blur = False

for name in ("Camera.002", "Camera.001", "Camera"):
    s.camera = bpy.data.objects[name]
    s.render.filepath = os.path.join(OUT, "probe-" + name.replace(".", "_") + ".jpg")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print("PROBE rendered", name, round(time.time() - t, 1), "s")

# a plan view to read the layout
cd = bpy.data.cameras.new("plan"); cam = bpy.data.objects.new("plan", cd); s.collection.objects.link(cam)
cd.type = "ORTHO"; cd.ortho_scale = 150; cd.clip_end = 2000
cam.location = (-10, 105, 300); cam.rotation_euler = (0, 0, 0)
s.camera = cam
s.render.resolution_x, s.render.resolution_y = 800, 800
s.render.filepath = os.path.join(OUT, "probe-plan.jpg")
bpy.ops.render.render(write_still=True)
print("PROBE_OK")
