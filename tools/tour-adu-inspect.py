# What the studio's finished exterior scene holds, for the ADU virtual tour. Prints to the console only.
#   blender --disable-autoexec -b assets-src/gellert/scene.blend -P tools/tour-adu-inspect.py
# Collections, cameras, world, lights, and every mesh of the Revit house sorted by kind with its box.
# Object names in this file carry Revit text (and personal names): nothing here is written to any output file.
import bpy, re, collections
from mathutils import Vector

s = bpy.context.scene
D = bpy.data
SCRUB = re.compile(r"gellert|gelle|yoon|leong|morgan|fergus\w*|jpa|peders\w*|arnold|caroline|byron|bryan|koo\b|\[\d+\]|_[0-9a-f]{7}\b", re.I)
nm = lambda n: SCRUB.sub("", n)[:46]
def box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))
r = lambda v: [round(x, 2) for x in v]

print("ADU scene", s.name, s.render.engine, "world", s.world.name if s.world else None,
      s.view_settings.view_transform, s.view_settings.look, "ev", s.view_settings.exposure, "frame", s.frame_current)
def walk(c, d=0):
    obs = list(c.objects)
    print("ADU coll", "  " * d + nm(c.name), "own", len(obs), "all", len(c.all_objects), "hide_render", c.hide_render)
    for ch in c.children:
        walk(ch, d + 1)
walk(s.collection)
for o in s.objects:
    if o.type in ("CAMERA", "LIGHT"):
        print("ADU", o.type, nm(o.name), r(o.matrix_world.translation), getattr(o.data, "type", ""), getattr(o.data, "energy", ""), "hide", o.hide_render)
if s.world and s.world.node_tree:
    print("ADU world nodes", [(n.type, getattr(getattr(n, "image", None), "name", "")) for n in s.world.node_tree.nodes])

house = D.collections.get("Revit House")
if house is None:
    best = max(D.collections, key=lambda c: sum(1 for o in c.all_objects if re.search(r"basic wall", o.name, re.I)))
    house = best
print("ADU house collection", nm(house.name), len(house.all_objects))
lo = Vector((1e9,) * 3); hi = -lo
rows = []
for o in house.all_objects:
    if o.type != "MESH":
        continue
    a, b = box(o)
    lo = Vector(map(min, lo, a)); hi = Vector(map(max, hi, b))
    rows.append((round(a.z, 1), nm(o.name), r(a), r(b), [m.name[:20] for m in o.data.materials if m][:3], o.hide_render))
print("ADU house box", r(lo), r(hi))
rows.sort()
for row in rows:
    print("ADU M", row)
