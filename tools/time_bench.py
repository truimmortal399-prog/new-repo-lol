"""Gate 3 timing of scenes/bench_live.py (final mesh, lossless encoder from manim.cfg).

Per resolution it renders BENCH_SECONDS = 2.0 and 0.5; the slope gives the true per-frame cost
(render + encode), the intercept the setup cost. Then it runs N copies of the 2 s render at once
to measure the per-frame cost under the contention a parallel full render will see.

  .venv/bin/python tools/time_bench.py            -> out/timing.json
"""

import json
import os
import subprocess
import sys
import time

FLAGS = {"1080p60": ["-qh"], "2160p60": ["-qk"]}
PARALLEL = 3


def run(quality, seconds, tag):
    env = dict(os.environ, RS_QUALITY="final", BENCH_SECONDS=str(seconds))
    media = os.path.join("out", "bench_media", tag)
    t = time.perf_counter()
    p = subprocess.run(
        [".venv/bin/manim", *FLAGS[quality], "--fps", "60", "--disable_caching", "--media_dir", media, "scenes/bench_live.py", "BenchLive"],
        env=env, capture_output=True, text=True,
    )
    wall = time.perf_counter() - t
    if p.returncode:
        sys.exit(p.stdout[-2000:] + p.stderr[-2000:])
    return wall


def main():
    out = {}
    for q in ("1080p60", "2160p60"):
        long_, short = run(q, 2.0, f"{q}_2s"), run(q, 0.5, f"{q}_05s")
        per_frame = (long_ - short) / ((2.0 - 0.5) * 60)
        out[q] = dict(wall_2s=round(long_, 1), wall_05s=round(short, 1), s_per_frame=round(per_frame, 3), setup_s=round(short - 0.5 * 60 * per_frame, 1))
        print(q, out[q], flush=True)
    # contention: PARALLEL simultaneous 2 s 4K renders
    env = dict(os.environ, RS_QUALITY="final", BENCH_SECONDS="2.0")
    t = time.perf_counter()
    procs = [
        subprocess.Popen([".venv/bin/manim", "-qk", "--fps", "60", "--disable_caching", "--media_dir", os.path.join("out", "bench_media", f"par{k}"), "scenes/bench_live.py", "BenchLive"],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for k in range(PARALLEL)
    ]
    codes = [p.wait() for p in procs]
    wall = time.perf_counter() - t
    setup = out["2160p60"]["setup_s"]
    out["2160p60_parallel"] = dict(n=PARALLEL, wall=round(wall, 1), exit_codes=codes, s_per_frame_each=round((wall - setup) / 120, 3))
    print("2160p60 x", PARALLEL, out["2160p60_parallel"], flush=True)
    os.makedirs("out", exist_ok=True)
    json.dump(out, open(os.path.join("out", "timing.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
