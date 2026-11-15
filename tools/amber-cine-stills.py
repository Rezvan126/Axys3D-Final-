# Full quality 16:9 stills taken from the film's own cameras at chosen frames (2400x1350, rendered as stills,
# not pulled from the motion blurred film frames).
#   blender --disable-autoexec -b assets-src/amber/scene-v3.blend -P tools/amber-cine-stills.py -- <abs out> <shot> <frame>:<name> [...]
# One Blender run per shot (the shot rig keys exposure and the sun, so it is built once per run).
import bpy, sys, os, time, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:]
out, shot, picks = os.path.abspath(argv[0]), argv[1], argv[2:]
spec = importlib.util.spec_from_file_location("cine", os.path.join(HERE, "amber-cine-shots.py"))
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
os.makedirs(out, exist_ok=True)
cs.setup_render(False, samples=int(os.environ.get("AMBER_STILL_SAMPLES", "160")), res=(2400, 1350))
s = bpy.context.scene
s.render.use_motion_blur = False
cs.build(shot)
for p in picks:
    f, name = p.split(":")
    s.frame_set(int(f))
    s.render.filepath = os.path.join(out, name + ".jpg")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print("STILL", name, shot, f, round(time.time() - t, 1), "s", flush=True)
