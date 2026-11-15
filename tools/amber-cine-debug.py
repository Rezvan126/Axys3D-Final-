# Fault finding for the leaf shadows: what a ray from the facade towards the sun meets.
#   blender --disable-autoexec -b assets-src/amber/scene-v3.blend -P tools/amber-cine-debug.py
import bpy, math
from mathutils import Vector
s = bpy.context.scene
sky = next(n for n in s.world.node_tree.nodes if n.type == "TEX_SKY")
el = sky.sun_elevation; az = math.pi / 2 - sky.sun_rotation
sv = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
print("DBG sun el", round(math.degrees(el), 1), "az from normal", round(math.degrees(az), 1), "vec", tuple(round(v, 3) for v in sv))
dg = bpy.context.evaluated_depsgraph_get()
for (x, y, z) in ((-13.0, 100.0, 33.5), (-13.5, 106.0, 31.5), (-16.0, 109.5, 27.5), (-12.8, 97.0, 28.0), (-13.0, 102.0, 35.0)):
    p = Vector((x, y, z)) + sv * 0.3
    hit, loc, nor, idx, ob, mat = s.ray_cast(dg, p, sv)
    print("DBG from", (x, y, z), "->", ob.name if hit else None, tuple(round(v, 1) for v in loc) if hit else "", "dist", round((loc - p).length, 1) if hit else "")
for o in s.objects:
    if o.name.startswith("amber_maple"):
        print("DBG", o.name, tuple(round(v, 1) for v in o.location), tuple(round(v, 2) for v in o.scale), o.instance_collection.name, tuple(o.instance_collection.instance_offset))
        # leaf canopy position in the world through the instance
        for c in o.instance_collection.all_objects:
            if c.type == "MESH" and "leaf" in c.name.lower():
                lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
                for cc in c.bound_box:
                    q = o.matrix_world @ (c.matrix_world @ Vector(cc) - o.instance_collection.instance_offset)
                    lo = Vector(map(min, lo, q)); hi = Vector(map(max, hi, q))
                print("DBG    canopy", c.name, tuple(round(v, 1) for v in lo), tuple(round(v, 1) for v in hi), "hide_render", c.hide_render, "vis shadow", c.visible_shadow)
coll = bpy.data.collections.get("Ahorn tree")
if coll:
    for c in coll.all_objects:
        print("DBG ahorn obj", c.name, c.type, c.hide_render, [m.type for m in c.modifiers], c.particle_systems[:] if c.type == "MESH" else "", tuple(round(v, 2) for v in c.matrix_world.translation))

# coverage map of the front: '#' shaded, '.' in sun (rows top to bottom z 37 -> 24, columns y 96 -> 116)
print("DBG map")
for z in (37, 35, 33, 31, 29, 27, 25):
    row = ""
    for y in [96 + i for i in range(21)]:
        x = -13.0 if z > 30 else -15.5
        p = Vector((x, y, z)) + sv * 0.3
        hit, loc, nor, idx, ob, mat = s.ray_cast(dg, p, sv)
        lit = (not hit) or ob.name == "amber_haze"
        row += "." if lit else ("#" if (loc - p).length > 3 else "o")
    print("DBG  ", z, row)
from collections import Counter
cnt = Counter()
for z in (37, 35, 33, 31, 29, 27, 25):
    for y in [96 + i for i in range(21)]:
        x = -13.0 if z > 30 else -15.5
        p = Vector((x, y, z)) + sv * 0.3
        hit, loc, nor, idx, ob, mat = s.ray_cast(dg, p, sv)
        if hit and (loc - p).length > 3 and ob.name != "amber_haze":
            cnt[(ob.name[:40], round((loc - p).length / 10) * 10)] += 1
print("DBG blockers", cnt.most_common(12))

# trace from points actually on the facade (found by casting from the street towards the house)
cnt = Counter(); lit = 0; tot = 0
for z in (25, 27, 29, 31, 33, 35):
    for y in range(96, 117, 2):
        h, p, n, *_r = s.ray_cast(dg, Vector((5.0, y, z)), Vector((-1, 0, 0)))
        if not h:
            continue
        tot += 1
        hit, loc, nor, idx, ob, mat = s.ray_cast(dg, p + n * 0.05, sv)
        if (not hit) or ob.name == "amber_haze":
            lit += 1
        else:
            cnt[(ob.name[:36], round((loc - p).length / 10) * 10)] += 1
print("DBG facade lit", lit, "of", tot, "blockers", cnt.most_common(10))
