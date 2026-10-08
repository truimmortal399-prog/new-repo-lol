"""Full caption audit (Gate 5): every caption of the film against the reading rule, the scene
cuts, the band sequencing rule and the observed render logs.

  .venv/bin/python tools/caption_audit.py [--fps 60]
Per caption: n recomputed from the text, required hold (0.5 + n/3.33, ceil 0.01), planned
reveal/hold/exit, the scene span (never crossed), the gap to the previous caption in the band
(>= previous exit end, or >= previous hold end for flagged continuations), and from the scene's render
log (out/captions/<scene>.json, written by the last real render): first/last visible frame against
the film grid, on-screen time >= reveal + hold, x-height, plus every overlap violation (caption band
or HUD) and stray of that render. Writes out/film/caption_audit.json and prints a table.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import captions  # noqa: E402
from rubber_sheet import script as sc  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=float, default=60.0)
    a = ap.parse_args()
    logs = {}
    for scene in sc.SCENES:
        p = os.path.join("out", "captions", f"{scene}.json")
        logs[scene] = json.load(open(p)) if os.path.exists(p) else None
    rows, ok = [], True
    band = [line for line in sc.LINES if line.region == "band"]
    prev_of = {nxt.id: prev for prev, nxt in zip(band, band[1:])}
    cuts = [span[1] for span in sc.SCENES.values()][:-1]
    for line in sc.LINES:
        problems = []
        n = sc.word_count(line.text)
        need = sc.required_hold(n)
        if n != line.n:
            problems.append(f"n {line.n} but text has {n}")
        if line.hold + 1e-9 < need:
            problems.append(f"hold {line.hold} < {need}")
        s0, s1 = sc.SCENES[line.scene]
        if line.reveal < s0 - 1e-9 or line.exit_end > s1 + 1e-9:
            problems.append(f"outside its scene {s0}-{s1}")
        if any(line.reveal + 1e-9 < c < line.exit_end - 1e-9 for c in cuts):
            problems.append("crosses a cut")
        if line.id in prev_of:
            prev = prev_of[line.id]
            bound = prev.hold_end if line.continuation else prev.exit_end
            if line.reveal + 1e-9 < bound:
                problems.append(f"reveal {line.reveal} before {prev.id}'s {'hold' if line.continuation else 'exit'} end {bound:.2f}")
        log = logs[line.scene]
        entry = None if log is None else next((c for c in log["captions"] if c["id"] == line.id), None)
        if entry is None:
            problems.append("no render log")
            seen = (None, None)
        else:
            seen = (entry["first_visible"], entry["last_visible"])
            problems += captions.timing_problems(line, line.scene, a.fps, *seen)
            if entry.get("x_height") is not None and entry["x_height"] < th.MIN_CAPTION_XHEIGHT:
                problems.append(f"x-height {entry['x_height']:.4f}")
        ok &= not problems
        rows.append(dict(id=line.id, scene=line.scene, n=n, hold=line.hold, required=need, reveal=line.reveal, hold_end=round(line.hold_end, 2),
                         exit_end=round(line.exit_end, 2), visible=seen, problems=problems))
        print(f"{'OK ' if not problems else 'FAIL'} {line.id:4s} {line.scene} n={n} hold {line.hold:.2f}>={need:.2f}  R {line.reveal:6.2f}  "
              f"H-end {line.hold_end:6.2f}  X-end {line.exit_end:6.2f}  seen {seen[0]}-{seen[1]}  {'; '.join(problems)}")
    scene_issues = {}
    for scene, log in logs.items():
        if log is None:
            scene_issues[scene] = ["no render log"]
            continue
        issues = [f"{v['visual']} x {v['with_']} at {v['t']}" for v in log["violations"]] + [f"stray {k}" for k in log.get("strays", {})]
        if issues:
            scene_issues[scene] = issues
            ok = False
    print("overlap / stray violations:", scene_issues or "none")
    os.makedirs(os.path.join("out", "film"), exist_ok=True)
    json.dump(dict(captions=rows, scene_issues=scene_issues, ok=ok), open(os.path.join("out", "film", "caption_audit.json"), "w"), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
