"""Clash test on a Revit FBX export: structure against mechanical, electrical and plumbing.

blender -b -P tools/clash-test.py -- <model.fbx> <out dir>

Writes clash.json (every clash above the tolerance, with the two elements, where it is and how deep)
and one picture per reported clash plus an overview, drawn the way a coordination view is drawn:
the two elements in colour, the rest of the building ghosted.
"""
import bpy, sys, os, re, json, math, importlib.util
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)
TOL = 0.012          # metres. Anything shallower is a touch, not a clash
SHOTS = 6

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)

# same naming and discipline rules as the website model, read from build-model.py without running it
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-model.py"), encoding="utf8").read()
ns = {"re": re}
exec(src[src.index("RULES = ["):src.index("# ---------------------------------------------------------------- join multi part families")], ns)
classify, clean_type = ns["classify"], ns["clean_type"]


def descendants(o):
    out = []
    for c in o.children:
        out.append(c); out.extend(descendants(c))
    return out

for cam in [o for o in bpy.data.objects if o.type in {"CAMERA", "LIGHT"}]:
    bpy.data.objects.remove(cam, do_unlink=True)
roots = [o for o in bpy.data.objects if o.type == "EMPTY" and (o.parent is None or o.parent.type != "EMPTY")]
for root in roots:
    kids = [c for c in descendants(root) if c.type == "MESH"]
    if not kids:
        continue
    bpy.ops.object.select_all(action="DESELECT")
    for k in kids:
        k.select_set(True)
    bpy.context.view_layer.objects.active = kids[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    if len(kids) > 1:
        bpy.ops.object.join()
    bpy.context.view_layer.objects.active.name = root.name
for e in [o for o in bpy.data.objects if o.type == "EMPTY"]:
    bpy.data.objects.remove(e, do_unlink=True)
bpy.context.view_layer.update()

meshes = [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.polygons)]
info = {}
for o in meshes:
    d, c = classify(o.name)
    info[o.name] = (d, c, clean_type(o.name))


def tree(o):
    m = o.matrix_world
    vs = [m @ v.co for v in o.data.vertices]
    o.data.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in o.data.loop_triangles]
    return BVHTree.FromPolygons(vs, tris, epsilon=0.0), vs, tris

cache = {}
def get(o):
    if o.name not in cache:
        cache[o.name] = tree(o)
    return cache[o.name]


def box(o):
    t, vs, _ = get(o)
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return lo, hi


def depth_into(vs_a, used_a, tree_b):
    """How far the deepest involved corner of A sits inside B."""
    best = 0.0
    for i in used_a:
        p = vs_a[i]
        loc, nor, _, dist = tree_b.find_nearest(p)
        if loc is None:
            continue
        if (p - loc).dot(nor) < 0:      # behind the nearest face: inside
            best = max(best, dist)
    return best

A = [o for o in meshes if info[o.name][0] == "structure"]
B = [o for o in meshes if info[o.name][0] in {"mechanical", "electrical", "plumbing"}]
print("structure", len(A), "services", len(B))

clashes, touches, pairs = [], 0, 0
for a in A:
    alo, ahi = box(a)
    for b in B:
        blo, bhi = box(b)
        if any(alo[k] > bhi[k] or blo[k] > ahi[k] for k in range(3)):
            continue
        pairs += 1
        ta, va, fa = get(a); tb, vb, fb = get(b)
        hit = ta.overlap(tb)
        if not hit:
            continue
        ua = {i for x, _ in hit for i in fa[x]}
        ub = {i for _, y in hit for i in fb[y]}
        dep = max(depth_into(va, ua, tb), depth_into(vb, ub, ta))
        # open (not watertight) Revit meshes make the inside test over read, so the overlap can never be
        # reported deeper than the thinnest shared dimension of the two elements
        dep = min(dep, min(min(ahi[k], bhi[k]) - max(alo[k], blo[k]) for k in range(3)))
        if dep < TOL:
            touches += 1
            continue
        pts = [va[i] for i in ua] + [vb[i] for i in ub]
        c = sum(pts, Vector()) / len(pts)
        clashes.append({"a": a.name, "b": b.name, "depth": dep, "at": c})

