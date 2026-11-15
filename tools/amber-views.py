# Camera positions for the amber house stills. Used by amber-setup.py (tests) and amber-stills.py (finals).
# Output order for the site: hero, low34, entry, upper, wide, uphill = amber-1 .. amber-6.
# Scene units; the facade faces +X, the street climbs towards +Y. Hero house: y 96.5 to 115, z 23 to 37.5.
import bpy, os, time
from mathutils import Vector

# name: (camera position, look at, lens mm, f-stop, vertical lens shift)
# A lens shift other than 0 means a level camera (upright verticals): the look-at height is ignored and the
# frame is moved up with the shift instead.
VIEWS = {
    # 1 street hero: from the far pavement, slightly down the hill
    "hero":    ((49.4, 98.0, 23.4), (-15.0, 106.2, 30.0), 68, 1.6, 0.25),
    # 2 low three quarter from the street just below the house, facade in raking light
    "low34":   ((4.5, 99.0, 22.1), (-16.0, 109.0, 30.4), 21, 1.8, 0.30),
    # 3 entry and garage close-up
    "entry":   ((6.5, 112.5, 25.6), (-16.0, 106.0, 26.8), 50, 1.6, 0.0),
    # 4 upper windows and fascia
    "upper":   ((15.0, 95.0, 24.0), (-13.2, 102.2, 34.4), 100, 2.0, 0.0),
    # 5 wide establishing with the hillside
    "wide":    ((64.0, 80.0, 25.0), (-25.0, 105.0, 35.0), 40, 2.8, 0.13),
    # 6 three quarter from up the street, past the street tree
    "uphill":  ((8.0, 128.0, 28.9), (-15.5, 105.0, 29.5), 35, 1.8, 0.05),
}

def make_cam(name, pos, aim, lens, fstop, shift=0.0):
    s = bpy.context.scene
    pos, aim = Vector(pos), Vector(aim)
    if shift:
        aim.z = pos.z
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); s.collection.objects.link(cam)
    cam.location = pos
    cam.rotation_euler = (aim - pos).to_track_quat("-Z", "Y").to_euler()
    cd.lens = lens; cd.sensor_width = 36.0; cd.clip_start = 0.3; cd.clip_end = 5000
    cd.shift_y = shift
    cd.dof.use_dof = True; cd.dof.focus_distance = (aim - pos).length; cd.dof.aperture_fstop = fstop
    return cam

def render_stills(out, only=(), test=False, samples=None):
    s = bpy.context.scene
    os.makedirs(out, exist_ok=True)
    s.cycles.samples = samples or (28 if test else 220)
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = (720, 405, 100) if test else (2400, 1350, 100)
    s.render.image_settings.file_format = "JPEG"; s.render.image_settings.quality = 95
    s.render.use_motion_blur = False
    for name, (pos, aim, lens, fstop, shift) in VIEWS.items():
        if only and name not in only:
            continue
        path = os.path.join(out, f"{name}.jpg")
        if not test and os.path.exists(path):
            continue
        s.camera = make_cam("amber_" + name, pos, aim, lens, fstop, shift)
        s.render.filepath = path
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("VIEW_OK", name, round(time.time() - t, 1), "s", flush=True)
