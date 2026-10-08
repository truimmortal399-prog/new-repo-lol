"""Render one film scene through the real pipeline and record its cost.

  .venv/bin/python tools/render_scene.py S4 [--res -qh] [--fps 60] [--quality final]
Lossless RGB from manim.cfg (libx264rgb, qp 0). Writes out/renders/<scene>_<res><fps>.json with
wall time, frame count (ffprobe), file size and seconds per frame (wall / frames, setup included),
and copies the caption log the render wrote. The video stays under media/videos/.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframes import SCENE_FILES  # noqa: E402

RES = {"-ql": "480p", "-qm": "720p", "-qh": "1080p", "-qp": "1440p", "-qk": "2160p"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--res", default="-qh")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--quality", default="final")
    a = ap.parse_args()
    module, cls = SCENE_FILES[a.scene]
    env = dict(os.environ, RS_QUALITY=a.quality)
    t = time.perf_counter()
    p = subprocess.run([".venv/bin/manim", a.res, "--fps", str(a.fps), "--disable_caching", f"scenes/{module}.py", cls],
                       env=env, capture_output=True, text=True)
    wall = time.perf_counter() - t
    if p.returncode:
        sys.exit(p.stdout[-3000:] + p.stderr[-3000:])
    video = os.path.join("media", "videos", module, f"{RES[a.res]}{a.fps}", f"{cls}.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                            "stream=nb_read_frames,codec_name,pix_fmt,width,height", "-of", "json", video],
                           capture_output=True, text=True, check=True)
    st = json.loads(probe.stdout)["streams"][0]
    frames = int(st["nb_read_frames"])
    out = dict(scene=a.scene, video=video, quality=a.quality, res=RES[a.res], fps=a.fps, codec=st["codec_name"], pix_fmt=st["pix_fmt"],
               size=f"{st['width']}x{st['height']}", frames=frames, bytes=os.path.getsize(video), wall_s=round(wall, 1),
               s_per_frame=round(wall / frames, 3))
    os.makedirs(os.path.join("out", "renders"), exist_ok=True)
    tag = f"{a.scene}_{RES[a.res]}{a.fps}"
    json.dump(out, open(os.path.join("out", "renders", f"{tag}.json"), "w"), indent=1)
    log = os.path.join("out", "captions", f"{a.scene}.json")
    if os.path.exists(log):
        shutil.copy(log, os.path.join("out", "renders", f"{tag}_captions.json"))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
