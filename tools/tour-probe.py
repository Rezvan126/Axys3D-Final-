# Finds candidate standpoints for the virtual tour from the geometry in tour.blend.
#   blender -b assets-src/amber/tour.blend -P tools/tour-probe.py -- [x y z ...]
#
# Without points: prints the room volumes from the model, the fittings (casework, furniture, plumbing) with
# their positions, and for every floor slab height a plan map of standing room at eye height
# (digit = clear distance to the nearest obstacle in 0.25 m steps, '.' = floor but blocked, ' ' = no floor).
# With points (triples): prints the clearance in 16 directions for each, to confirm a standpoint.
import bpy, sys, json, math, collections
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
s = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
SIZE = json.loads(s["size"])
EYE = 1.6
house = bpy.data.collections["house"]

def ring(p, n=16, far=30.0):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ok, loc, *_ = s.ray_cast(dg, p, Vector((math.sin(a), math.cos(a), 0)), distance=far)
        out.append((loc - p).length if ok else far)
    return out

if argv:
    v = [float(a) for a in argv]
    for i in range(0, len(v), 3):
        p = Vector(v[i:i + 3])
        ok, loc, nrm, idx, ob, _m = s.ray_cast(dg, p, Vector((0, 0, -1)))
        ok2, loc2, nrm2, idx2, ob2, _m2 = s.ray_cast(dg, p, Vector((0, 0, 1)))
        print("POINT", [round(c, 2) for c in p], "floor", round(p.z - loc.z, 2) if ok else None, ob.get("c") if ok else None,
              "ceiling", round(loc2.z - p.z, 2) if ok2 else None, ob2.get("c") if ok2 else None)
        print("   ring (from +y, clockwise):", " ".join(f"{d:.1f}" for d in ring(p)))
    sys.exit(0)

print("LEVELS", s["levels"], "FRONT", s["front"], "SIZE", SIZE)
for r in json.loads(s.get("rooms", "[]")):
    print("ROOM", r["l"], "|", r["n"], "|", r["lo"], r["hi"])

seen = collections.defaultdict(list)
for o in house.objects:
    if o["c"] in ("Casework", "Furniture", "Plumbing fixtures", "Specialty equipment", "Stairs", "Doors", "Generic models"):
        bb = [Vector(c) for c in o.bound_box]
        c = sum(bb, Vector()) / 8
        seen[(o["c"], o["t"], round(c.x, 0), round(c.y, 0), round(min(b.z for b in bb), 1))].append(o)
for (cat, t, x, y, z), obs in sorted(seen.items(), key=lambda k: (k[0][4], k[0][3])):
    print("ITEM", f"z{z:5.1f} x{x:5.0f} y{y:5.0f}", cat, "|", t)

STEP = 0.4
nx = int(SIZE[0] / STEP); ny = int(SIZE[1] / STEP)
cells = collections.defaultdict(dict)        # floor height bucket -> {(ix, iy): clearance}
for ix in range(nx + 1):
    for iy in range(ny + 1):
        x = -SIZE[0] / 2 + ix * STEP; y = -SIZE[1] / 2 + iy * STEP
        z = SIZE[2] + 1.0
        hits = []
        for _ in range(60):
            ok, loc, nrm, idx, ob, _m = s.ray_cast(dg, Vector((x, y, z)), Vector((0, 0, -1)))
            if not ok:
                break
            hits.append((loc.z, nrm.z, ob.get("c", "")))
            z = loc.z - 0.004
        for i, (hz, hn, hc) in enumerate(hits):
            if hc not in ("Floors", "Roofs") or hn < 0.5:
                continue
            if i > 0 and hits[i - 1][0] - hz < 2.0:
                cells[round(hz * 2) / 2].setdefault((ix, iy), -1)   # a lower layer of the slab, or something low over the floor
                continue
            d = min(ring(Vector((x, y, hz + EYE)), 12, 8.0))
            cells[round(hz * 2) / 2][(ix, iy)] = d
for z in sorted(cells):
    grid = cells[z]
    if sum(1 for d in grid.values() if d > 0.7) < 6:
        continue
    print(f"\nFLOOR z~{z}  (x left to right {-SIZE[0] / 2:.1f}..{SIZE[0] / 2:.1f}, y top = +{SIZE[1] / 2:.1f} street side if FRONT=1)")
    for iy in range(ny, -1, -1):
        row = ""
        for ix in range(nx + 1):
            d = grid.get((ix, iy))
            row += " " if d is None else ("." if d < 0.5 else str(min(9, int(d / 0.25))))
        print(f"y{-SIZE[1] / 2 + iy * STEP:6.1f} |{row}|")
