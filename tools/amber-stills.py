# Final stills of the amber house from the improved scene (views live in amber-views.py).
#   blender --disable-autoexec -b assets-src/amber/scene-v2.blend -P tools/amber-stills.py -- <abs out folder> [test] [view ...]
import bpy, sys, os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(argv[0])
TEST = "test" in argv[1:]
ONLY = [a for a in argv[1:] if a != "test"]

prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == kind
            break
    except Exception:
        continue
bpy.context.scene.cycles.device = "GPU"

spec = importlib.util.spec_from_file_location("amber_views", os.path.join(HERE, "amber-views.py"))
av = importlib.util.module_from_spec(spec); spec.loader.exec_module(av)
av.render_stills(OUT, ONLY, test=TEST)
print("STILLS_OK", flush=True)
