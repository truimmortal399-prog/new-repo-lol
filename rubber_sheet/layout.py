"""Screen-space composition checks for camera states and moves (used by tests and tuning).

Projects the world content that matters for framing — floor outline, the sheet's node grid at a
given lift, the tent-pole tops and their 'pole' labels — through a RigCamera at a CamState.
"""

import numpy as np

from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet import world
from rubber_sheet.camera import CamState, trapezoid
from rubber_sheet.surface import Z_CEIL

SAFE_X = th.FRAME_W / 2 * (1 - th.SAFE_MARGIN)  # 6.76 -> captions use 6.4; keep visuals inside ±6.4
SAFE_Y = th.FRAME_H / 2 * (1 - 2 * th.SAFE_MARGIN)  # 3.6
BAND_TOP = th.CAPTION_BAND["y1"]


def floor_outline():
    (s0, s1), (w0, w1) = th.SIGMA_RANGE, th.OMEGA_RANGE
    s = np.linspace(s0, s1, 21)
    w = np.linspace(w0, w1, 31)
    edge = [(x, w0) for x in s] + [(x, w1) for x in s] + [(s0, y) for y in w] + [(s1, y) for y in w]
    return np.array([world.xyz(a, b) for a, b in edge])


def sheet_points(R, lift):
    from rubber_sheet.common import SheetAssembly

    sheet = SheetAssembly(R=R, lift=lift, opacity=1.0)
    return sheet.surface.outline_points()


def pole_label_points(R, lift):
    pts = []
    for p in ph.poles(R) / 1e3:
        top = (Z_CEIL + 0.55) * lift
        for dx in (0.15, 0.85):  # label spans ~0.42 +/- 0.35 to the right of the pole line
            for dz in (-0.15, 0.2):
                pts.append(world.xyz(p.real, p.imag, top + dz) + np.array([dx, 0.0, 0.0]))
    return np.array(pts)


def interpolate_state(a: CamState, b: CamState, alpha):
    lerp = lambda u, v: (1 - alpha) * np.asarray(u, float) + alpha * np.asarray(v, float)  # noqa: E731
    return CamState(
        phi=float(lerp(a.phi, b.phi)),
        theta=float(lerp(a.theta, b.theta)),
        zoom=float(lerp(a.zoom, b.zoom)),
        pivot=tuple(lerp(a.pivot, b.pivot)),
        pan=tuple(lerp(a.pan, b.pan)),
    )


def states_along(move, n=12):
    rate = trapezoid(move.run_time)
    return [(move.t0 + k / n * move.run_time, interpolate_state(move.start, move.end, rate(k / n))) for k in range(n + 1)]


def screen_extent(state, points):
    from rubber_sheet.rig import RigCamera, apply_state

    cam = RigCamera()
    apply_state(cam, state)
    xy = cam.screen_points(points)[:, :2]
    return xy.min(axis=0), xy.max(axis=0)
