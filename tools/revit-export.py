"""Export a Revit project's default 3D view to FBX by replaying a journal in Revit 2026.

python tools/revit-export.py <model.rvt> <out.fbx> [wait seconds]

Revit opens on screen, runs the steps in tools/revit-export-fbx.txt and quits without saving.
"""
import sys, os, subprocess, time
rvt, fbx = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
wait = int(sys.argv[3]) if len(sys.argv) > 3 else 900
here = os.path.dirname(os.path.abspath(__file__))
work = os.path.dirname(fbx)
os.makedirs(work, exist_ok=True)
txt = open(os.path.join(here, "revit-export-fbx.txt"), encoding="utf8").read()
txt = txt.replace("RVT_PATH", rvt).replace("FBX_PATH", fbx)
jrn = os.path.join(work, "export.txt")
open(jrn, "w", encoding="utf8", newline="\r\n").write(txt)
p = subprocess.Popen([r"C:\Program Files\Autodesk\Revit 2026\Revit.exe", jrn, "/nosplash"])
print("revit pid", p.pid, flush=True)
t0 = time.time()
while time.time() - t0 < wait:
    time.sleep(5)
    if p.poll() is not None:
        print("revit exited", p.returncode, "after", round(time.time() - t0), "s"); break
else:
    print("still running after", wait, "s: left open, pid", p.pid)
print("fbx", os.path.exists(fbx), os.path.getsize(fbx) if os.path.exists(fbx) else 0)
