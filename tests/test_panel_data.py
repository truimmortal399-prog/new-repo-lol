"""Plotted data == physics: invert the panels' screen transforms on the drawn curve points and
compare against scipy.signal (independent reference). Catches plotting bugs, not just math bugs."""

import numpy as np
import pytest
from manim import ValueTracker
from scipy import signal

from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet.panels import BodePanel, ImpulsePanel


def anchors(vmob):
    pts = vmob.points
    return np.vstack([pts[::4], pts[-1:]])[:, :2]


@pytest.mark.parametrize("R", [120.0, 40.0, 4.0])
@pytest.mark.parametrize("mu", [1.0, 0.0, 0.5])
def test_bode_curve_points_match_scipy(R, mu):
    warp = ValueTracker(mu)
    panel = BodePanel(lambda w: ph.mag_C(1j * w, R), th.BODE_BOX, warp=warp)
    xy = anchors(panel.curve)
    u, db = panel.from_screen(xy).T  # u = normalized x in [0, 1]
    # invert x_of_w numerically on a fine grid (monotone in w for any mu in [0, 1])
    wg = np.logspace(1, 5.4, 200001)
    xg = panel.x_of_w(wg)
    w = np.interp(u, xg, wg)
    _, H = signal.freqresp(signal.TransferFunction([1.0], ph.denominator_coeffs(R)), w)
    ref = np.clip(20 * np.log10(np.abs(H)), *BodePanel.DB)
    assert np.max(np.abs(db - ref)) < 0.05
    assert len(xy) > 100


@pytest.mark.parametrize("R", [120.0, 40.0, 4.0, 0.0])
def test_impulse_curve_points_match_scipy(R):
    panel = ImpulsePanel(lambda: R, th.IMPULSE_BOX)
    t_ms, h = panel.from_screen(anchors(panel.curve)).T
    _, h_ref = signal.impulse(signal.TransferFunction([1.0], ph.denominator_coeffs(R)), T=t_ms * 1e-3)
    ref = np.clip(h_ref / ph.OMEGA0, *ImpulsePanel.Y)
    assert np.max(np.abs(h - ref)) < 0.005 * (ImpulsePanel.Y[1] - ImpulsePanel.Y[0])


@pytest.mark.parametrize("R", [120.0, 4.0])
def test_impulse_envelope_bounds_curve(R):
    panel = ImpulsePanel(lambda: R, th.IMPULSE_BOX)
    t_ms, h = panel.from_screen(anchors(panel.curve)).T
    env = ph.impulse_envelope(t_ms * 1e-3, R) / ph.OMEGA0
    assert np.all(np.abs(h) <= env + 1e-9)


@pytest.mark.parametrize("mu", [1.0, 0.0])
def test_bode_ticks_agree_with_drawn_data(mu):
    """The '10' krad/s tick sits where the drawn R = 4 ohm curve peaks (w_r = 9.996 krad/s),
    and every visible decade label's text matches the frequency it is placed at."""
    R = ph.R_SWEEP_END
    panel = BodePanel(lambda w: ph.mag_C(1j * w, R), th.BODE_BOX, warp=ValueTracker(mu))
    xy = anchors(panel.curve)
    peak_x = xy[np.argmax(xy[:, 1]), 0]
    tick10 = panel.decade_labels[1]
    assert tick10.text == "10"
    assert abs(tick10.get_center()[0] - peak_x) < 0.01 * (panel.box[1] - panel.box[0])
    for lab, w in zip(panel.decade_labels, (1e3, 1e4, 1e5)):
        assert float(lab.text) * 1e3 == w
        if lab.get_fill_opacity() > 0:
            assert abs(lab.get_center()[0] - panel.to_screen([panel.x_of_w(w)], [0])[0, 0]) < 1e-9
