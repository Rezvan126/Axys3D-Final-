# Renders the virtual tour panoramas from assets-src/amber/tour.blend and writes the tour data for the site.
#
#   blender -b assets-src/amber/tour.blend -P tools/tour-render.py -- plan  <out folder>            plan cuts per floor (to choose standpoints)
#   blender -b assets-src/amber/tour.blend -P tools/tour-render.py -- test  <out folder> [slug ..]  1024x512 look tests
#   blender -b assets-src/amber/tour.blend -P tools/tour-render.py -- final <out folder> [slug ..]  4096x2048 finals
#   blender -b assets-src/amber/tour.blend -P tools/tour-render.py -- json  <src/data/tour.json>    rooms, hotspots, start views
#   blender -b assets-src/amber/tour.blend -P tools/tour-render.py -- at    <out folder> x y z      one test from a free point
#
# Equirectangular convention (the viewer uses the same): the image centre looks along +y, yaw grows clockwise
# seen from above (towards +x), pitch is up. So yaw = atan2(dx, dy).
import bpy, sys, os, json, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT = argv[0], argv[1]
REST = argv[2:]
s = bpy.context.scene
D = bpy.data
EYE = 1.6

# Standpoints. x, y in metres from the middle of the plan, fz = finished floor height under the point.
# "look" is the yaw the visitor starts with. "to" lists the rooms an arrow leads to.
ROOMS = [
    {"slug": "entry", "name": "Entry", "floor": "Ground floor", "p": (1.55, 5.2), "fz": 2.07, "look": 150, "ev": 0.4, "to": ["living"],
     "aim": {"living": (162, 6)}},                                   # the stair, not the room straight overhead
    {"slug": "living", "name": "Living and dining", "floor": "Second floor", "p": (0.2, 5.9), "fz": 5.34, "look": 40, "to": ["kitchen", "bedroom", "entry"],
     # the open slider to the stair hall (down to the entry, up to the bedrooms) and the open kitchen door
     "aim": {"entry": (127, -14), "bedroom": (141, 2), "kitchen": (237, -8)}},
    {"slug": "kitchen", "name": "Kitchen", "floor": "Second floor", "p": (-1.7, 1.5), "fz": 5.34, "look": 275, "to": ["living"],
     "aim": {"living": (320, -8)}},                                  # the open door to the dining end, right of the fridge
    # the three rooms at the back are shot with the sun behind the house, low and warm, so light reaches the deck
    {"slug": "bedroom", "name": "Primary bedroom", "floor": "Third floor", "p": (2.2, -6.7), "fz": 6.66, "look": 60, "ev": 0.3, "sun": (200, 22), "to": ["deck", "bathroom", "living"],
     "aim": {"deck": (159, -12), "bathroom": (359, -8), "living": (339, -6)}},   # deck slider, bath door, hall door
    {"slug": "bathroom", "name": "Primary bath", "floor": "Third floor", "p": (3.6, -0.95), "fz": 6.66, "look": 90, "ev": 0.4, "sun": (200, 22), "to": ["bedroom"],
     "aim": {"bedroom": (199, -14)}},                                # the open door back to the bedroom (via the closet)
    {"slug": "deck", "name": "Back deck", "floor": "Third floor", "p": (0.0, -9.6), "fz": 6.6, "look": 20, "ev": 0.1, "sun": (200, 22), "to": ["bedroom"],
     "aim": {"bedroom": (59, -5)}},                                  # the open bedroom slider
]
FRONT = s.get("front", 1)
# Tried and left out after looking at test renders: ground floor office (3.6, 6.2) one blank dark panel on the wall,
# stair hall (2.9, 2.8) and third floor landing (-1.4, -2.6) closed doors on every side, second bathroom (-3.9, -1.2) dark with an odd boxed fixture.
BY = {r["slug"]: r for r in ROOMS}

