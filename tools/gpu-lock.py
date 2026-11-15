"""One GPU render at a time on this PC (owner's rule: renders run one by one).

  python tools/gpu-lock.py acquire <job name>   waits until the GPU is free, then takes it
  python tools/gpu-lock.py release <job name>   frees it (only the holder can)
  python tools/gpu-lock.py status               who holds it, and since when

Take the lock around one batch of GPU work (one film shot, one tour's set of rooms, one set of stills),
then release it so the next job can run. Scene prep, downloads and encoding do not need the lock.
A lock older than 8 hours whose holder wrote no heartbeat is treated as stale.
"""
import os, sys, time, json

LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets-src", ".gpu-lock")
STALE = 8 * 3600


def read():
    try:
        return json.load(open(os.path.join(LOCK, "owner.json"), encoding="utf8"))
    except Exception:
        return None


def acquire(name):
    waited = 0
    while True:
        try:
            os.mkdir(LOCK)  # atomic: only one process can create it
            json.dump({"job": name, "since": time.strftime("%Y-%m-%d %H:%M:%S"), "t": time.time()},
                      open(os.path.join(LOCK, "owner.json"), "w", encoding="utf8"))
            print("GPU acquired by", name, flush=True)
            return
        except FileExistsError:
            o = read()
            if o and time.time() - o.get("t", time.time()) > STALE:
                print("stale lock from", o.get("job"), "removed", flush=True)
                release(o.get("job"), force=True)
                continue
            if waited % 300 == 0:
                print("GPU busy with", o and o.get("job"), "- waiting", flush=True)
            time.sleep(15)
            waited += 15


def release(name, force=False):
    o = read()
    if o and o.get("job") != name and not force:
        print("not released: held by", o.get("job"))
        return
    try:
        os.remove(os.path.join(LOCK, "owner.json"))
    except FileNotFoundError:
        pass
    try:
        os.rmdir(LOCK)
    except FileNotFoundError:
        pass
    print("GPU released by", name, flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "acquire":
        acquire(sys.argv[2])
    elif cmd == "release":
        release(sys.argv[2])
    else:
        print(read() or "free")
