# What extra assets does the amber file hold: the second scene, objects in no scene, cars, plants.
#   blender --disable-autoexec -b assets-src/amber/scene-v2.blend -P tools/amber-cine-probe.py
import bpy
from mathutils import Vector
main = bpy.data.scenes["Scene"]
in_main = set(o.name for o in main.objects)
for sc in bpy.data.scenes:
    if sc.name != "Scene":
        print("CP SCENE", sc.name, [(o.name, o.type, len(o.data.polygons) if o.type == "MESH" else 0) for o in sc.objects])
orph = [o for o in bpy.data.objects if o.name not in in_main]
print("CP objects outside main scene", len(orph))
for o in orph[:80]:
    print("CP  ", o.name, o.type, len(o.data.polygons) if o.type == "MESH" else "", [c.name for c in o.users_collection], o.users)
print("CP collections not in main", [c.name for c in bpy.data.collections if c.name not in [x.name for x in main.collection.children_recursive]])
for k in ("car", "auto", "vehicle", "bird", "leaf", "plant", "bush", "grass", "flower", "tree", "shrub", "fern"):
    hits = [o.name for o in bpy.data.objects if k in o.name.lower()]
    print("CP name", k, len(hits), hits[:12])
print("CP node groups", [g.name for g in bpy.data.node_groups][:60])
print("CP materials", len(bpy.data.materials))
o = bpy.data.objects["tree.008"]
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for c in o.bound_box:
    p = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
print("CP tree.008 origin", tuple(round(v, 2) for v in o.matrix_world.translation), "bbox", tuple(round(v, 1) for v in lo), tuple(round(v, 1) for v in hi), "scale", tuple(o.scale))
for n in ("tree.001", "Cotoneáster.002", "Wild Grass Patch 2", "Grid.002", "Cylinder"):
    o = bpy.data.objects[n]
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    print("CP", n, "origin", tuple(round(v, 2) for v in o.matrix_world.translation), "bbox", tuple(round(v, 1) for v in lo), tuple(round(v, 1) for v in hi), "scale", tuple(round(v, 2) for v in o.scale), "rot", tuple(round(v, 2) for v in o.rotation_euler))
g = bpy.data.objects["Grid.002"].modifiers["Scatter on Surface"]
print("CP Grid.002 scatter inputs", [(k, (g[k].name if hasattr(g[k], "name") else str(g[k])[:40])) for k in g.keys()][:40])
for n in ("Toposolid Toposolid 1 [1794106]", "Toposolid Toposolid 1 [1794097]", "Toposolid Toposolid 1 [1794106].001", 'Basic Wall Generic - 3" [5021574].001'):
    o = bpy.data.objects.get(n)
    if o:
        print("CP topo", n, len(o.data.polygons), [m.type for m in o.modifiers], o.hide_render, [sl.material.name if sl.material else None for sl in o.material_slots])
print("CP blenderkit prefs", [a for a in bpy.context.preferences.addons.keys() if "blender" in a.lower() or "kit" in a.lower()])