def eye(r):
    """Eye height above the real floor under the point (the slab is found by a ray, fz is only where to start looking)."""
    x, y = r["p"]
    dg = bpy.context.evaluated_depsgraph_get()
    ok, loc, *_ = s.ray_cast(dg, Vector((x, y, r["fz"] + 1.0)), Vector((0, 0, -1)), distance=2.5)
    fz = loc.z if ok else r["fz"]
    r["fz"] = round(fz, 3)
    return Vector((x, y, fz + r.get("eye", EYE)))

# ---------------------------------------------------------------- data for the site
if MODE == "json":
    rooms = []
    for r in ROOMS:
        a = eye(r)
        spots = []
        for slug in r["to"]:
            t = BY[slug]
            b = eye(t)
            d = b - a
            flat = math.hypot(d.x, d.y)
            yaw = math.degrees(math.atan2(d.x, d.y)) % 360
            # aim at the floor under the next standpoint, kept inside a comfortable band
            pitch = math.degrees(math.atan2((t["fz"] + 0.2) - a.z, max(flat, 0.5)))
            pitch = max(-22.0, min(12.0, pitch))
            ov = r.get("aim", {}).get(slug)
            if ov:
                yaw, pitch = ov
            spots.append({"to": slug, "yaw": round(yaw, 1), "pitch": round(pitch, 1)})
        rooms.append({"slug": r["slug"], "name": r["name"], "floor": r["floor"], "yaw": r["look"], "pitch": r.get("tilt", 0), "spots": spots})
    # merge into the library file: the fields the library owns (summary, poster_alt, order ...) are kept
    data = json.load(open(OUT, encoding="utf8")) if os.path.exists(OUT) else {}
    data.update({
        "slug": data.get("slug", "hillside"),
        "project": data.get("project", "Split level residence"),
        "summary": data.get("summary", "A house stepped into a hillside, walked from the front door up to the primary suite and its back deck."),
        "rooms_count": len(rooms),
        "title": "Split level residence",
        "note": "Six 360 degree views rendered from the studio's Revit model and virtually staged.",
        "size": [int(os.environ.get("TOUR_RES", "4096")), int(os.environ.get("TOUR_RES", "4096")) // 2], "small": [2048, 1024],
        "rooms": rooms,
    })
    with open(OUT, "w", encoding="utf8") as f:
        f.write(json.dumps(data, indent=1) + "\n")
    print("TOUR_JSON_OK", OUT, len(rooms))
    sys.exit(0)

# ---------------------------------------------------------------- render set up
os.makedirs(OUT, exist_ok=True)
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            break
    except Exception:
        continue
s.render.engine = "CYCLES"
c = s.cycles
c.device = "GPU"
c.use_denoising = True
try:
    c.denoiser = "OPTIX"
except Exception:
    pass
if os.environ.get("TOUR_CPU"):                           # look tests on the processor while the GPU lock is taken
    c.device = "CPU"
    try:
        c.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
s.render.use_stamp = False
s.render.resolution_percentage = 100
# Image maps: 2K for what sits close to the camera (floors, worktops, rugs, upholstery, bedding, tile),
# 1K for everything else, so the scene stays in video memory on a card shared with other renders.
import re as _re
CLOSE = _re.compile(r"oak_wood_planks|oak wood natural|wool carpet|runner rug|regular white marble|sofa fabric|^materials$|"
                    r"mattress|sheet&|^frame$|bouclette|tissu|^fabric|sofa\.|pillow|white oak|walnut|laiton|marbre", _re.I)
img_mats = {}
for m in D.materials:
    if not m.node_tree:
        continue
    stack = [m.node_tree]
    while stack:
        nt_ = stack.pop()
        for n in nt_.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                img_mats.setdefault(n.image.name, set()).add(m.name)
            elif n.type == "GROUP" and n.node_tree:
                stack.append(n.node_tree)
s.render.use_simplify = False
scaled = 0
for img in D.images:
    if img.source not in ("FILE", "TILED") and not img.packed_file:
        continue
    try:
        w, h = img.size[:]
    except Exception:
        continue
    if not w:
        continue
    if img.filepath.lower().endswith((".exr", ".hdr")):
        cap = 2048                                           # the HDRI: a window view needs no more
    else:
        cap = 2048 if any(CLOSE.search(mn) for mn in img_mats.get(img.name, ())) else 1024
    if max(w, h) > cap:
        k = cap / max(w, h)
        img.scale(max(1, int(w * k)), max(1, int(h * k)))
        scaled += 1
print("TOUR images scaled", scaled, "close-up maps kept at 2K:", sum(1 for i in img_mats if any(CLOSE.search(m) for m in img_mats[i])))
if "TOUR_EXPOSURE" in os.environ:
    s.view_settings.exposure = float(os.environ["TOUR_EXPOSURE"])

cd = D.cameras.new("tour_cam")
cam = D.objects.new("tour_cam", cd)
s.collection.objects.link(cam)
s.camera = cam

if MODE == "plan":
    size = json.loads(s["size"])
    cd.type = "ORTHO"
    cd.ortho_scale = 27.0
    s.render.resolution_x, s.render.resolution_y = 520, 1080     # 40 px per metre; x = (px-260)/40, y = (540-py)/40
    c.samples = 24
    s.render.image_settings.file_format = "JPEG"
    for name, z in (("ground", 2.07 + 2.0), ("second", 5.34 + 2.0), ("third", 6.66 + 1.9)):
        cam.location = (0, 0, z)
        cam.rotation_euler = (0, 0, 0)
        cd.clip_start = 0.01; cd.clip_end = 3.2
        s.render.filepath = os.path.join(OUT, f"plan-{name}.jpg")
        bpy.ops.render.render(write_still=True)
    sys.exit(0)

cd.type = "PANO"
try:
    cd.panorama_type = "EQUIRECTANGULAR"
except Exception:
    cd.cycles.panorama_type = "EQUIRECTANGULAR"
cd.clip_start = 0.02; cd.clip_end = 2000
cam.rotation_euler = (math.radians(90), 0, 0)                     # image centre looks along +y, up is +z

if MODE == "final":
    RES = int(os.environ.get("TOUR_RES", "4096"))
    s.render.resolution_x, s.render.resolution_y = RES, RES // 2
    c.samples = int(os.environ.get("TOUR_SAMPLES", "300"))
    c.use_adaptive_sampling = True
    c.adaptive_threshold = float(os.environ.get("TOUR_NOISE", "0.02"))
    s.render.use_persistent_data = False
    c.use_auto_tile = True; c.tile_size = 1024                       # small film buffers on a shared card
    # Cycles applies the time limit to each tile, so a total budget is spread over the tiles
    tiles = math.ceil(RES / 1024) * math.ceil(RES / 2 / 1024)
    c.time_limit = float(os.environ.get("TOUR_TOTAL", "330")) / tiles
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "8"
    ext = "png"
else:
    s.render.resolution_x, s.render.resolution_y = 1024, 512
    c.samples = int(os.environ.get("TOUR_SAMPLES", "64"))
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.05
    s.render.image_settings.file_format = "JPEG"
    s.render.image_settings.quality = 90
    ext = "jpg"

if MODE == "at":
    jobs = [("at", Vector([float(v) for v in REST[:3]]))]
else:
    jobs = [(r["slug"], eye(r)) for r in ROOMS if not REST or r["slug"] in REST]

BASE_EV = s.view_settings.exposure
for slug, p in jobs:
    cam.location = p
    # rooms the sun does not reach are opened up a little, as a photographer would for each room
    s.view_settings.exposure = BASE_EV + BY.get(slug, {}).get("ev", 0.0)
    sun = D.objects.get("sun")
    if sun:                                                  # each room is shot at its own time of day
        az, el = [math.radians(v) for v in BY.get(slug, {}).get("sun", (24, 24))]
        d = Vector((math.sin(az), FRONT * math.cos(az), math.sin(el))).normalized()
        sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    s.render.filepath = os.path.join(OUT, f"{slug}.{ext}")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print("PANO_OK", slug, [round(v, 2) for v in p], round(time.time() - t, 1), "s", flush=True)
