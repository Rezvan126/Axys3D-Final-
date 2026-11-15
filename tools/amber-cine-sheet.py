# Contact sheet for the amber film: three graded frames per shot (1 s, 5 s, 9 s) beside adu-1 and adu-13.
#   python tools/amber-cine-sheet.py      -> assets-src/amber/renders/cine-contact.jpg
import os, subprocess, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "assets-src", "amber", "renders")
W, H, GAP = 760, 318, 6          # 2.39:1 cells
tmp = tempfile.mkdtemp()
rows = []
for shot in "abcd":
    src = os.path.join(M, f"cine-graded-{shot}.mp4")
    row = []
    for t in (1, 5, 9):
        out = os.path.join(tmp, f"{shot}{t}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", src, "-frames:v", "1", out], check=True)
        row.append(Image.open(out).convert("RGB").resize((W, H), Image.LANCZOS))
    rows.append(row)
# reference row: the current site stills, cropped to the same 2.39:1 cell
ref = []
for name in ("adu-1.webp", "adu-13.webp"):
    im = Image.open(os.path.join(ROOT, "public", "media", name)).convert("RGB")
    th = int(im.width * H / W); y = (im.height - th) // 2
    ref.append(im.crop((0, y, im.width, y + th)).resize((W, H), Image.LANCZOS))
sheet = Image.new("RGB", (3 * W + 4 * GAP, 5 * H + 6 * GAP + 4 * 22), (16, 16, 16))
d = ImageDraw.Draw(sheet)
labels = ["A  crane up through the verge", "B  dolly along the pavement planting", "C  rack focus: grass, door, garage", "D  pull back as the light falls", "Current site: adu-1, adu-13"]
y = GAP
for i, row in enumerate(rows + [ref]):
    d.text((GAP, y), labels[i], fill=(220, 220, 220))
    y += 22
    for j, im in enumerate(row):
        sheet.paste(im, (GAP + j * (W + GAP), y))
    y += H + GAP
out = os.path.join(M, "cine-contact.jpg")
sheet.save(out, quality=90)
print("sheet", out, sheet.size)
