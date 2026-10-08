"""Fabric-texture shimmer check (Gate 4): 3 s moving sheet, 4K60 final mesh, Lanczos -> 1080p.

Renders scenes/probe_fabric.py twice at 4K (seam strokes on = the film's look, and off), takes
each through the deliverable's path (lossless RGB -> Lanczos 1080p -> BT.709 CRF 18), then
measures temporal shimmer on the decoded 1080p frames inside the sheet: the energy of the
temporal second difference f[t-1] - 2 f[t] + f[t+1], high-pass filtered in space. Smooth motion
leaves it small; strokes that alias (crawl, flicker, moire) raise it. Writes crops of
consecutive frames for eyeballing and out/fabric/report.json.

  .venv/bin/python tools/fabric_check.py
"""

import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

OUT = os.path.join("out", "fabric")
VARIANTS = {"strokes": None, "no_strokes": "0"}


def render(tag, stroke):
    env = dict(os.environ, RS_QUALITY="final")
    if stroke is not None:
        env["PROBE_STROKE"] = stroke
    media = os.path.join(OUT, "media", tag)
    subprocess.run([".venv/bin/manim", "-qk", "--fps", "60", "--disable_caching", "--media_dir", media,
                    "scenes/probe_fabric.py", "ProbeFabric"], env=env, check=True, capture_output=True)
    return os.path.join(media, "videos", "probe_fabric", "2160p60", "ProbeFabric.mp4")


def deliver_1080(src, dst):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-an",
                    "-vf", "scale=1920:1080:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "animation",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv", dst], check=True)


def frames(video, first=58, n=64):
    """Luma of frames first..first+n (the middle of the clip: camera and R both moving)."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         check=True, capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920)
    return a[first:first + n].astype(np.float32)


def highpass(f):
    """Remove the low spatial frequencies (shading, the moving silhouette) with a 9x9 box blur."""
    k = 9
    c = np.cumsum(np.cumsum(np.pad(f, ((0, 0), (k // 2 + 1, k // 2), (k // 2 + 1, k // 2)), mode="edge"), axis=1), axis=2)
    box = (c[:, k:, k:] - c[:, :-k, k:] - c[:, k:, :-k] + c[:, :-k, :-k]) / (k * k)
    return f - box


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    stacks = {}
    for tag, stroke in VARIANTS.items():
        src = render(tag, stroke)
        dst = os.path.join(OUT, f"{tag}_1080p.mp4")
        deliver_1080(src, dst)
        stacks[tag] = frames(dst)
        print(tag, "rendered", dst, flush=True)
    # sheet mask: pixels that differ from the background in every frame of both variants
    mask = (stacks["strokes"] > 40).all(axis=0) & (stacks["no_strokes"] > 40).all(axis=0)
    for tag, f in stacks.items():
        hp = highpass(f)
        d2 = hp[:-2] - 2 * hp[1:-1] + hp[2:]
        per_frame = np.sqrt((d2[:, mask] ** 2).mean(axis=1))
        report[tag] = dict(rms_temporal_d2=round(float(per_frame.mean()), 3), p95=round(float(np.percentile(per_frame, 95)), 3),
                           spatial_hf_rms=round(float(np.sqrt((hp[:, mask] ** 2).mean())), 3))
        # 4 consecutive crops at the swing's mid-point (sheet centre), 2x nearest-neighbour zoom
        for k in range(4):
            fr = f[32 + k]
            crop = fr[380:620, 700:1100]
            Image.fromarray(crop.astype(np.uint8)).resize((800, 480), Image.NEAREST).save(os.path.join(OUT, f"{tag}_crop_{k}.png"))
    report["mask_pixels"] = int(mask.sum())
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    sys.exit(main())
