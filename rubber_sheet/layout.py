"""Screen-space composition checks for camera states and moves (used by tests and tuning).

Projects the world content that matters for framing — floor outline, the sheet's node grid at a
given lift, the tent-pole tops and their 'pole' labels — through a RigCamera at a CamState.
"""

import numpy as np

from rubber_sheet import beats as bt
from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet import world
from rubber_sheet.camera import state_at_time
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


def floor_samples(step=1.0):
    """Dense floor grid (every `step` krad/s) for overlap checks against HUD blocks."""
    (s0, s1), (w0, w1) = th.SIGMA_RANGE, th.OMEGA_RANGE
    S, W = np.meshgrid(np.arange(s0, s1 + 1e-9, step), np.arange(w0, w1 + 1e-9, step), indexing="ij")
    x, y = th.s_to_xy(S.ravel(), W.ravel())
    return np.column_stack([x, y, np.zeros_like(x)])


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


def states_along(move, n=12):
    """[(film time, CamState)] sampled along a move exactly as the renderer will drive it."""
    return [(move.t0 + k / n * move.run_time, state_at_time(move, move.t0 + k / n * move.run_time)) for k in range(n + 1)]


def screen_extent(state, points):
    from rubber_sheet.rig import RigCamera, apply_state

    cam = RigCamera()
    apply_state(cam, state)
    xy = cam.screen_points(points)[:, :2]
    return xy.min(axis=0), xy.max(axis=0)


# --- the full composition rule set (tests/test_composition.py and framing search) ---------------
BAND_MARGIN = 0.05
_cache = {}


def _sheet_unit(R, zero):
    """Sheet node grid at lift 1 (heights scale linearly with lift), cached."""
    key = (R, zero)
    if key not in _cache:
        from rubber_sheet.common import SheetAssembly

        if zero is None:
            sheet = SheetAssembly(R=R, lift=1.0, opacity=1.0)
        else:
            sheet = SheetAssembly(R=R, lift=1.0, opacity=1.0, mag=lambda S, R=R, z=zero: ph.mag_zero(S, R, z * 1e3))
        _cache[key] = sheet.surface.outline_points().copy()
    return _cache[key]


_floor = []


def _floor_dense():
    if not _floor:
        _floor.append(floor_samples())
    return _floor[0]


def lift_at(t):
    if t < bt.S3_LIFT_START:
        return 0.0
    return float(th.SWEEP(min((t - bt.S3_LIFT_START) / bt.S3_LIFT_RUN, 1.0)))


_hud = {}


def _hud_box(name):
    if not _hud:
        from rubber_sheet import captions, common

        f = common.formula_HC()
        _hud["formula"] = captions._bbox_fixed(f)
        _hud["roots"] = captions._bbox_fixed(common.roots_block(f))
        _hud["height tag"] = captions._bbox_fixed(common.height_tag(f))
    return _hud[name]


def hud_boxes_at(t):
    within = lambda span: span[0] <= t <= span[1]  # noqa: E731
    spans = [("formula", bt.FORMULA_SPAN), ("roots", bt.ROOTS_SPAN), ("height tag", bt.TAG_SPAN)]
    return [(name, _hud_box(name)) for name, span in spans if within(span)]


_cam = []


def _project(state, pts):
    from rubber_sheet.rig import RigCamera, apply_state

    if not _cam:
        _cam.append(RigCamera())
    c = _cam[0]
    apply_state(c, state)
    return c.screen_points(pts)[:, :2]


def pole_tops(R, lift):
    return np.array([world.xyz(p.real, p.imag, (Z_CEIL + 0.3) * lift) for p in ph.poles(R) / 1e3])


def label_boxes(state, R, lift):
    """Screen boxes of the S3 'pole' ScreenLabels (lower pole up-left, upper up-right)."""
    tops = _project(state, pole_tops(R, lift))
    w, h, dx, dy = 0.62, 0.30, 0.22, 0.12
    lower, upper = tops[0], tops[1]
    return [(lower[0] - dx - w, lower[1] + dy, lower[0] - dx, lower[1] + dy + h), (upper[0] + dx, upper[1] + dy, upper[0] + dx + w, upper[1] + dy + h)]


def frame_violations(state, t, R, zero=None):
    """Every framing rule at film time t for camera state `state`. Returns a list of strings."""
    out = []
    lift = lift_at(t)
    sheet = _sheet_unit(R, zero) * np.array([1.0, 1.0, lift]) if lift > 0 else np.zeros((0, 3))
    floor = floor_outline()
    pts = np.vstack([floor, sheet]) if len(sheet) else floor
    xy = _project(state, pts)
    labels = label_boxes(state, R, lift) if bt.POLE_LABEL_SPAN[0] <= t <= bt.POLE_LABEL_SPAN[1] else []
    ys = [xy[:, 1].min()] + [b[1] for b in labels]
    tops = [xy[:, 1].max()] + [b[3] for b in labels]
    xs_lo = [xy[:, 0].min()] + [b[0] for b in labels]
    xs_hi = [xy[:, 0].max()] + [b[2] for b in labels]
    if min(ys) < BAND_TOP + BAND_MARGIN:
        out.append(f"enters caption band (y={min(ys):.2f})")
    if max(tops) > SAFE_Y:
        out.append(f"above title-safe (y={max(tops):.2f})")
    if min(xs_lo) < -th.SAFE_X or max(xs_hi) > th.SAFE_X:
        out.append(f"outside safe x ({min(xs_lo):.2f}, {max(xs_hi):.2f})")
    if t >= bt.PANEL_COLUMN_FROM and xy[:, 0].max() > th.PANEL_REGION["x0"] - BAND_MARGIN:
        out.append(f"runs into the panel column (x={xy[:, 0].max():.2f})")
    sheet_xy = xy[len(floor):]
    floor_xy = _project(state, _floor_dense())
    for name, (x0, y0, x1, y1) in hud_boxes_at(t):
        for what, P in (("sheet", sheet_xy), ("floor", floor_xy)):
            if len(P) and np.any((P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1)):
                out.append(f"{what} runs into the {name}")
        for lb in labels:
            if lb[0] < x1 and x0 < lb[2] and lb[1] < y1 and y0 < lb[3]:
                out.append(f"pole label runs into the {name}")
    if t >= bt.APEX_SEPARATION_FROM:
        tops_xy = _project(state, pole_tops(R, max(lift, 1e-6)))
        sep = abs(tops_xy[0, 0] - tops_xy[1, 0])
        if sep < bt.APEX_MIN_SEPARATION:
            out.append(f"tent-pole apexes only {sep:.2f} apart on screen")
    return out
