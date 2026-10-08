"""Gate 4 timing on real film content: a span of a scene (default S6 52-54 s, mid-sweep, the
heaviest load: full sheet, both panels, readouts, captions, camera move) drawn at 1080p60 and
2160p60, final mesh, lossless encoder. Per-frame cost = (wall(span) - wall(1-frame span)) / extra
frames, so setup and the undrawn frames before the span cancel out. Then the 4K span 3x in
parallel (the planned render layout). Writes out/timing_scenes.json.

  .venv/bin/python tools/time_scenes.py [S6] [52] [54]
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframes import SCENE_FILES  # noqa: E402

FLAGS = {"1080p60": "-qh", "2160p60": "-qk"}


def cmd(scene, res, media):
    module, cls = SCENE_FILES[scene]
    return [".venv/bin/manim", res, "--fps", "60", "--disable_caching", "--media_dir", media, f"scenes/{module}.py", cls]


def run(scene, res, span, tag):
    env = dict(os.environ, RS_QUALITY="final", RS_SPAN=span, RS_NO_LOG="1")
    t = time.perf_counter()
    subprocess.run(cmd(scene, res, os.path.join("out", "time_media", tag)), env=env, check=True, capture_output=True)
    return time.perf_counter() - t


def main(scene="S6", a="52", b="54"):
    a, b = float(a), float(b)
    n = round((b - a) * 60)
    out = dict(scene=scene, span=[a, b], frames=n)
    for q, res in FLAGS.items():
        full = run(scene, res, f"{a}:{b}", f"{q}_span")
        one = run(scene, res, f"{a}:{a}", f"{q}_one")
        out[q] = dict(wall_span=round(full, 1), wall_one_frame=round(one, 1), s_per_frame=round((full - one) / n, 3))
        print(q, out[q], flush=True)
    env = dict(os.environ, RS_QUALITY="final", RS_SPAN=f"{a}:{b}", RS_NO_LOG="1")
    t = time.perf_counter()
    procs = [subprocess.Popen(cmd(scene, "-qk", os.path.join("out", "time_media", f"par{k}")), env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for k in range(3)]
    codes = [p.wait() for p in procs]
    wall = time.perf_counter() - t
    one = out["2160p60"]["wall_one_frame"]
    out["2160p60_x3"] = dict(wall=round(wall, 1), codes=codes, s_per_frame_each=round((wall - one) / n, 3))
    print("2160p60 x3", out["2160p60_x3"], flush=True)
    json.dump(out, open(os.path.join("out", "timing_scenes.json"), "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
