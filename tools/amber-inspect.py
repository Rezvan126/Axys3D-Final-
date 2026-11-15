# Report on the amber scene: units, cameras, lights, world, collections, materials, modifiers, missing images.
#   blender --disable-autoexec -b assets-src/amber/scene.blend -P tools/amber-inspect.py -- <out.txt>
import bpy, sys, os
from mathutils import Vector
from collections import Counter, defaultdict

out = sys.argv[sys.argv.index("--") + 1]
L = []
def P(*a):
    L.append(" ".join(str(x) for x in a))

s = bpy.context.scene
P("FILE", bpy.data.filepath, "scenes", [x.name for x in bpy.data.scenes])
P("UNITS", s.unit_settings.system, s.unit_settings.scale_length, s.unit_settings.length_unit)
P("ENGINE", s.render.engine, s.render.resolution_x, s.render.resolution_y, "fps", s.render.fps, "frames", s.frame_start, s.frame_end)
P("VIEW", s.view_settings.view_transform, s.view_settings.look, s.view_settings.exposure)
P("ACTIVE CAM", s.camera.name if s.camera else None)

def bounds(obs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in obs:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi

def r(v, n=2):
    return [round(x, n) for x in v]

P("\n== CAMERAS")
for o in s.objects:
    if o.type == "CAMERA":
        q = o.matrix_world.to_quaternion()
        P(o.name, "loc", r(o.matrix_world.translation), "fwd", r(q @ Vector((0, 0, -1)), 3), "lens", o.data.lens, "sensor", o.data.sensor_width,
          "clip", o.data.clip_start, o.data.clip_end, "dof", o.data.dof.use_dof, "anim", bool(o.animation_data))

P("\n== LIGHTS")
for o in s.objects:
    if o.type == "LIGHT":
        d = o.data
        P(o.name, d.type, "energy", d.energy, "color", r(d.color), "loc", r(o.matrix_world.translation), "rot", r(o.rotation_euler), "hide_render", o.hide_render)

P("\n== WORLD")
w = s.world
if w:
    P(w.name, "nodes", w.use_nodes)
    if w.node_tree:
        for n in w.node_tree.nodes:
            extra = ""
            if n.type == "TEX_ENVIRONMENT":
                extra = (n.image.filepath if n.image else "none")
            P("  ", n.type, n.name, extra)

P("\n== COLLECTIONS")
def walk(c, d=0):
    obs = list(c.objects)
    polys = sum(len(o.data.polygons) for o in obs if o.type == "MESH")
    P("  " * d + c.name, "objects", len(obs), "polys", polys, "hide_render", c.hide_render)
    for ch in c.children:
        walk(ch, d + 1)
walk(s.collection)
vl = bpy.context.view_layer
def walk_lc(lc, d=0):
    if lc.exclude or lc.hide_viewport:
        P("  LAYERCOL", lc.name, "exclude", lc.exclude, "hide_viewport", lc.hide_viewport)
    for ch in lc.children:
        walk_lc(ch, d + 1)
walk_lc(vl.layer_collection)

P("\n== OBJECT TYPES", Counter(o.type for o in s.objects))
P("hidden render", len([o for o in s.objects if o.hide_render]), "hidden viewport", len([o for o in s.objects if o.hide_get()]))
ms = [o for o in s.objects if o.type == "MESH"]
lo, hi = bounds(ms)
P("BOUNDS", r(lo), r(hi), "size", r(hi - lo))

P("\n== MODIFIERS / PARTICLES")
mc = Counter()
for o in s.objects:
    for m in o.modifiers:
        mc[m.type] += 1
        if m.type in ("NODES", "PARTICLE_SYSTEM"):
            ng = m.node_group.name if m.type == "NODES" and m.node_group else ""
            P("  ", o.name, m.type, m.name, ng, "render", m.show_render)
    for ps in o.particle_systems:
        st = ps.settings
        P("   PS", o.name, ps.name, st.type, "count", st.count, "child", st.child_type, st.rendered_child_count, "render_as", st.render_type,
          "inst", st.instance_object.name if st.instance_object else (st.instance_collection.name if st.instance_collection else None))
P("modifier counts", dict(mc))
P("instancers", [(o.name, o.instance_type) for o in s.objects if o.instance_type != "NONE"][:40])

P("\n== OBJECTS (name | type | polys | size | centre | materials | collection)")
for o in sorted(s.objects, key=lambda o: o.name):
    if o.type != "MESH":
        P(o.name, "|", o.type, "| loc", r(o.matrix_world.translation), "| parent", o.parent.name if o.parent else None)
        continue
    lo2, hi2 = bounds([o])
    mats = [sl.material.name if sl.material else "-" for sl in o.material_slots]
    P(o.name, "|", len(o.data.polygons), "|", r(hi2 - lo2, 1), "|", r((lo2 + hi2) / 2, 1), "|", mats[:6], "|", [c.name for c in o.users_collection],
      "| HR" if o.hide_render else "", "| uv" if o.data.uv_layers else "| nouv")

P("\n== MATERIALS (name | users | summary)")
use = Counter()
polyuse = Counter()
for o in ms:
    for i, sl in enumerate(o.material_slots):
        if sl.material:
            use[sl.material.name] += 1
for m in bpy.data.materials:
    desc = ""
    if m.node_tree:
        types = Counter(n.type for n in m.node_tree.nodes)
        bs = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bs:
            def val(nm):
                i = bs.inputs.get(nm)
                if i is None: return "?"
                if i.is_linked:
                    fn = i.links[0].from_node
                    return "<" + fn.type + (":" + fn.image.name if fn.type == "TEX_IMAGE" and fn.image else "") + ">"
                v = i.default_value
                try: return r(list(v)[:3])
                except TypeError: return round(v, 3)
            desc = f"base {val('Base Color')} rough {val('Roughness')} metal {val('Metallic')} trans {val('Transmission Weight')} alpha {val('Alpha')} norm {val('Normal')} emis {val('Emission Strength')}"
        desc += " | nodes " + ",".join(f"{k}{v}" for k, v in types.items())
    else:
        desc = "no nodes, diffuse " + str(r(list(m.diffuse_color)))
    P(m.name, "|", use[m.name], "|", desc)

P("\n== IMAGES")
miss = 0
for im in bpy.data.images:
    packed = im.packed_file is not None
    path = bpy.path.abspath(im.filepath) if im.filepath else ""
    exists = os.path.exists(path) if path else False
    if not packed and not exists and im.source == "FILE":
        miss += 1
    P(im.name, "|", im.source, "|", list(im.size), "| packed" if packed else ("| ondisk" if exists else "| MISSING"), "|", im.filepath[-70:])
P("MISSING COUNT", miss, "of", len(bpy.data.images))

P("\n== TEXT / FONT OBJECTS")
for o in s.objects:
    if o.type == "FONT":
        P(o.name, repr(o.data.body), r(o.matrix_world.translation))

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("INSPECT_OK", len(L))
