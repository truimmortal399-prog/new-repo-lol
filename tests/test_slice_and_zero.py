"""S4 (slice -> Bode) and S5 (hand-moved zero) mechanics: exact data, exact handoff, clean swaps."""

import numpy as np
import pytest
from manim import ValueTracker

from rubber_sheet import beats as bt
from rubber_sheet import camera as cam
from rubber_sheet import common, world
from rubber_sheet import layout as L
from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet.panels import BodePanel
from rubber_sheet.rig import RigCamera, apply_state
from rubber_sheet.surface import CUT_BIAS, CutCurve


def zero_sheet(z_rad):
    return common.SheetAssembly(lift=1.0, opacity=1.0, zero=lambda: z_rad)


@pytest.mark.parametrize("z", [-np.inf, -15e3, -5e3, 0.0])
def test_cut_is_exact_physics(z):
    sheet = zero_sheet(z)
    cut = CutCurve(sheet.surface)
    pts = cut.world_points(cut.omega)
    ref = ph.zmap(ph.to_db(ph.mag_zero(1j * cut.omega * 1e3, ph.R_START, z)))
    np.testing.assert_allclose(pts[:, 2], ref, atol=1e-12)
    np.testing.assert_allclose(pts[:, 0], 0.0)
    if z == 0.0:  # the zero at the origin pins the cut to the -40 dB floor at w = 0
        assert pts[np.argmin(np.abs(cut.omega)), 2] == pytest.approx(0.0, abs=1e-9)


def test_cut_reveal_and_depth_bias():
    cut = CutCurve(common.SheetAssembly(lift=1.0, opacity=1.0).surface)
    cut.reveal.set_value(0.5)
    cut.refresh()
    drawn = np.concatenate([p.points for p in cut.submobjects if p.has_points()])
    assert drawn[:, 1].max() == pytest.approx(0.0, abs=1e-9)  # half of [-15, 15] krad/s
    assert all(p.depth_bias == CUT_BIAS and p.shade_in_3d for p in cut.submobjects)


def test_handoff_curves_are_exact():
    """The flyer starts exactly on the projected cut (CUT view) and lands exactly on the panel's
    linear-axis curve: inverting the panel transform gives the physics dB at the same w."""
    sheet = common.SheetAssembly(lift=1.0, opacity=1.0)
    cut = CutCurve(sheet.surface)
    w_krad = np.linspace(0.0, 15.0, 301)
    c = RigCamera()
    apply_state(c, cam.CUT)
    start = c.screen_points(cut.world_points(w_krad))[:, :2]
    rig = RigCamera()  # what the renderer draws for the world cut: capture resets the rotation first
    apply_state(rig, cam.CUT)
    rig.reset_rotation_matrix()
    world_px = rig.project_points(cut.world_points(w_krad))[:, :2]
    np.testing.assert_allclose(start, world_px, atol=1e-12)
    bode = BodePanel(lambda w: ph.mag_C(1j * w, ph.R_START), th.BODE_BOX, warp=ValueTracker(0.0))
    end = bode.screen_curve(w_krad * 1e3, mu=0.0)
    u, db = bode.from_screen(end).T
    np.testing.assert_allclose(u, w_krad / 15.0, atol=1e-12)
    np.testing.assert_allclose(db, ph.to_db(ph.mag_C(1j * w_krad * 1e3, ph.R_START)), atol=1e-9)


def test_sigma_plane_splits_at_the_cut():
    sheet = common.SheetAssembly(lift=1.0, opacity=1.0)
    cut = CutCurve(sheet.surface)
    plane = world.SigmaPlane(lambda w: cut.world_points(w)[:, 2])
    plane.opacity.set_value(1.0)
    plane.refresh()
    z = cut.world_points(plane.w)[:, 2]
    for k, (up, lo) in enumerate(zip(plane.upper, plane.lower)):
        assert lo.points[:, 2].max() == pytest.approx(max(z[k], z[k + 1]))
        assert up.points[:, 2].min() == pytest.approx(min(z[k], z[k + 1]))
        assert lo.depth_bias == world.UNDER_SHEET and up.depth_bias == world.ABOVE_PLANE_BIAS
        assert np.allclose(up.points[:, 0], 0.0) and np.allclose(lo.points[:, 0], 0.0)


def test_hidden_right_half_leaves_the_outline():
    surf = common.SheetAssembly(lift=1.0, opacity=1.0).surface
    full = len(surf.outline_points())
    surf.right_opacity.set_value(0.0)
    surf.refresh()
    left = surf.outline_points()
    assert len(left) < full and left[:, 0].max() == pytest.approx(0.0)


def test_zero_schedule_endpoints_are_exact():
    assert np.isneginf(ph.zero_slide(0.0)) and ph.zero_slide(1.0) == ph.ZERO_EDGE and ph.zero_slide(2.0) == 0.0
    s = 1j * np.logspace(2, 6, 300) - 2000.0
    np.testing.assert_array_equal(ph.mag_zero(s, ph.R_START, ph.zero_slide(0.0)), ph.mag_C(s, ph.R_START))
    np.testing.assert_allclose(ph.mag_zero(s, ph.R_START, ph.zero_slide(2.0)), ph.mag_R(s, ph.R_START), rtol=1e-14)
    (first, *_), last = bt.S5_ZERO_PHASES, bt.S5_ZERO_PHASES[-1]
    assert L.zero_at(first[0][0] - 0.01) is None and L.zero_at(last[0][1] + 0.01) is None
    assert L.zero_at(41.0) == pytest.approx(0.0, abs=1e-12) and L.zero_at(43.6) == pytest.approx(0.0, abs=1e-12)
    zs = [L.zero_at(t) for t in np.linspace(38.0, 41.0, 61)]
    assert all(b >= a - 1e-12 for a, b in zip(zs, zs[1:]))  # slides monotonically into the origin


def test_zero_is_a_mesh_knot():
    for z in (-15e3, -7.3e3, -0.4e3):
        sheet = zero_sheet(z)
        sigma, omega = sheet.surface.grid()
        assert np.min(np.abs(sigma - z / 1e3)) < 1e-12  # a node line runs exactly through the zero
        assert np.min(np.abs(omega)) == 0.0
        assert sheet.surface.heights[np.argmin(np.abs(sigma - z / 1e3)), np.argmin(np.abs(omega))] == pytest.approx(0.0, abs=1e-12)


def test_formula_swap_changes_only_the_numerator():
    c, r = common.formula_HC(), common.formula_HR()
    np.testing.assert_allclose([m.get_center() for m in c[2][1:]], [m.get_center() for m in r[2][3:]], atol=1e-9)
    np.testing.assert_allclose(c[0].get_center(), r[0].get_center(), atol=0.02)
    assert len(c[2][common.NUMERATOR_HC]) == 1 and len(r[2][common.NUMERATOR_HR]) == 3


def test_probe_swap_changes_only_the_subscript():
    a, b = common.probe_label("C"), common.probe_label("R")
    assert len(a) == len(b)
    np.testing.assert_allclose([m.get_center() for m in a[:-1]], [m.get_center() for m in b[:-1]], atol=0.01)


def test_s5_labels_at_the_edge_never_share_the_screen():
    """'from -inf', 'zero' and 'to -inf' sit at almost the same spot: their fades never overlap."""
    assert bt.S5_EDGE_LABEL_OUT[1] <= bt.S5_ZERO_LABEL_IN[0]
    assert bt.S5_ZERO_LABEL_OUT[1] <= bt.S5_EDGE_LABEL_BACK[0]
