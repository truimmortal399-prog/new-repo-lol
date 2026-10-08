"""Search framing keyframes (Move.via) that make a camera move pass every composition rule.

Angles are fixed by the move; only zoom/pan at 1-2 keyframes are searched. Candidates must pass
layout.frame_violations at every sample (R = 120/4/0, zero variants during S5). Among feasible
paths it prefers the smallest peak pan speed (smooth, no whip), then the highest zoom.

  .venv/bin/python tools/frame_search.py "S4 swing"      # prints the best Frame keyframes
"""

import dataclasses
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

from rubber_sheet import beats as bt  # noqa: E402
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import layout as L  # noqa: E402

RS = (120.0, 4.0, 0.0)


def zeros_at(t):
    return [None, -15.0, -5.0, 0.0] if bt.ZERO_BEAT[0] <= t <= bt.ZERO_BEAT[1] else [None]


def feasible(move, n=24):
    for t, st in L.states_along(move, n):
        for R in RS:
            for z in zeros_at(t):
                if L.frame_violations(st, t, R, z):
                    return False
    return True


def peak_pan_speed(move, n=200):
    """Peak screen-pan speed (frame units/s) and zoom rate along the move."""
    ts = np.linspace(move.t0, move.t1, n + 1)
    p = np.array([[s.pan[0], s.pan[1], s.zoom] for s in (cam.state_at_time(move, t) for t in ts)])
    v = np.diff(p, axis=0) / np.diff(ts)[:, None]
    return float(np.max(np.hypot(v[:, 0], v[:, 1]))), float(np.max(np.abs(v[:, 2])))


def search(move, pairs=((0.35, 0.7), (0.4, 0.75), (0.3, 0.6)), zooms=(0.74, 0.72, 0.70),
           dxs1=(0.6, 1.0, 1.4, 1.8), dys1=(-0.4, -0.2, 0.0), dxs2=(0.4, 0.8, 1.2, 1.6), dys2=(-0.4, -0.2, 0.0)):
    """Two keyframes as offsets from the straight path; returns (peak pan speed, zoom rate, frames)."""
    straight = dataclasses.replace(move, via=())
    best = None
    for s1, s2 in pairs:
        b1, b2 = cam.state_at(straight, s1), cam.state_at(straight, s2)
        for z1, z2 in itertools.product(zooms, zooms):
            for dx1, dy1, dx2, dy2 in itertools.product(dxs1, dys1, dxs2, dys2):
                f1 = cam.Frame(s=s1, zoom=z1, pivot=b1.pivot, pan=(round(b1.pan[0] + dx1, 3), round(b1.pan[1] + dy1, 3)))
                f2 = cam.Frame(s=s2, zoom=z2, pivot=b2.pivot, pan=(round(b2.pan[0] + dx2, 3), round(b2.pan[1] + dy2, 3)))
                cand = dataclasses.replace(move, via=(f1, f2))
                speed, zrate = peak_pan_speed(cand)
                if best and speed >= best[0]:
                    continue
                if feasible(cand):
                    best = (speed, zrate, (f1, f2))
                    print(f"candidate peak pan {speed:.3f}/s zoom rate {zrate:.3f}/s: {f1} {f2}", flush=True)
    return best


if __name__ == "__main__":
    mv = next(m for m in cam.MOVES if m.name.startswith(sys.argv[1]))
    print("current path feasible:", feasible(mv), "peak pan/zoom speed:", peak_pan_speed(mv))
    print("BEST", search(mv))
