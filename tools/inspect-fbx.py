"""What is inside an FBX: counts, size, name samples by depth, materials, and two previews.
blender -b -P tools/inspect-fbx.py -- <model.fbx> <out prefix>
"""
import bpy, sys, math, collections
from mathutils import Vector
src, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
sc = bpy.context.scene
obs = list(sc.objects)
ms = [o for o in obs if o.type == "MESH"]
print("INFO objects", len(obs), "meshes", len(ms), "empties", len([o for o in obs if o.type == "EMPTY"]),
      "polys", sum(len(o.data.polygons) for o in ms), "materials", len(bpy.data.materials), "images", len(bpy.data.images))
def depth(o):
    d = 0
    while o.parent: o = o.parent; d += 1
    return d
by = collections.defaultdict(list)
for o in obs: by[depth(o)].append(o.name)
for d in sorted(by):
    print("INFO depth", d, len(by[d]), [n[:44] for n in by[d][:10]])
names = collections.Counter(o.name.rsplit(".", 1)[0][:40] for o in ms)
print("INFO mesh names", names.most_common(30))
print("INFO mats", [(m.name[:30], [round(c, 2) for c in m.diffuse_color[:3]]) for m in list(bpy.data.materials)[:40]])
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in ms:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
print("INFO size", [round(v, 2) for v in (hi - lo)], "lo", [round(v, 2) for v in lo])
mid = (lo + hi) / 2; span = (hi - lo).length
cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.lens = 40; cd.clip_start = span / 2000; cd.clip_end = span * 20
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"; sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1100, 700, 100
sc.render.image_settings.file_format = "PNG"
for i, (yaw, pitch) in enumerate([(215, 28), (35, 32)]):
    y, p = math.radians(yaw), math.radians(pitch)
    cam.location = mid + Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * span * 1.05
    cam.rotation_euler = (mid - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}-{i}.png"
    bpy.ops.render.render(write_still=True)
