# Fault finding: what the fascia and other black parts really carry.
import bpy
for o in bpy.data.objects:
    if o.type == "MESH" and any(k in o.name for k in ("Fascia", "Facade Trim", "Canopy", "Basic Wall Generic - 3\"", "Monolithic Run 3/4")):
        me = o.data
        idx = sorted({p.material_index for p in me.polygons})
        print("P3", o.name[:50], "| slots", [(sl.link, sl.material.name if sl.material else None) for sl in o.material_slots],
              "| data mats", [m.name if m else None for m in me.materials], "| poly idx", idx,
              "| attrs", [a.name for a in me.color_attributes], "| mods", [m.type for m in o.modifiers])
for mn in ("Black Metal", "Black Metal.001", "Metal black"):
    m = bpy.data.materials[mn]
    print("P3 mat", mn, "users", m.users, "lib", m.library, [(n.type, n.name) for n in m.node_tree.nodes][:8],
          "displacement", m.displacement_method if hasattr(m, "displacement_method") else None)
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            for i in n.inputs:
                if i.name in ("Emission Color", "Emission Strength", "Base Color", "Sheen Weight", "Specular Tint", "Coat Tint", "Subsurface Weight"):
                    v = i.default_value
                    print("P3    ", i.name, list(v) if hasattr(v, "__len__") else v, "linked" if i.is_linked else "")
