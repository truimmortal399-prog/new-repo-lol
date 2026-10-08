"""Framing: projected world content stays out of the caption band, inside title-safe, and (in
the analysis layouts) left of the panel column — sampled along every planned camera move."""

import numpy as np
import pytest

from rubber_sheet import beats as bt
from rubber_sheet import captions
from rubber_sheet import common
from rubber_sheet import camera as cam
from rubber_sheet import layout as L
from rubber_sheet import physics as ph
from rubber_sheet import theme as th

MARGIN = 0.05


def s3_lift(t):
    return float(th.SWEEP(min(max((t - bt.S3_LIFT_START) / bt.S3_LIFT_RUN, 0.0), 1.0)))


def extent(state, lift, labels, R=ph.R_START):
    pts = [L.floor_outline()]
    if lift > 0:
        pts.append(L.sheet_points(R, lift))
    if labels:
        pts.append(L.pole_label_points(R, lift))
    return L.screen_extent(state, np.vstack(pts))


def hud_boxes(with_tag):
    f = common.formula_HC()
    boxes = [("formula", captions._bbox_fixed(f))]
    if with_tag:
        boxes.append(("height tag", captions._bbox_fixed(common.height_tag(f))))
    return boxes


def check_hud(state, lift, R, with_tag, what, labels=False):
    """No projected sheet point (or pole label) may fall inside a HUD block."""
    from rubber_sheet.rig import RigCamera, apply_state

    pts = [L.sheet_points(R, lift)] if lift > 0 else []
    if labels:
        pts.append(L.pole_label_points(R, lift))
    if not pts:
        return
    c = RigCamera()
    apply_state(c, state)
    xy = c.screen_points(np.vstack(pts))[:, :2]
    for name, (x0, y0, x1, y1) in hud_boxes(with_tag):
        inside = (xy[:, 0] > x0) & (xy[:, 0] < x1) & (xy[:, 1] > y0) & (xy[:, 1] < y1)
        assert not inside.any(), f"{what}: sheet runs into the {name}"


def check(lo, hi, what, panel_column=False):
    assert lo[1] >= L.BAND_TOP + MARGIN, f"{what}: enters caption band (y={lo[1]:.2f})"
    assert hi[1] <= L.SAFE_Y, f"{what}: above title-safe (y={hi[1]:.2f})"
    assert lo[0] >= -6.4 and hi[0] <= 6.4, f"{what}: outside safe x ({lo[0]:.2f}, {hi[0]:.2f})"
    if panel_column:
        assert hi[0] <= th.PANEL_REGION["x0"] - MARGIN, f"{what}: runs into the panel column (x={hi[0]:.2f})"


@pytest.mark.parametrize("move", cam.moves_in("S3"), ids=lambda m: m.name)
def test_s3_moves_framed(move):
    for t, state in L.states_along(move, 12):
        lift, labels = s3_lift(t), t >= bt.S3_POLE_LABELS
        lo, hi = extent(state, lift, labels)
        check(lo, hi, f"{move.name} t={t:.2f}")
        check_hud(state, lift, ph.R_START, t >= bt.S3_LIFT_START, f"{move.name} t={t:.2f}", labels)


def test_top_view_framed():
    lo, hi = extent(cam.TOP, 0.0, False)
    check(lo, hi, "TOP")


@pytest.mark.parametrize("R", [ph.R_START, ph.R_SWEEP_END, 0.0])
@pytest.mark.parametrize("name,panels", [("CUT", True), ("ANALYSIS", True), ("HERO", False)])
def test_static_states_framed(name, panels, R):
    lo, hi = extent(getattr(cam, name), 1.0, name == "HERO", R)
    check(lo, hi, f"{name} R={R}", panel_column=panels)
    check_hud(getattr(cam, name), 1.0, R, True, f"{name} R={R}", name == "HERO")
