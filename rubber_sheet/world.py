"""World-space s-plane objects: floor grid, axes, pole/zero markers, |s| = w0 circle, labels.

The s-plane lies in z = 0 (the -40 dB floor). Coordinates come from theme.s_to_xy (krad/s).
"""

import numpy as np
from manim import MathTex, Text, VGroup, VMobject

from rubber_sheet import physics as ph
from rubber_sheet import theme as th


def _seg(a, b, color, width, opacity=1.0, shade=True):
    m = VMobject(shade_in_3d=shade)
    m.set_points_as_corners([a, b])
    m.set_stroke(color, width=width, opacity=opacity)
    return m


def xyz(sigma_krad, omega_krad, z=0.0):
    x, y = th.s_to_xy(sigma_krad, omega_krad)
    return np.array([float(x), float(y), float(z)])


class SPlaneFloor(VGroup):
    """Grid every 5 krad/s, sigma and jw axes, tick labels (flat, for the top view)."""

    def __init__(self):
        super().__init__()
        smin, smax = th.SIGMA_RANGE
        omin, omax = th.OMEGA_RANGE
        self.grid = VGroup()
        for s in np.arange(smin, smax + 1e-9, 5.0):
            if abs(s) > 1e-9:
                self.grid.add(_seg(xyz(s, omin), xyz(s, omax), th.FAINT, 1.2))
        for w in np.arange(omin, omax + 1e-9, 5.0):
            if abs(w) > 1e-9:
                self.grid.add(_seg(xyz(smin, w), xyz(smax, w), th.FAINT, 1.2))
        self.axes = VGroup(
            _seg(xyz(smin, 0), xyz(smax, 0), th.MUTED, 2.0),
            _seg(xyz(0, omin), xyz(0, omax), th.MUTED, 2.0),
        )
        self.ticks = VGroup()
        for s in (-15, -10, -5, 5):
            t = Text(f"{s}".replace("-", "−"), font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
            t.move_to(xyz(s, -0.9))
            self.ticks.add(t)
        for w in (-15, -10, -5, 5, 10, 15):
            t = Text(f"{w}".replace("-", "−"), font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
            t.next_to(xyz(0, w), np.array([1.0, 0, 0]), buff=0.08)
            self.ticks.add(t)
        self.unit = Text("krad/s", font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
        self.unit.move_to(xyz(smax - 0.2, -2.0)).shift(np.array([-self.unit.width / 2, 0, 0]))
        self.add(self.grid, self.axes, self.ticks, self.unit)


class AxisLabels(VGroup):
    """sigma and jw labels; scenes register them as fixed-orientation billboards."""

    def __init__(self):
        super().__init__()
        smin, smax = th.SIGMA_RANGE
        omin, omax = th.OMEGA_RANGE
        self.sigma = MathTex(r"\sigma", font_size=th.SIZE_MATH, color=th.MUTED).move_to(xyz(smax + 0.9, 0))
        self.jw = MathTex(r"j\omega", font_size=th.SIZE_MATH, color=th.MUTED).move_to(xyz(-1.5, omax - 0.6))
        self.add(self.sigma, self.jw)


CROSS_HALF = 0.13  # half-size of the x marker, world units
CROSS_WIDTH = 4.0


class Cross(VGroup):
    """x marker in the floor plane at a (moving) s-plane point."""

    def __init__(self, get_s_krad, color, size=CROSS_HALF, width=CROSS_WIDTH):
        super().__init__()
        self.get_s = get_s_krad
        self.size = size
        self.a = _seg(np.zeros(3), np.ones(3), color, width)
        self.b = _seg(np.zeros(3), np.ones(3), color, width)
        self.add(self.a, self.b)
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def refresh(self):
        s = self.get_s()
        c = xyz(s.real, s.imag, 0.012)
        d = self.size
        self.a.set_points_as_corners([c + [-d, -d, 0], c + [d, d, 0]])
        self.b.set_points_as_corners([c + [-d, d, 0], c + [d, -d, 0]])
        return self


class DashedCircle(VGroup):
    """|s| = w0 in the floor plane as short shaded dashes, clipped to the s-plane domain."""

    def __init__(self, radius_krad=ph.OMEGA0 / 1e3, color=th.MUTED, n_dashes=72, width=1.6, opacity=0.8):
        super().__init__()
        a = np.linspace(0, 2 * np.pi, 2 * n_dashes + 1)
        for k in range(n_dashes):
            ang = np.linspace(a[2 * k], a[2 * k + 1], 4)
            if np.any(radius_krad * np.cos(ang) > th.SIGMA_RANGE[1]):
                continue
            x, y = th.s_to_xy(radius_krad * np.cos(ang), radius_krad * np.sin(ang))
            m = VMobject(shade_in_3d=True)
            m.set_points_as_corners(np.column_stack([x, y, np.full(4, 0.006)]))
            m.set_stroke(color, width=width, opacity=opacity)
            self.add(m)
