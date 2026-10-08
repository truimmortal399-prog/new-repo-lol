"""Assemble the whole film from the per-scene lossless renders and verify it (Gate 5).

  .venv/bin/python tools/assemble_film.py [--res 1080p60] [--crf 18]
1. every scene video has exactly script.scene_frames(scene, 60) frames (none dropped or extra)
2. stream-copy concat (all scenes share manim.cfg's lossless encoder spec) -> out/film/concat_rgb.mkv
3. the concat has exactly round(FILM_END * 60) frames whose timestamps step by exactly 1/60 s
   (no dropped or duplicated frame anywhere, cuts included)
4. ONE final encode: RGB -> BT.709 limited 4:2:0, CRF 18, -tune animation, -preset slow, tagged
   -> out/film/the_rubber_sheet_<res>.mp4, then ffprobe: duration, frame count, fps, tags, no audio
5. a 24-frame contact sheet at evenly spaced film times -> out/film/contact24.png
Writes out/film/assembly.json.
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyframes import SCENE_FILES  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import script as sc  # noqa: E402

OUT = os.path.join("out", "film")
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
COLOR = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]


def probe_frames(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.split()
    return np.array([float(x) for x in out if x.strip()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="1080p60")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()
    fps = int(a.res.split("p")[1])
    os.makedirs(OUT, exist_ok=True)
    rep = dict(scenes={}, problems=[])
    files = []
    for scene in sc.SCENES:
        module, cls = SCENE_FILES[scene]
        path = os.path.join("media", "videos", module, a.res, f"{cls}.mp4")
        _, expected = sc.scene_frames(scene, fps)
        n = len(probe_frames(path))
        rep["scenes"][scene] = dict(video=path, frames=n, expected=expected)
        if n != expected:
            rep["problems"].append(f"{scene}: {n} frames, grid says {expected}")
        files.append(os.path.abspath(path))
    lst = os.path.join(OUT, "scenes.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in files)
    concat = os.path.join(OUT, "concat_rgb.mkv")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", concat], check=True)
    pts = probe_frames(concat)
    total = round(sc.FILM_END * fps)
    steps = np.diff(pts)
    rep["concat"] = dict(frames=len(pts), expected=total, min_step=float(steps.min()), max_step=float(steps.max()))
    if len(pts) != total:
        rep["problems"].append(f"concat has {len(pts)} frames, film needs {total}")
    if np.abs(steps - 1.0 / fps).max() > 0.5e-3:
        rep["problems"].append(f"timestamp steps {steps.min():.5f}..{steps.max():.5f} s, expected {1 / fps:.5f}")
    out = os.path.join(OUT, f"the_rubber_sheet_{a.res}.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", concat, "-an", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-tune", "animation", *COLOR, "-movflags", "+faststart", out], check=True)
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                                      "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,pix_fmt,color_space,color_primaries,color_transfer,color_range",
                                      "-of", "json", out], capture_output=True, text=True, check=True).stdout)
    v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    rep["final"] = dict(path=out, bytes=int(info["format"]["size"]), duration=float(info["format"]["duration"]), frames=int(v["nb_read_frames"]),
                        fps=v["r_frame_rate"], size=f"{v['width']}x{v['height']}", pix_fmt=v["pix_fmt"],
                        color=[v.get("color_space"), v.get("color_primaries"), v.get("color_transfer"), v.get("color_range")],
                        audio_streams=sum(s["codec_type"] == "audio" for s in info["streams"]))
    f = rep["final"]
    if f["frames"] != total or abs(f["duration"] - sc.FILM_END) > 0.5 / fps or f["audio_streams"] or f["fps"] != f"{fps}/1":
        rep["problems"].append(f"final file: {f}")
    # 24 evenly spaced frames
    times = [(k + 0.5) * sc.FILM_END / 24 for k in range(24)]
    font = ImageFont.truetype(FONT, 16) if os.path.exists(FONT) else None
    w, h = 480, 270
    sheet = Image.new("RGB", (6 * w, 4 * (h + 24)), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(times):
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", out, "-frames:v", "1", "-vf", f"scale={w}:{h}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        im = Image.frombytes("RGB", (w, h), raw)
        x, y = (i % 6) * w, (i // 6) * (h + 24)
        sheet.paste(im, (x, y + 24))
        scene = next(s for s, (t0, t1) in sc.SCENES.items() if t0 <= t < t1)
        d.text((x + 6, y + 3), f"{t:5.2f} s  {scene}", fill=(230, 230, 230), font=font)
    sheet.save(os.path.join(OUT, "contact24.png"))
    json.dump(rep, open(os.path.join(OUT, "assembly.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "scenes"}, indent=1))
    sys.exit(1 if rep["problems"] else 0)


if __name__ == "__main__":
    main()
