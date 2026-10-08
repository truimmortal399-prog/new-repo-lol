"""Extract review keyframes from a rendered scene and build a labeled contact sheet.

Times: scene start/end, every caption's mid-hold, the beat times in EXTRA, plus any extra
times given on the command line. The output folder is cleared first, so a contact sheet never
mixes renders.
  .venv/bin/python tools/keyframes.py S3                 # newest render of S3 (any quality)
  .venv/bin/python tools/keyframes.py S3 path/to/video.mp4 [extra film times ...]
Writes out/keys/<scene>/<film-time>.png and out/keys/<scene>/contact.png.
"""

import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from rubber_sheet import script as sc  # noqa: E402

EXTRA = {
    "S3": [12.4, 13.4, 13.9, 14.5, 15.6, 17.0, 18.0, 18.6, 19.4, 20.6, 21.0, 22.8, 24.9],
    "S4": [25.2, 25.6, 26.3, 26.8, 27.5, 28.2, 29.2, 30.25, 30.35, 30.8, 31.2, 31.6, 31.9, 33.6, 34.2, 34.8, 35.6],
    "S5": [36.0, 36.5, 37.0, 37.4, 37.8, 38.1, 38.6, 39.4, 40.2, 41.0, 42.5, 43.9, 44.8, 45.9, 46.3, 46.7, 47.1, 47.6, 48.2],
    "S6": [48.6, 49.0, 49.5, 51.0, 52.5, 54.0, 55.5, 57.0, 58.5, 59.5, 60.3, 60.9],
}
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def keyframe_times(scene_id):
    t0, t1 = sc.SCENES[scene_id]
    times = {round(t0 + 0.04, 2), round(t1 - 0.08, 2)}
    for line in sc.lines_for(scene_id):
        times.add(round(line.reveal_end + line.hold / 2, 2))
    times.update(EXTRA.get(scene_id, []))
    return sorted(times)


def extract(video, t_local, path):
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t_local:.3f}", "-i", video, "-frames:v", "1", path],
        check=True,
    )


def contact_sheet(paths, labels, out, cols=4, width=480):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = int(ims[0].height * width / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width, rows * (h + 22)), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT, 15) if os.path.exists(FONT) else None
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * width, (i // cols) * (h + 22)
        sheet.paste(im.resize((width, h)), (x, y + 22))
        draw.text((x + 6, y + 3), lab, fill=(230, 230, 230), font=font)
    sheet.save(out)


SCENE_FILES = {
    "S3": ("s03_poles_sheet", "S3PolesSheet"),
    "S4": ("s04_slice_bode", "S4SliceBode"),
    "S5": ("s05_zero_nail", "S5ZeroNail"),
    "S6": ("s06_sweep", "S6Sweep"),
}


def newest_video(scene_id):
    module, cls = SCENE_FILES[scene_id]
    found = glob.glob(os.path.join("media", "videos", module, "*", f"{cls}.mp4"))
    if not found:
        raise SystemExit(f"no render of {scene_id} under media/videos/{module}/")
    return max(found, key=os.path.getmtime)


def main(scene_id, video, extra=()):
    outdir = os.path.join("out", "keys", scene_id)
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir)
    fps = float(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video],
        capture_output=True, text=True, check=True).stdout.strip().split("/")[0])
    t0 = sc.scene_start_on_grid(scene_id, fps)  # the video's first frame shows this film time
    times = sorted(set(keyframe_times(scene_id)) | set(extra))
    paths, labels = [], []
    for t in times:
        p = os.path.join(outdir, f"{t:06.2f}.png")
        extract(video, t - t0, p)
        paths.append(p)
        cap = [l.id for l in sc.lines_for(scene_id) if l.reveal <= t <= l.exit_end]
        labels.append(f"t = {t:.2f} s  {' '.join(cap)}")
    contact_sheet(paths, labels, os.path.join(outdir, "contact.png"))
    print(os.path.join(outdir, "contact.png"), len(paths), "frames from", video)


if __name__ == "__main__":
    scene = sys.argv[1]
    video = sys.argv[2] if len(sys.argv) > 2 else newest_video(scene)
    main(scene, video, [float(x) for x in sys.argv[3:]])
