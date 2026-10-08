"""Check a scene's caption log: observed timing vs script (±1 frame), legibility, overlap violations.

  .venv/bin/python tools/check_captions.py S3 [--fps 15]
Exit status 1 on any failure.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import script as sc  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--fps", type=float, default=15.0)
    args = ap.parse_args()
    frame = 1.0 / args.fps
    log = json.load(open(os.path.join("out", "captions", f"{args.scene}.json")))
    ok = True
    for c in log["captions"]:
        line = sc.BY_ID[c["id"]]
        problems = []
        if c["first_visible"] is None:
            problems.append("never visible")
        else:
            if abs(c["first_visible"] - line.reveal) > 1.5 * frame:
                problems.append(f"first visible {c['first_visible']:.3f} vs reveal {line.reveal:.3f}")
            if c["last_visible"] < line.hold_end - frame:
                problems.append(f"last visible {c['last_visible']:.3f} before hold end {line.hold_end:.3f}")
            if c["last_visible"] > line.exit_end + 1.5 * frame:
                problems.append(f"still visible {c['last_visible']:.3f} after exit end {line.exit_end:.3f}")
        xh = c.get("x_height")
        if xh is not None and xh < th.MIN_CAPTION_XHEIGHT:
            problems.append(f"x-height {xh:.4f} < {th.MIN_CAPTION_XHEIGHT}")
        status = "OK " if not problems else "FAIL"
        ok &= not problems
        xs = f"{xh:.4f}" if xh is not None else "n/a"
        print(f"{status} {c['id']:4s} visible {c['first_visible']}–{c['last_visible']}  planned {line.reveal:.2f}–{line.exit_end:.2f}  x-height {xs}  {'; '.join(problems)}")
    viol = log["violations"]
    if viol:
        ok = False
        by = {}
        for v in viol:
            by.setdefault((v["visual"], v["with_"]), []).append(v["t"])
        for (vis, other), ts in by.items():
            print(f"FAIL overlap: {vis} intersects {other} at {len(ts)} checks, t = {ts[0]:.2f}–{ts[-1]:.2f}")
    else:
        print("OK   no overlap violations")
    strays = log.get("strays", {})
    if strays:
        ok = False
        for key, (t0, t1, at) in strays.items():
            print(f"FAIL stray unregistered mobject {key} first at {at}, visible {t0:.2f}–{t1:.2f} (renders projected)")
    else:
        print("OK   no stray unregistered mobjects")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
