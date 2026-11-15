# Reads BlenderKit asset blends already in the local cache (no downloads): what each holds, its asset ids and licence.
#   blender --factory-startup -b -P tools/amber-bk-probe.py -- <blend> [<blend> ...]
import bpy, sys, os, json
from mathutils import Vector

def props(idb):
    out = {}
    bk = idb.get("asset_data") if hasattr(idb, "get") else None
    for k in idb.keys():
        try:
            v = idb[k]
            v = v.to_dict() if hasattr(v, "to_dict") else v
            out[k] = v
        except Exception:
            pass
    return out

for path in sys.argv[sys.argv.index("--") + 1:]:
    before_m = set(bpy.data.materials); before_o = set(bpy.data.objects); before_c = set(bpy.data.collections)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        names = {"materials": list(src.materials), "objects": list(src.objects), "collections": list(src.collections)}
        if src.collections:
            dst.collections = list(src.collections)
        elif src.objects:
            dst.objects = list(src.objects)
        dst.materials = list(src.materials)
    print("BK FILE", os.path.basename(os.path.dirname(path)), "|", {k: v[:6] for k, v in names.items()})
    for m in set(bpy.data.materials) - before_m:
        p = props(m)
        bk = p.get("asset_data") or {}
        print("BK   MAT", m.name, "| keys", list(p.keys())[:8], "| ad", m.asset_data is not None)
        if m.asset_data:
            print("BK     tags", list(m.asset_data.tags.keys())[:6], "desc", (m.asset_data.description or "")[:80], "author", getattr(m.asset_data, "author", ""), "license", getattr(m.asset_data, "license", ""), "copyright", getattr(m.asset_data, "copyright", ""))
        if "asset_data" in p:
            ad = p["asset_data"]
            print("BK     bk", {k: ad.get(k) for k in ("name", "assetBaseId", "id", "license", "isFree", "canDownload", "author", "displayName") if isinstance(ad, dict)})
    for c in set(bpy.data.collections) - before_c:
        objs = list(c.all_objects)
        lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3); polys = 0
        for o in objs:
            if o.type == "MESH":
                polys += len(o.data.polygons)
                for cc in o.bound_box:
                    q = o.matrix_world @ Vector(cc); lo = Vector(map(min, lo, q)); hi = Vector(map(max, hi, q))
        print("BK   COLL", c.name, "objs", len(objs), "polys", polys, "size", tuple(round(v, 2) for v in (hi - lo)), "min", tuple(round(v, 2) for v in lo))
        p = props(c)
        if "asset_data" in p and isinstance(p["asset_data"], dict):
            ad = p["asset_data"]
            print("BK     bk", {k: ad.get(k) for k in ("name", "assetBaseId", "id", "license", "isFree", "author")})
        else:
            print("BK     keys", list(p.keys())[:10])
            for o in objs[:3]:
                po = props(o)
                if "asset_data" in po and isinstance(po["asset_data"], dict):
                    ad = po["asset_data"]
                    print("BK     obj bk", o.name, {k: ad.get(k) for k in ("name", "assetBaseId", "id", "license", "isFree")})
                else:
                    print("BK     obj keys", o.name, list(po.keys())[:8], "mods", [m.type for m in o.modifiers], "parent", o.parent.name if o.parent else None)
    for o in set(bpy.data.objects) - before_o:
        if not o.users_collection or all(c in before_c for c in o.users_collection):
            if o.type == "MESH":
                po = props(o)
                print("BK   OBJ", o.name, len(o.data.polygons), "keys", list(po.keys())[:8], "dims", tuple(round(v, 2) for v in o.dimensions))
                if "asset_data" in po and isinstance(po["asset_data"], dict):
                    ad = po["asset_data"]
                    print("BK     bk", {k: ad.get(k) for k in ("name", "assetBaseId", "id", "license", "isFree")})
