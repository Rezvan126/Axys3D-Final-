# Plan cuts and quick looks for the ADU virtual tour, straight from the finished exterior scene. Nothing is saved.
#   blender --disable-autoexec -b assets-src/gellert/scene.blend -P tools/tour-adu-probe.py -- plan <abs out folder> z [z ...]
#   blender --disable-autoexec -b assets-src/gellert/scene.blend -P tools/tour-adu-probe.py -- rays <x> <y> <z>
# plan: orthographic workbench cuts over the ADU (x 18 to 32, y 2 to 11), 50 px per metre, clipped 1.2 m under z.
#       pixel (px, py) -> x = 18 + px / 50, y = 11 - py / 50
# rays: what a standpoint sees around it (distance to the first surface every 30 degrees, and what it is).
import bpy, sys, os, re, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
s = bpy.context.scene
D = bpy.data
SCRUB = re.compile(r"gellert|gelle|yoon|leong|morgan|fergus\w*|jpa|peders\w*|arnold|caroline|byron|bryan|koo\b|\[\d+\]|_[0-9a-f]{7}\b", re.I)

if argv[0] == "plan":
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    for o in D.objects:
        if o.type == "MESH" and o.users_collection and o.users_collection[0].name in ("SJ-garden beautiful Bloom", "Vegetation", "Topo"):
            o.hide_render = True
    cd = D.cameras.new("plan"); cam = D.objects.new("plan", cd); s.collection.objects.link(cam); s.camera = cam
    cd.type = "ORTHO"; cd.ortho_scale = 14.0
    s.render.engine = "BLENDER_WORKBENCH"
    s.display.shading.light = "STUDIO"; s.display.shading.color_type = "OBJECT"; s.display.shading.show_cavity = True
    s.render.resolution_x, s.render.resolution_y = 700, 450
    s.render.image_settings.file_format = "JPEG"
    for i, o in enumerate(D.objects):
        o.color = ((i * 0.37) % 1 * 0.6 + 0.3, (i * 0.61) % 1 * 0.6 + 0.3, (i * 0.83) % 1 * 0.6 + 0.3, 1)
    for z in [float(v) for v in argv[2:]]:
        cam.location = (25.0, 6.5, z); cam.rotation_euler = (0, 0, 0)
        cd.clip_start = 0.01; cd.clip_end = 1.2
        s.render.filepath = os.path.join(out, f"plan-z{z:.1f}.jpg")
        bpy.ops.render.render(write_still=True)
        print("PLAN", z)
    sys.exit(0)

if argv[0] == "rays":
    p = Vector([float(v) for v in argv[1:4]])
    dg = bpy.context.evaluated_depsgraph_get()
    for a in range(0, 360, 30):
        d = Vector((math.sin(math.radians(a)), math.cos(math.radians(a)), 0))
        ok, loc, nrm, idx, ob, _ = s.ray_cast(dg, p, d, distance=30)
        print("RAY", a, round((loc - p).length, 2) if ok else None, SCRUB.sub("", ob.name)[:40] if ok else "")
    for d in ((0, 0, -1), (0, 0, 1)):
        ok, loc, nrm, idx, ob, _ = s.ray_cast(dg, p, Vector(d), distance=30)
        print("RAY", d, round(loc.z, 3) if ok else None, SCRUB.sub("", ob.name)[:40] if ok else "")
