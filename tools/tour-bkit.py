# BlenderKit helper for the virtual tour, run headless with the owner's logged in add-on.
#
#   blender -b -P tools/tour-bkit.py -- probe
#   blender -b -P tools/tour-bkit.py -- search <model|material|hdr> "<words>" [n]
#   blender -b -P tools/tour-bkit.py -- get <asset_base_id> [...]
#
# Only free assets are searched for and fetched (is_free:true). Nothing is bought, no account is made,
# no credential is typed: the add-on's own stored login and its local client do the download, exactly as
# a click in the asset bar would. The key is never printed.
# Downloads land in the add-on's normal cache (~/blenderkit_data/<type>s/...). Every fetched asset is
# appended to assets-src/amber/tour/bkit-assets.json (name, id, type, licence, author) for HANDOFF.md.
import bpy, sys, os, json, time
import addon_utils

argv = sys.argv[sys.argv.index("--") + 1:]
MODE = argv[0]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "assets-src", "amber", "tour", "bkit-assets.json")

mod = None
for name in ("bl_ext.user_default.blenderkit", "blenderkit"):
    try:
        addon_utils.enable(name, default_set=False, persistent=False, handle_error=None)
        mod = sys.modules.get(name)
        if mod:
            break
    except Exception as e:
        print("BKIT enable failed", name, e)
if not mod:
    print("BKIT_FAIL add-on not found"); sys.exit(1)
pkg = mod.__name__
client_lib = sys.modules[pkg + ".client_lib"]
paths = sys.modules[pkg + ".paths"]
download = sys.modules[pkg + ".download"]
import requests

prefs = bpy.context.preferences.addons[pkg].preferences
API_KEY = getattr(prefs, "api_key", "") or ""
API = "https://www.blenderkit.com/api/v1/search/"
import uuid
SCENE_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "axys3d-virtual-tour"))   # a fixed id for this scene, as the add-on sends per .blend

def client_ok():
    try:
        client_lib.reorder_ports()
    except Exception:
        pass
    for _ in range(20):
        try:
            r = requests.get(client_lib.get_base_url(), timeout=2, proxies={"http": "", "https": ""})
            return True, r.status_code
        except Exception as e:
            err = e
        try:
            client_lib.start_blenderkit_client()
        except Exception:
            pass
        time.sleep(1.5)
    return False, str(err)[:120]

def search(kind, words, n=12):
    q = f"{words} asset_type:{kind} is_free:true order:-score"
    r = requests.get(API, params={"query": q, "page_size": n, "dict_parameters": 1}, timeout=30,
                     headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})
    r.raise_for_status()
    return r.json().get("results", [])

def slug(name):
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:16]

def line(a):
    return f'{a.get("assetBaseId")} | {a.get("name")} | {a.get("license")} | free={a.get("isFree")} | {a.get("dictParameters", {}).get("dimensionX", "")}x{a.get("dictParameters", {}).get("dimensionY", "")}x{a.get("dictParameters", {}).get("dimensionZ", "")} | by {a.get("author", {}).get("fullName", "")}'

if MODE == "probe":
    ok, code = client_ok()
    print("BKIT client", ok, code, "logged_in", bool(API_KEY))
    for a in search("model", "sofa", 5):
        print("BKIT", line(a))
    sys.exit(0)

if MODE == "search":
    kind, words = argv[1], argv[2]
    n = int(argv[3]) if len(argv) > 3 else 12
    for a in search(kind, words, n):
        print("BKIT", kind, line(a))
    sys.exit(0)

if MODE == "batch":                                     # batch "<kind>:<words>" ... , six results each
    for q in argv[1:]:
        kind, words = q.split(":", 1)
        print("\nBKIT_Q", q)
        try:
            for a in search(kind, words, 6):
                print("BKIT", line(a))
        except Exception as e:
            print("BKIT_ERR", repr(e)[:120])
    sys.exit(0)

if MODE == "get":
    ok, code = client_ok()
    print("BKIT client", ok, code, "logged_in", bool(API_KEY))
    log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    for base_id in argv[1:]:
        r = requests.get(API, params={"query": f"asset_base_id:{base_id}", "dict_parameters": 1}, timeout=30,
                         headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})
        res = r.json().get("results", [])
        if not res:
            print("BKIT_MISS", base_id); continue
        a = res[0]
        if not a.get("isFree"):
            print("BKIT_SKIP not free", base_id, a.get("name")); continue
        try:
            a = paths.ensure_asset_data_dict(a) if hasattr(paths, "ensure_asset_data_dict") else a
        except Exception:
            pass
        try:
            # pick the file: the .blend for models and materials, a 4K (else 2K) map for HDRIs
            files = a.get("files", [])
            want = ["resolution_4K", "resolution_2K", "blend"] if a.get("assetType") == "hdr" else ["resolution_2K", "blend"]   # 2K maps keep the shared card within memory
            f = next((x for w in want for x in files if x.get("fileType") == w), None)
            if not f:
                print("BKIT_FAIL no file", a["name"], [x.get("fileType") for x in files]); continue
            folder = os.path.join(os.path.expanduser("~"), "blenderkit_data", a["assetType"] + "s",
                                  f'{slug(a["name"])}_{a["id"]}')
            existing = [n for n in os.listdir(folder)] if os.path.isdir(folder) else []
            existing = [n for n in existing if n.endswith((".blend", ".exr", ".hdr")) and os.path.getsize(os.path.join(folder, n)) > 1000]
            if existing:
                target = os.path.join(folder, existing[0])
                print("BKIT_CACHED", a["name"], target)
            else:
                # the same signed request the add-on makes: the API answers with a short lived file address
                r = requests.get(f["downloadUrl"], params={"scene_uuid": SCENE_UUID}, timeout=30,
                                 headers={"Authorization": f"Bearer {API_KEY}"})
                if r.status_code != 200:
                    print("BKIT_DENIED", a["name"], r.status_code); continue
                src = r.json().get("filePath")
                ext = os.path.splitext(src.split("?")[0])[1] or ".blend"
                os.makedirs(folder, exist_ok=True)
                target = os.path.join(folder, f'{slug(a["name"])}_{f["fileType"]}{ext}')
                with requests.get(src, stream=True, timeout=600) as d:
                    d.raise_for_status()
                    with open(target, "wb") as out:
                        for chunk in d.iter_content(1 << 20):
                            out.write(chunk)
                ok = os.path.getsize(target) > 1000
                print("BKIT_GOT" if ok else "BKIT_FAIL", a["name"], target, round(os.path.getsize(target) / 1e6, 1), "MB")
                if not ok:
                    continue
            log[base_id] = {"name": a.get("name"), "type": a.get("assetType"), "license": a.get("license"),
                            "author": a.get("author", {}).get("fullName", ""), "file": target}
        except Exception as e:
            print("BKIT_FAIL", a.get("name"), repr(e)[:200])
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    json.dump(log, open(LOG, "w"), indent=1)
    print("BKIT_LOG", LOG, len(log))
