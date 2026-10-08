"""Render one film-time frame of a scene (final mesh by default) for close inspection.

  .venv/bin/python tools/still.py S4 25.6 [--quality final] [--res -qh]   -> out/stills/S4_25.60.png
Uses RS_STILL_AT (rubber_sheet/timeline.py): the scene's single play runs up to that film time and
draws only its last frame. The monitor still runs, but the caption log is not written to out/.
"""

import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframes import SCENE_FILES  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("times", nargs="+", type=float)
    ap.add_argument("--quality", default="final")
    ap.add_argument("--res", default="-qh")
    a = ap.parse_args()
    module, cls = SCENE_FILES[a.scene]
    os.makedirs(os.path.join("out", "stills"), exist_ok=True)
    for t in a.times:
        media = os.path.join("out", "stills", "media")
        env = dict(os.environ, RS_QUALITY=a.quality, RS_STILL_AT=str(t), RS_NO_LOG="1")
        subprocess.run([".venv/bin/manim", a.res, "--disable_caching", "--media_dir", media, f"scenes/{module}.py", cls],
                       env=env, check=True, capture_output=True)
        video = max(glob.glob(os.path.join(media, "videos", module, "*", f"{cls}.mp4")), key=os.path.getmtime)
        out = os.path.join("out", "stills", f"{a.scene}_{t:05.2f}.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.1", "-i", video, "-update", "1", "-frames:v", "1", out], check=True)
        print(out)


if __name__ == "__main__":
    main()
