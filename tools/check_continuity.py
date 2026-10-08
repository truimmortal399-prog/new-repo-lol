"""Continuity across scene cuts: the last frame of scene A vs the first frame of scene B.

Pass when the mean absolute pixel difference is < 1.5 % (docs/PLAN.md) and no 32x32 block jumps
by more than the larger of 8 % and 3x the in-scene frame-to-frame change just before the cut (a
pop: something appearing/vanishing at the cut). Writes out/continuity/<A>_<B>.png
(A last | B first | 4x amplified difference) for eyeballing.

  .venv/bin/python tools/check_continuity.py S4 S5 [S6 ...]      (newest 1080p60 renders)
"""

import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframes import SCENE_FILES  # noqa: E402

RES = "1080p60"


def video(scene):
    module, cls = SCENE_FILES[scene]
    return os.path.join("media", "videos", module, RES, f"{cls}.mp4")


def frames(path, which):
    """Two RGB frames: the last two ('end') or the first two ('start')."""
    args = ["-sseof", "-0.2"] if which == "end" else []
    limit = [] if which == "end" else ["-frames:v", "2"]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", *args, "-i", path, *limit, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920, 3)
    pair = (a[-2], a[-1]) if which == "end" else (a[0], a[1])
    return tuple(f.astype(np.float32) for f in pair)


def blocks(d, k=32):
    h, w = (d.shape[0] // k) * k, (d.shape[1] // k) * k
    return d[:h, :w].reshape(h // k, k, w // k, k, 3).mean(axis=(1, 3, 4))


def main(scenes):
    os.makedirs(os.path.join("out", "continuity"), exist_ok=True)
    ok = True
    for a, b in zip(scenes, scenes[1:]):
        prev, last = frames(video(a), "end")
        first, _ = frames(video(b), "start")
        cut = np.abs(first - last)
        inside = np.abs(last - prev)
        mean_pct = float(cut.mean() / 255 * 100)
        jump = blocks(cut) / 255 * 100
        base = blocks(inside) / 255 * 100
        limit = np.maximum(8.0, 3.0 * base)
        pops = int((jump > limit).sum())
        good = mean_pct < 1.5 and pops == 0
        ok &= good
        print(f"{'OK ' if good else 'FAIL'} {a}|{b}: mean diff {mean_pct:.3f} % (in-scene {inside.mean() / 255 * 100:.3f} %), "
              f"max block jump {jump.max():.2f} %, pops {pops}")
        amp = np.clip(cut * 4, 0, 255)
        sheet = np.concatenate([last, first, amp], axis=1).astype(np.uint8)
        Image.fromarray(sheet).resize((1920, 360)).save(os.path.join("out", "continuity", f"{a}_{b}.png"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
