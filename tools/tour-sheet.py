# Contact sheet of panorama tests, for looking at several at once.
#   python tools/tour-sheet.py <folder> <out.jpg> <cols> name [name ...]
import subprocess, sys, os
folder, out, cols = sys.argv[1], sys.argv[2], int(sys.argv[3])
names = sys.argv[4:]
files = [os.path.join(folder, n if "." in n else n + ".jpg") for n in names]
rows = (len(files) + cols - 1) // cols
cmd = ["ffmpeg", "-v", "error", "-y"]
for f in files:
    cmd += ["-i", f]
lay = "|".join(f"{(i % cols) * 1024}_{(i // cols) * 512}" for i in range(len(files)))
scaled = "".join(f"[{i}:v]scale=1024:512[s{i}];" for i in range(len(files)))
ins = "".join(f"[s{i}]" for i in range(len(files)))
cmd += ["-filter_complex", f"{scaled}{ins}xstack=inputs={len(files)}:layout={lay}:fill=black[v]", "-map", "[v]", "-q:v", "3", out]
subprocess.run(cmd, check=True)
print("SHEET", out, cols, "x", rows)
