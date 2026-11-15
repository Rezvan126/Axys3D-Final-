# Pulls the texture maps the finished Blender scene uses on the house (BlenderKit and scanned
# materials, packed in the .blend) and saves small tiling copies for the interactive web model.
#   blender -b <scene.blend> --python tools/extract-textures.py -- <out folder>
import bpy, sys, os
OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
# web name: (material in the scene, fragment of the image name)
WANT = {
    "siding": ("Wooden Planks.001", "Albedo"),
    "roof": ("Dark shingle", "diffuse"),
    "stucco": ("White Stucco Wall Texture", "albedo"),
    "plaster": ("Plaster", "color"),
    "deck": ("Wooden planks", "diffuse"),
    "wood": ("Wooden Planks", "_D"),
    "concrete": ("Concrete.001", "basecolor"),
    "grass": ("Grass", "diffuse"),
    "paving": ("Paving.001", "diffuse"),
}
s = bpy.context.scene
s.render.image_settings.file_format = "PNG"
for web, (mat, frag) in WANT.items():
    m = bpy.data.materials.get(mat)
    img = next((n.image for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and frag.lower() in n.image.name.lower()), None) if m else None
    if not img:
        print("MISSING", web); continue
    c = img.copy(); c.scale(1024, 1024)
    c.filepath_raw = os.path.join(OUT, web + ".png"); c.file_format = "PNG"; c.save()
    # how the material tints or remaps the map, for reference
    info = [(n.type, n.name) for n in m.node_tree.nodes if n.type in ("HUE_SAT", "RGB", "MIX", "MIX_RGB", "VALTORGB", "BRIGHTCONTRAST", "MAPPING", "GAMMA", "RGBCURVE")]
    print("TEX_OK", web, img.name, info)
