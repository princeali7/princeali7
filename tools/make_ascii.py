"""One-off: turn a photo into assets/ascii-art.txt (dark) and ascii-art-light.txt.

Run locally (needs Pillow), not in CI:
    python tools/make_ascii.py photo.jpg --crop 170,40,400,400 --cols 60
"""
import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAMP = " .:-=+*#%@"  # light -> dense
CELL_ASPECT = 0.54  # monospace cell width / height, so the face isn't stretched


def subject_mask(rgb: Image.Image) -> Image.Image:
    """White where the person is; drops foliage (green-dominant) and blown-out sky."""
    m = Image.new("L", rgb.size)
    m.putdata([
        0 if (g > b + 10 and g >= r - 5 and r + g + b > 150) or min(r, g, b) > 215 else 255
        for r, g, b in rgb.getdata()
    ])
    return m.filter(ImageFilter.MedianFilter(9))


def render(img: Image.Image, mask: Image.Image, cols: int, invert: bool) -> str:
    rows = round(cols * img.height / img.width * CELL_ASPECT)
    g = img.resize((cols, rows), Image.LANCZOS)
    if invert:
        g = ImageOps.invert(g)
    g = ImageChops.multiply(g, mask.resize((cols, rows), Image.LANCZOS))  # background -> blank
    n = len(RAMP) - 1
    return "\n".join(
        "".join(RAMP[g.getpixel((x, y)) * n // 255] for x in range(cols)).rstrip()
        for y in range(rows)
    ) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("photo")
    p.add_argument("--crop", help="left,top,right,bottom in pixels")
    p.add_argument("--cols", type=int, default=60)
    a = p.parse_args()
    rgb = Image.open(a.photo).convert("RGB")
    if a.crop:
        rgb = rgb.crop(tuple(int(v) for v in a.crop.split(",")))
    mask = subject_mask(rgb)
    img = ImageOps.autocontrast(ImageEnhance.Contrast(rgb.convert("L")).enhance(1.6))
    # Dark card: bright pixels get dense glyphs. Light card: the reverse.
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets/ascii-art.txt").write_text(render(img, mask, a.cols, invert=False))
    (ROOT / "assets/ascii-art-light.txt").write_text(render(img, mask, a.cols, invert=True))


if __name__ == "__main__":
    main()
