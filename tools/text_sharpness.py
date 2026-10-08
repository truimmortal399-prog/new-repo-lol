"""1080p text-sharpness check (Gate 4): native 1080p vs 4K -> Lanczos 1080p, both after the final
BT.709 4:2:0 encode. Crops the smallest and the coloured text, reports edge sharpness (10-90%
rise width of the strongest edges, in px; smaller = crisper) and mean gradient, and writes a
side-by-side 3x nearest-neighbour comparison sheet.

  .venv/bin/python tools/text_sharpness.py out/sharp/native_dec.png out/sharp/down_dec.png out/sharp/compare.png
"""

import json
import sys

import numpy as np
from PIL import Image, ImageDraw

# (name, x0, y0, x1, y1) in 1080p pixels, S6 at 58.0 s
CROPS = [
    ("caption (gold underlined words)", 520, 920, 1420, 1000),
    ("axis title  w (krad/s), 20 px font", 1590, 380, 1800, 440),
    ("tick labels +40 / -40", 1200, 100, 1300, 380),
    ("peak readout, gold 20 px", 1520, 55, 1800, 100),
    ("R / zeta readouts", 90, 755, 320, 870),
    ("height tag line 2, 20 px", 90, 315, 700, 360),
]


def luma(im):
    a = np.asarray(im.convert("RGB"), dtype=np.float64)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def edge_metrics(y):
    gx = np.abs(np.diff(y, axis=1))
    g = float(gx.mean())
    # rise width: for each row, the strongest step; count px between 10% and 90% of its swing
    widths = []
    for row in y:
        d = np.diff(row)
        i = int(np.argmax(np.abs(d)))
        lo, hi = max(i - 4, 0), min(i + 5, len(row) - 1)
        seg = row[lo : hi + 1]
        a, b = seg.min(), seg.max()
        if b - a < 60:
            continue
        t = (seg - a) / (b - a)
        widths.append(int(((t > 0.1) & (t < 0.9)).sum()))
    return g, (float(np.mean(widths)) if widths else None)


def main(a_path, b_path, out_path):
    A, B = Image.open(a_path).convert("RGB"), Image.open(b_path).convert("RGB")
    rep = {}
    rows = []
    for name, x0, y0, x1, y1 in CROPS:
        ca, cb = A.crop((x0, y0, x1, y1)), B.crop((x0, y0, x1, y1))
        ga, wa = edge_metrics(luma(ca))
        gb, wb = edge_metrics(luma(cb))
        rep[name] = dict(native=dict(mean_grad=round(ga, 2), rise_px=wa and round(wa, 2)), from_4k=dict(mean_grad=round(gb, 2), rise_px=wb and round(wb, 2)))
        rows.append((name, ca, cb))
    # comparison sheet: native | from 4K, 3x nearest
    k = 3
    W = max((c.width for _, c, _ in rows)) * k
    H = sum(c.height * k + 26 for _, c, _ in rows)
    sheet = Image.new("RGB", (2 * W + 20, H), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    y = 0
    for name, ca, cb in rows:
        d.text((4, y + 4), f"{name}   left: native 1080p   right: 4K -> Lanczos 1080p", fill=(230, 230, 230))
        sheet.paste(ca.resize((ca.width * k, ca.height * k), Image.NEAREST), (0, y + 26))
        sheet.paste(cb.resize((cb.width * k, cb.height * k), Image.NEAREST), (W + 20, y + 26))
        y += ca.height * k + 26
    sheet.save(out_path)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
