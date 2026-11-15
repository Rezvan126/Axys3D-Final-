# Contact sheets for the amber renders (plain Python with Pillow, not Blender).
#   python tools/amber-sheet.py tests <folder>          -> <folder>/sheet.jpg from every jpg in it
#   python tools/amber-sheet.py contact                 -> assets-src/amber/renders/contact.jpg (6 finals beside adu-1 and adu-13)
import sys, os, glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sheet(paths, out, cols, w, h, gap=6):
    rows = (len(paths) + cols - 1) // cols
    sh = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), (18, 18, 18))
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        # centre crop to the cell shape, then scale
        tw = im.height * w / h
        if tw < im.width:
            x = int((im.width - tw) / 2); im = im.crop((x, 0, x + int(tw), im.height))
        else:
            th = int(im.width * h / w); y = int((im.height - th) / 2); im = im.crop((0, y, im.width, y + th))
        im = im.resize((w, h), Image.LANCZOS)
        sh.paste(im, (gap + (i % cols) * (w + gap), gap + (i // cols) * (h + gap)))
    sh.save(out, quality=90)
    print("sheet", out, sh.size)

if sys.argv[1] == "tests":
    folder = sys.argv[2]
    order = ["hero", "low34", "entry", "upper", "wide", "planting"]
    files = [os.path.join(folder, n + ".jpg") for n in order if os.path.exists(os.path.join(folder, n + ".jpg"))]
    files += [f for f in sorted(glob.glob(os.path.join(folder, "*.jpg"))) if f not in files and not f.endswith("sheet.jpg")]
    sheet(files, os.path.join(folder, "sheet.jpg"), 2, 720, 405)
else:
    m = os.path.join(ROOT, "public", "media")
    files = [os.path.join(m, f"amber-{i}.webp") for i in range(1, 7)] + [os.path.join(m, "adu-1.webp"), os.path.join(m, "adu-13.webp")]
    sheet(files, os.path.join(ROOT, "assets-src", "amber", "renders", "contact.jpg"), 2, 960, 540)
