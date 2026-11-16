# Packs every external image (BlenderKit maps, the HDRI) into a tour scene so it opens anywhere,
# and drops the library links' file paths from view.
#   blender -b "<...>/02 Scenes/tour.blend" -P tools/tour-pack.py
import bpy

missing = [i.name for i in bpy.data.images if i.source == "FILE" and not i.packed_file and not i.has_data and not bpy.path.abspath(i.filepath)]
bpy.ops.file.pack_all()
left = [i.name for i in bpy.data.images if i.source == "FILE" and not i.packed_file]
print("PACK images", len(bpy.data.images), "not packed", left[:10], "missing before", missing[:10])
bpy.ops.wm.save_mainfile(compress=True)
print("PACK_OK", bpy.data.filepath)
