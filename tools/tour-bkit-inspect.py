# Lists what each downloaded BlenderKit file holds: for models the objects, their combined size and
# whether they share one root; for materials the material names, image sizes and texture coordinate setup.
#   blender -b --factory-startup -P tools/tour-bkit-inspect.py [-- <asset_base_id> ...]
import bpy, json, os, sys
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log = json.load(open(os.environ.get("BKIT_LOG") or os.path.join(ROOT, "assets-src", "amber", "tour", "bkit-assets.json")))   # BKIT_LOG: a per project log
ONLY = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for base_id, a in log.items():
    if ONLY and base_id not in ONLY:
        continue
    path = a["file"]
    if a["type"] == "hdr":
        print("INSPECT hdr", a["name"], "|", path); continue
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        if a["type"] == "model":
            dst.objects = list(src.objects)
        else:
            dst.materials = list(src.materials)
    if a["type"] == "model":
        obs = [o for o in dst.objects if o]
        for o in obs:
            bpy.context.scene.collection.objects.link(o)
        bpy.context.view_layer.update()
        mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
        for o in obs:
            if o.type != "MESH":
                continue
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
        roots = [o.name for o in obs if o.parent is None]
        mats = sorted({m.name for o in obs if o.type == "MESH" for m in o.data.materials if m})
        print("INSPECT model", a["name"], "| size", [round(v, 2) for v in (mx - mn)], "| min", [round(v, 2) for v in mn],
              "| objects", len(obs), "| roots", roots[:6], "| mats", mats[:8])
        for o in obs:
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        for m in dst.materials:
            if not m or not m.node_tree:
                continue
            imgs = [(n.image.name, tuple(n.image.size), n.projection) for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
            coords = [n.type for n in m.node_tree.nodes if n.type in ("TEX_COORD", "UVMAP", "MAPPING")]
            maps = [tuple(round(v, 3) for v in n.inputs["Scale"].default_value) for n in m.node_tree.nodes if n.type == "MAPPING"]
            groups = [n.node_tree.name for n in m.node_tree.nodes if n.type == "GROUP" and n.node_tree]
            print("INSPECT material", a["name"], "| mat", m.name, "| imgs", imgs[:5], "| coords", coords, "| mapping scale", maps, "| groups", groups)
            bpy.data.materials.remove(m)
