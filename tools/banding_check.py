"""Banding check of the final encode (Gate 5 prep): the darkest smooth regions of the rendered
scenes after the 1080p BT.709 4:2:0 encode, against the lossless RGB source.

For each sampled frame it finds smooth dark regions in the SOURCE (sheet shading on the far side,
the scrim over 3D content): luma < 80, not background, gentle but non-zero gradient. Banding is the
encoder turning such slopes into flat plateaus separated by steps (false contours), so it measures
  plateau_gain  = fraction of zero-gradient pixels in the encode minus in the source (same pixels)
  step_gain     = fraction of >= 2-level steps in the encode minus in the source
  mae           = mean |encode - source| luma there
and writes 4x crops of the darkest such window: source | encode | both contrast-stretched x6.
Variants (the escalation order): base = CRF 18 -tune animation -preset slow (our final encode);
dither = base + ~1 LSB temporal noise before the encode; crf16 = base at CRF 16.

  .venv/bin/python tools/banding_check.py S3 S4 S5 S6 [--variants base,dither,crf16]
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframes import SCENE_FILES  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import script as sc  # noqa: E402

OUT = os.path.join("out", "banding")
COLOR = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
VARIANTS = {
    "base": dict(pre="", crf=18),
    "dither": dict(pre="noise=c0s=1:c1s=1:c2s=1:allf=t,", crf=18),
    "crf16": dict(pre="", crf=16),
}


def video(scene):
    module, cls = SCENE_FILES[scene]
    return os.path.join("media", "videos", module, "1080p60", f"{cls}.mp4")


def encode(src, dst, variant):
    v = VARIANTS[variant]
    vf = f"{v['pre']}scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-an", "-vf", vf, "-c:v", "libx264", "-preset", "slow",
                    "-crf", str(v["crf"]), "-tune", "animation", *COLOR, "-movflags", "+faststart", dst], check=True)


def frame(path, t):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1080, 1920, 3).astype(np.float64)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def smooth_dark_mask(src):
    y = luma(src)
    bg = np.abs(src - np.array([13, 17, 23])).max(axis=2) <= 2
    gx = np.abs(np.diff(y, axis=1, append=y[:, -1:]))
    gy = np.abs(np.diff(y, axis=0, append=y[-1:, :]))
    g = np.maximum(gx, gy)
    # gentle slopes: the regions where an encoder plateaus first (exclude edges and text)
    return (~bg) & (y < 80) & (g <= 2.0), y


def metrics(src, enc, mask):
    ys, ye = luma(src), luma(enc)

    def stats(y):
        dx = np.abs(np.diff(np.round(y), axis=1, append=np.round(y[:, -1:])))
        return (dx == 0)[mask].mean(), (dx >= 2)[mask].mean()

    ps, ss = stats(ys)
    pe, se = stats(ye)
    return dict(pixels=int(mask.sum()), plateau_gain=round(float(pe - ps), 4), step_gain=round(float(se - ss), 4),
                mae=round(float(np.abs(ye - ys)[mask].mean()), 3))


def darkest_window(mask, y, size=(80, 120)):
    h, w = size
    best, at = None, (0, 0)
    for r in range(0, 1080 - h, 20):
        for c in range(0, 1920 - w, 20):
            m = mask[r : r + h, c : c + w]
            if m.mean() < 0.6:
                continue
            v = y[r : r + h, c : c + w][m].mean()
            if best is None or v < best:
                best, at = v, (r, c)
    return at, size


def stretch(a, lo, hi):
    return np.clip((a - lo) / max(hi - lo, 1e-6) * 255, 0, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="+")
    ap.add_argument("--variants", default="base")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lst = os.path.join(OUT, "scenes.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(video(s))}'\n" for s in a.scenes)
    concat = os.path.join(OUT, "concat_rgb.mkv")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", concat], check=True)
    t0 = sc.scene_start_on_grid(a.scenes[0], 60)
    times = []
    for s in a.scenes:  # 3 frames per scene: early, middle, late
        s0, s1 = sc.SCENES[s]
        times += [round(s0 + f * (s1 - s0), 2) for f in (0.25, 0.55, 0.9)]
    report = {}
    for variant in a.variants.split(","):
        enc = os.path.join(OUT, f"{variant}.mp4")
        encode(concat, enc, variant)
        rows = []
        for t in times:
            src, out = frame(concat, t - t0), frame(enc, t - t0)
            mask, y = smooth_dark_mask(src)
            m = metrics(src, out, mask)
            (r, c), (h, w) = darkest_window(mask, y)
            m.update(t=t, window=[c, r, w, h])
            rows.append(m)
            cs, ce = src[r : r + h, c : c + w], out[r : r + h, c : c + w]
            lo, hi = np.percentile(luma(cs), 2), np.percentile(luma(cs), 98)
            lo, hi = lo - 4, hi + 4
            strip = np.concatenate([cs, ce, stretch(cs, lo, hi), stretch(ce, lo, hi)], axis=1).astype(np.uint8)
            Image.fromarray(strip).resize((strip.shape[1] * 4, h * 4), Image.NEAREST).save(os.path.join(OUT, f"{variant}_{t:05.2f}.png"))
        size = os.path.getsize(enc)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", enc],
                                   capture_output=True, text=True, check=True).stdout)
        report[variant] = dict(bytes=size, mbit_s=round(size * 8 / dur / 1e6, 3), duration=dur, frames=rows,
                               mean_plateau_gain=round(float(np.mean([r["plateau_gain"] for r in rows])), 4),
                               mean_step_gain=round(float(np.mean([r["step_gain"] for r in rows])), 4))
        print(variant, {k: v for k, v in report[variant].items() if k != "frames"}, flush=True)
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
