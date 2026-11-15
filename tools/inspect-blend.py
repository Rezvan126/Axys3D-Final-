"""Quick look at a .blend: what is in it and a clay preview from a three quarter angle.
blender --disable-autoexec -b <file.blend> -P tools/inspect-blend.py -- <out.png>
"""
import bpy, sys, math
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene
ms = [o for o in sc.objects if o.type == "MESH" and not o.hide_render]
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
tris = 0
for o in ms:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    tris += len(o.data.polygons)
print("INFO objects", len(sc.objects), "meshes", len(ms), "polys", tris, "size", [round(v, 2) for v in (hi - lo)],
      "materials", len(bpy.data.materials), "images", len(bpy.data.images), "cameras", len([o for o in sc.objects if o.type == "CAMERA"]),
      "engine", sc.render.engine, "unit", sc.unit_settings.system, sc.unit_settings.scale_length)
print("INFO names", [o.name[:28] for o in ms[:14]])
print("INFO mats", [m.name[:24] for m in bpy.data.materials[:16]])
mid = (lo + hi) / 2; span = (hi - lo).length
cd = bpy.data.cameras.new("insp"); cam = bpy.data.objects.new("insp", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.lens = 40; cd.clip_start = span / 1000; cd.clip_end = span * 20
y, p = math.radians(215), math.radians(28)
cam.location = mid + Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * span * 1.15
cam.rotation_euler = (mid - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"; sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 900, 600, 100
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
