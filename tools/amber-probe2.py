# Geometry facts needed to dress the amber scene: road and pavement outline, hill outline, sky enum, film settings.
#   blender --disable-autoexec -b assets-src/amber/scene.blend -P tools/amber-probe2.py
import bpy
from mathutils import Vector
s = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

def r(v): return tuple(round(x, 1) for x in v)

for name in ("ROAD", 'Floor Concrete 6" Thick new [1794082]', 'Floor Concrete 6" Thick new [1792510]'):
    o = bpy.data.objects[name]
    me = o.data
    print("P2", name, "verts", len(me.vertices), "mods", [m.type for m in o.modifiers], "scale", r(o.scale), "rot", r(o.rotation_euler))
    pts = sorted({r(o.matrix_world @ v.co) for v in me.vertices}, key=lambda p: (p[1], p[0]))
    print("P2   ", pts[:60])
    m = o.material_slots[0].material
    for n in m.node_tree.nodes:
        if n.type == "MAPPING":
            print("P2    mapping", n.vector_type, [list(i.default_value) for i in n.inputs[1:]], "from", [l.from_socket.name for l in n.inputs[0].links])

o = bpy.data.objects["Cube"]
pts = [o.matrix_world @ v.co for v in o.data.vertices]
print("P2 hill verts", len(pts))
for ylo in range(-40, 140, 20):
    row = [p for p in pts if ylo <= p.y < ylo + 20]
    if row:
        print("P2 hill y", ylo, "x", round(min(p.x for p in row), 1), round(max(p.x for p in row), 1), "z", round(min(p.z for p in row), 1), round(max(p.z for p in row), 1),
              "z at max x", round(max(row, key=lambda p: p.x).z, 1))
for m in o.modifiers:
    print("P2 hill mod", m.type, m.name)
    if m.type == "NODES":
        for n in m.node_group.nodes:
            if n.type == "DISTRIBUTE_POINTS_ON_FACES":
                print("P2    distribute", n.distribute_method, [(i.name, i.default_value) for i in n.inputs if hasattr(i, "default_value") and not i.is_linked])
            if n.type == "INSTANCE_ON_POINTS":
                print("P2    instance", [(i.name, str(i.default_value)) for i in n.inputs if hasattr(i, "default_value") and not i.is_linked])
print("P2 hill grass mat", [(n.type, n.name) for n in bpy.data.materials["Grass"].node_tree.nodes])
for n in ("tree.001", "tree.005", "tree.008", "Cotoneáster.002", "Cotoneáster.003", "Cotoneáster.004", "Wild Grass Patch 2", "Trunk.002"):
    o = bpy.data.objects[n]
    print("P2 obj", n, "loc", r(o.matrix_world.translation), "scale", r(o.scale), "data", o.data.name, "users", o.data.users, "mods", [m.type for m in o.modifiers])

# ray casts down to learn ground heights along the street
for x in (-20, -10, 0, 20, 40, 60):
    row = []
    for y in (30, 50, 70, 90, 105, 120, 140, 160, 180):
        hit, loc, nor, idx, ob, mat = s.ray_cast(dg, Vector((x, y, 200)), Vector((0, 0, -1)))
        row.append((y, round(loc.z, 1), ob.name[:10]) if hit else (y, None))
    print("P2 ground x", x, row)

print("P2 film transparent", s.render.film_transparent, "view", s.view_settings.view_transform, s.view_settings.look, "exposure", s.view_settings.exposure, s.cycles.film_exposure)
wt = bpy.data.worlds.new("t"); wt.use_nodes = True
sk = wt.node_tree.nodes.new("ShaderNodeTexSky")
print("P2 sky types", [e.identifier for e in sk.bl_rna.properties["sky_type"].enum_items], "default", sk.sky_type)
print("P2 sky props", [p.identifier for p in sk.bl_rna.properties if not p.is_readonly])
print("P2 looks", [e.identifier for e in s.view_settings.bl_rna.properties["look"].enum_items][:40])
print("P2 transforms", [e.identifier for e in s.view_settings.bl_rna.properties["view_transform"].enum_items])
b = bpy.data.materials.new("t").node_tree if False else None
m = bpy.data.materials.new("t"); m.use_nodes = True
bs = m.node_tree.nodes["Principled BSDF"]
print("P2 principled inputs", [i.name for i in bs.inputs])
print("P2 glass group inputs", [(i.name, getattr(i, "default_value", None)) for i in bpy.data.materials["Glass.002"].node_tree.nodes["Group"].inputs])
g = bpy.data.node_groups["Procedural Glass"]
p = next(n for n in g.nodes if n.type == "BSDF_PRINCIPLED")
print("P2 glass principled", [(i.name, (list(i.default_value) if hasattr(i.default_value, "__len__") else i.default_value)) for i in p.inputs if not i.is_linked and hasattr(i, "default_value") and i.name in ("Base Color", "Roughness", "Transmission Weight", "IOR", "Alpha")], "linked", [i.name for i in p.inputs if i.is_linked])
print("P2 plaster group inputs", [(i.name, (list(i.default_value) if hasattr(i.default_value, "__len__") else i.default_value)) for i in bpy.data.materials["Plaster"].node_tree.nodes["Group"].inputs if hasattr(i, "default_value")])
print("P2 plaster mapping", [list(i.default_value) for i in bpy.data.materials["Plaster"].node_tree.nodes["Mapping"].inputs[1:]], bpy.data.materials["Plaster"].node_tree.nodes["RGB"].outputs[0].default_value[:], bpy.data.materials["Plaster"].node_tree.nodes["Value"].outputs[0].default_value)
print("P2 gpu", bpy.context.preferences.addons["cycles"].preferences.compute_device_type)
