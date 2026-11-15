# What is around a point: the first surfaces hit going up, down and to the four sides, with class and type.
#   blender -b assets-src/amber/tour.blend -P tools/tour-probe2.py -- x y z [x y z ...]
import bpy, sys
from mathutils import Vector
argv = [float(a) for a in sys.argv[sys.argv.index("--") + 1:]]
s = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
DIRS = {"up": (0, 0, 1), "down": (0, 0, -1), "+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0)}
for i in range(0, len(argv), 3):
    p = Vector(argv[i:i + 3])
    print("POINT", tuple(p))
    for name, d in DIRS.items():
        q = p.copy(); out = []
        for _ in range(5):
            ok, loc, nrm, idx, ob, _m = s.ray_cast(dg, q, Vector(d))
            if not ok:
                out.append("sky"); break
            out.append(f"{(loc - p).length:.2f}m {ob.name} {ob.get('c', '')}/{ob.get('k', '')}/{str(ob.get('t', ''))[:30]} dim{tuple(round(v, 1) for v in ob.dimensions)}")
            q = loc + Vector(d) * 0.01
        print("  ", name, " > ".join(out))
