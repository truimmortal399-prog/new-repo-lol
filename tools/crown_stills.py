"""Close crops of the final-mesh sheet around both pole crowns, rendered at 1080p through the real
RigCamera (same draw order, shading and colours as the film), for several R and camera states.

  RS_QUALITY=final .venv/bin/python tools/crown_stills.py
Writes out/keys/crowns/<state>_R<R>.png (full frame) and a crop contact sheet crowns.png.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from manim import tempconfig  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import layout as L  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet import world  # noqa: E402
from rubber_sheet.common import SheetAssembly  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state  # noqa: E402

OUT = os.path.join("out", "keys", "crowns")
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def render(state_name, R, w=1920, h=1080):
    with tempconfig({"pixel_width": w, "pixel_height": h, "background_color": th.BG}):
        sheet = SheetAssembly(R=R, lift=1.0, opacity=1.0)
        floor = world.SPlaneFloor()
        floor.remove(floor.ticks, floor.unit)
        c = RigCamera()
        apply_state(c, getattr(cam, state_name))
        c.reset_rotation_matrix()
        c.capture_mobjects([floor.grid, floor.axes, world.DashedCircle(), sheet.crosses, sheet.surface, sheet.tents])
        img = Image.fromarray(c.pixel_array[..., :3].copy())
        tops = c.screen_points(L.pole_tops(R, 1.0))[:, :2]
        px = [((x + th.FRAME_W / 2) / th.FRAME_W * w, (th.FRAME_H / 2 - y) / th.FRAME_H * h) for x, y in tops]
        return img, px


def main():
    os.makedirs(OUT, exist_ok=True)
    crops, labels = [], []
    for state in ("S3_END", "ANALYSIS", "CUT"):
        for R in (120.0, 40.0, 4.0, 0.5):
            img, px = render(state, R)
            img.save(os.path.join(OUT, f"{state}_R{R:g}.png"))
            for k, (x, y) in enumerate(px):
                box = (int(x - 150), int(y - 40), int(x + 150), int(y + 260))  # apex at top, crown below
                crops.append(img.crop(box))
                labels.append(f"{state} R={R:g} {'upper' if k else 'lower'} pole")
    cols, cw, ch = 6, 300, 300
    sheet = Image.new("RGB", (cols * cw, ((len(crops) + cols - 1) // cols) * (ch + 22)), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT, 14) if os.path.exists(FONT) else None
    for i, (im, lab) in enumerate(zip(crops, labels)):
        x, y = (i % cols) * cw, (i // cols) * (ch + 22)
        sheet.paste(im, (x, y + 22))
        draw.text((x + 4, y + 3), lab, fill=(230, 230, 230), font=font)
    sheet.save(os.path.join(OUT, "crowns.png"))
    print(os.path.join(OUT, "crowns.png"), len(crops), "crops")


if __name__ == "__main__":
    main()
