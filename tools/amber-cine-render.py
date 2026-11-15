# Renders one shot of the amber film from scene-v3.blend.
#   blender --disable-autoexec -b assets-src/amber/scene-v3.blend -P tools/amber-cine-render.py -- <abs out> <a|b|c|d> [preview] [frames=1,60,120] [samples=N] [res=WxH]
# Finals skip frames that already exist, so a stopped render can be resumed by running it again.
import bpy, sys, os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:]
out, shot = argv[0], argv[1]
opts = {a.split("=")[0]: a.split("=")[1] for a in argv[2:] if "=" in a}
preview = "preview" in argv[2:]
spec = importlib.util.spec_from_file_location("cine", os.path.join(HERE, "amber-cine-shots.py"))
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
frames = [int(f) for f in opts["frames"].split(",")] if "frames" in opts else None
if "res" in opts:
    cs.RES = tuple(int(v) for v in opts["res"].split("x"))
cs.render_shot(out, shot, preview=preview, frames=frames, samples=int(opts["samples"]) if "samples" in opts else None)