clashes.sort(key=lambda c: -c["depth"])
zs = [v.z for o in meshes for v in get(o)[1]] if False else None
allz = [box(o) for o in meshes]
zmin = min(b[0].z for b in allz); zmax = max(b[1].z for b in allz)

rows = []
for i, c in enumerate(clashes):
    da, ca, na = info[c["a"]]; db, cb, nb = info[c["b"]]
    rows.append({
        "id": f"C{i + 1:02d}",
        "a": {"cat": ca, "type": na}, "b": {"disc": db, "cat": cb, "type": nb},
        "depth_mm": round(c["depth"] * 1000),
        "at": [round(c["at"].x, 2), round(c["at"].y, 2), round(c["at"].z - zmin, 2)],
    })
by = {}
for r in rows:
    k = f'{r["a"]["cat"]} against {r["b"]["cat"]}'
    by[k] = by.get(k, 0) + 1
report = {
    "tested": {"structure": len(A), "services": len(B), "pairs_checked": pairs},
    "tolerance_mm": round(TOL * 1000),
    "clashes": len(rows), "touches_ignored": touches, "groups": by, "rows": rows,
}
json.dump(report, open(os.path.join(OUT, "clash.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in report.items() if k != "rows"}))
for r in rows[:12]:
    print(r)

# ---------------------------------------------------------------- pictures
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_shadows = False; sh.show_cavity = True
sh.show_object_outline = True; sh.object_outline_color = (0.05, 0.06, 0.08)
sc.display.render_aa = "16"
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.035, 0.04, 0.05)
sc.render.resolution_x, sc.render.resolution_y = 1400, 900
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"

cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam); sc.camera = cam
cam_d.clip_start = 0.05; cam_d.clip_end = 500

GHOST = (0.62, 0.66, 0.72, 0.07)
RED = (0.93, 0.20, 0.16, 1.0)
RED_SOFT = (0.93, 0.20, 0.16, 0.42)
GREEN = (0.20, 0.78, 0.42, 1.0)
STRUCT = (0.86, 0.87, 0.90, 0.9)
COL = {"mechanical": (0.25, 0.62, 0.95, 1), "electrical": (0.98, 0.72, 0.15, 1), "plumbing": (0.25, 0.80, 0.62, 1)}


def look(point, yaw, pitch, dist, lens=35):
    cam_d.lens = lens
    y, p = math.radians(yaw), math.radians(pitch)
    off = Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * dist
    cam.location = point + off
    cam.rotation_euler = (point - cam.location).to_track_quat("-Z", "Y").to_euler()


def shot(name):
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)

lo = Vector((min(b[0].x for b in allz), min(b[0].y for b in allz), zmin))
hi = Vector((max(b[1].x for b in allz), max(b[1].y for b in allz), zmax))
mid, span = (lo + hi) / 2, (hi - lo).length

# overview: structure solid, services coloured, the rest ghosted, a marker on every clash
for o in meshes:
    d = info[o.name][0]
    o.color = STRUCT if d == "structure" else COL.get(d, GHOST)
marks = []
for c in clashes:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.24, location=c["at"])
    m = bpy.context.active_object; m.color = RED; marks.append(m)
look(mid, 215, 30, span * 1.02, 40)
shot("overview.png")
for m in marks:
    bpy.data.objects.remove(m, do_unlink=True)

for i, c in enumerate(clashes[:SHOTS]):
    for o in meshes:
        o.color = GHOST
    a, b = bpy.data.objects[c["a"]], bpy.data.objects[c["b"]]
    alo, ahi = box(a)
    slab = (ahi.z - alo.z) < 0.7 and (ahi - alo).length > 4      # a floor: look up at it from below
    a.color, b.color = (RED_SOFT if slab else RED), GREEN
    blo, bhi = box(b)
    size = max((bhi - blo).length, 0.6)
    # look from the side of the building the clash is nearest to, so walls are not in the way
    out = c["at"] - mid
    yaw = math.degrees(math.atan2(out.y, out.x)) + 28
    look(c["at"], yaw, -26 if slab else 24, max(size * 2.6, 2.2), 40)
    shot(f"clash-{i + 1:02d}.png")
print("DONE")
