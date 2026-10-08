"""World-space s-plane objects: floor grid, axes, pole/zero markers, |s| = w0 circle, labels.

The s-plane lies in z = 0 (the -40 dB floor). Coordinates come from theme.s_to_xy (krad/s).
"""

import numpy as np
from manim import MathTex, Rectangle, Text, ValueTracker, VGroup, VMobject

from rubber_sheet import physics as ph
from rubber_sheet import theme as th


FLOOR_LAYER = -1  # RigCamera depth layer: drawn before everything else
BIAS_GRID, BIAS_CIRCLE, BIAS_MARKER = 0.0, 500.0, 1000.0  # order inside the floor layer


def _seg(a, b, color, width, opacity=1.0, shade=True, bias=BIAS_GRID):
    m = VMobject(shade_in_3d=shade)
    m.set_points_as_corners([a, b])
    m.set_stroke(color, width=width, opacity=opacity)
    m.depth_layer, m.depth_bias = FLOOR_LAYER, bias
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
        # Tick labels (flat, top view only) on BG-coloured backings so grid lines and the |s|
        # circle do not strike through them.
        self.ticks = VGroup()
        for s in (-15, -10, -5, 5):
            self.ticks.add(_tick(f"{s}", xyz(s, -0.9)))
        for w in (-15, -10, -5, 5, 10, 15):
            lab = _tick(f"{w}", xyz(0, w))
            lab.shift(np.array([lab.width / 2 + 0.06, 0, 0]))
            self.ticks.add(lab)
        self.unit = Text("krad/s", font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
        self.unit.move_to(xyz(smax - 0.2, -2.0)).shift(np.array([-self.unit.width / 2, 0, 0]))
        self.add(self.grid, self.axes, self.ticks, self.unit)


def _tick(text, at):
    label = Text(text.replace("-", "−"), font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
    backing = Rectangle(width=label.width + 0.08, height=label.height + 0.06).set_stroke(width=0).set_fill(th.BG, opacity=1.0)
    return VGroup(backing, label).move_to(at)


class AxisLabels(VGroup):
    """sigma and jw labels. Scenes register them as fixed-orientation billboards; they belong to
    the floor layer (painted before the sheet, so a lifted sheet correctly covers them)."""

    def __init__(self):
        super().__init__()
        smin, smax = th.SIGMA_RANGE
        omin, omax = th.OMEGA_RANGE
        # above the axis end, clear of the '5' tick label below it
        self.sigma = MathTex(r"\sigma", font_size=th.SIZE_MATH, color=th.MUTED).move_to(xyz(smax + 0.9, 1.3))
        self.jw = MathTex(r"j\omega", font_size=th.SIZE_MATH, color=th.MUTED).move_to(xyz(-2.6, omax - 0.9))
        self.add(self.sigma, self.jw)
        for leaf in self.get_family():
            leaf.shade_in_3d = True
            leaf.depth_layer, leaf.depth_bias = FLOOR_LAYER, BIAS_MARKER


CROSS_HALF = 0.13  # half-size of the x marker, world units
CROSS_WIDTH = 4.0


class Cross(VGroup):
    """x marker in the floor plane at a (moving) s-plane point."""

    def __init__(self, get_s_krad, color, size=CROSS_HALF, width=CROSS_WIDTH):
        super().__init__()
        self.get_s = get_s_krad
        self.size = size
        self.a = _seg(np.zeros(3), np.ones(3), color, width, bias=BIAS_MARKER)
        self.b = _seg(np.zeros(3), np.ones(3), color, width, bias=BIAS_MARKER)
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


class ZeroMark(VGroup):
    """o marker in the floor plane at the (moving) zero; opacity: display-only tracker."""

    def __init__(self, get_sigma, color=th.ZERO, radius=CROSS_HALF, width=CROSS_WIDTH, opacity=None):
        super().__init__()
        self.get_sigma = get_sigma
        self.radius = radius
        self.opacity = opacity
        self._op = None
        self.ring = _seg(np.zeros(3), np.ones(3), color, width, bias=BIAS_MARKER)
        self.add(self.ring)
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def refresh(self):
        c = xyz(self.get_sigma(), 0.0, 0.012)
        a = np.linspace(0.0, 2.0 * np.pi, 33)
        self.ring.set_points_as_corners(c + np.column_stack([self.radius * np.cos(a), self.radius * np.sin(a), np.zeros(33)]))
        if self.opacity is not None and self.opacity.get_value() != self._op:
            self._op = self.opacity.get_value()
            self.ring.set_stroke(opacity=self._op, family=False)
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
            m.depth_layer, m.depth_bias = FLOOR_LAYER, BIAS_CIRCLE
            self.add(m)


SIGMA_PLANE_TOP = 3.0  # scene units: above the R = 120 cut (~2.0), below the tent-pole tops (4.3)
UNDER_SHEET = -1e3  # depth bias of plane parts below the sheet surface (same as surface.UNDER_SHEET_BIAS)
# Upper plane parts only ever overlap (on screen) what lies behind the plane: the sigma < 0 half
# and the tent poles. A sigma < 0 face touching sigma = 0 sorts only ~0.02 behind a strip, less than
# the strip's own half-width can shift the distance proxy (teeth along the cut, Gate 4 review), so
# they get the same generous bias as the cut itself.
ABOVE_PLANE_BIAS = 0.25


def _quad(p0, p1, p2, p3):
    return np.array([p0, p1, p2, p3, p0])


class SigmaPlane(VGroup):
    """The gold 'knife' of S4: the vertical plane sigma = 0, z in [0, top], translucent.

    The plane passes through the sheet, and interpenetrating primitives defeat the painter's
    order (a whole strip sorts as one object: staircase artifacts along the intersection, Gate 4
    review). So every strip along omega is split at the exact cut height cut_z(omega):
      upper part  [cut, top]  sorts by distance (+ABOVE_PLANE_BIAS); it only ever overlaps the
                              sigma < 0 half on screen, which lies behind it
      lower part  [0, cut]    lies under the sheet surface: painted before every face, so the
                              sigma > 0 half (in front) covers it; once that half falls away it
                              reads as the gold cross-section under the cut
    Side edges are split the same way; the bottom edge lies on the floor's jw axis (floor layer).
    cut_z(omega_krad array) -> z array. opacity: display-only tracker (0 = hidden).
    """

    def __init__(self, cut_z, top=SIGMA_PLANE_TOP, n_strips=120, color=th.SIGNAL):
        super().__init__()
        self.opacity = ValueTracker(0.0)
        self.cut_z = cut_z
        self.top = top
        self.w = np.linspace(*th.OMEGA_RANGE, n_strips + 1)
        self.upper, self.lower, self.edges = VGroup(), VGroup(), VGroup()

        def piece(group, fill, bias=0.0, layer=0):
            m = VMobject(shade_in_3d=True)
            m.set_points_as_corners(np.zeros((2, 3)))
            if fill:
                m.set_fill(color, opacity=0.0).set_stroke(width=0)
            else:
                m.set_stroke(color, width=th.PLANE_EDGE_WIDTH, opacity=0.0)
            m.depth_bias, m.depth_layer, m.zref = bias, layer, np.zeros(3)
            group.add(m)
            return m

        for _ in range(n_strips):
            piece(self.upper, True, ABOVE_PLANE_BIAS)
            piece(self.lower, True, UNDER_SHEET)
            piece(self.edges, False, ABOVE_PLANE_BIAS + 0.01)  # top edge
        self.floor_edge = piece(VGroup(), False, BIAS_MARKER, FLOOR_LAYER)
        self.sides = [(piece(self.edges, False, UNDER_SHEET), piece(self.edges, False, ABOVE_PLANE_BIAS + 0.01)) for _ in range(2)]
        self.edges.add(self.floor_edge)
        self.add(self.lower, self.upper, self.edges)
        self._op = None
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def outline_points(self):
        (w0, w1), t = th.OMEGA_RANGE, self.top
        return np.array([xyz(0, w0), xyz(0, w1), xyz(0, w0, t), xyz(0, w1, t)]) if self._op else np.zeros((0, 3))

    def refresh(self):
        op = self.opacity.get_value()
        if op <= 0.0 and self._op == 0.0:
            return self
        w, top = self.w, self.top
        z = np.clip(self.cut_z(w), 0.0, top)
        for k, (up, lo, edge) in enumerate(zip(self.upper, self.lower, self.edges)):
            a, b = w[k], w[k + 1]
            up.set_points_as_corners(_quad(xyz(0, a, z[k]), xyz(0, b, z[k + 1]), xyz(0, b, top), xyz(0, a, top)))
            lo.set_points_as_corners(_quad(xyz(0, a), xyz(0, b), xyz(0, b, z[k + 1]), xyz(0, a, z[k])))
            edge.set_points_as_corners([xyz(0, a, top), xyz(0, b, top)])
            mid = 0.5 * (a + b)
            up.zref, lo.zref, edge.zref = xyz(0, mid, top), xyz(0, mid), xyz(0, mid, top)
        self.floor_edge.set_points_as_corners([xyz(0, w[0], 0.01), xyz(0, w[-1], 0.01)])
        self.floor_edge.zref = xyz(0, 0.0, 0.0)
        for (below, above), wv, zv in zip(self.sides, (w[0], w[-1]), (z[0], z[-1])):
            below.set_points_as_corners([xyz(0, wv), xyz(0, wv, zv)])
            above.set_points_as_corners([xyz(0, wv, zv), xyz(0, wv, top)])
            below.zref, above.zref = xyz(0, wv), xyz(0, wv, top)
        if op != self._op:
            for m in (*self.upper, *self.lower):
                m.set_fill(opacity=th.PLANE_FILL_OPACITY * op, family=False)
            for m in self.edges:
                m.set_stroke(opacity=th.PLANE_EDGE_OPACITY * op, family=False)
            self._op = op
        return self


class ScreenLabel(VGroup):
    """A label pinned to a world point with an offset in SCREEN space (fixed-in-frame).

    World-space offsets (as with fixed-orientation billboards) rotate with the camera and can
    swing a label onto other geometry; this keeps it e.g. up-right of its anchor on screen.
    Register it with camera.add_fixed_in_frame_mobjects. Its updater only moves it (in place).
    opacity (optional ValueTracker): fade it with that tracker, never with FadeIn/FadeOut while the
    camera moves (a fade suspends the updater, so the label would stop following its anchor).
    """

    def __init__(self, mob, camera, get_world_point, offset=(0.22, 0.12), opacity=None):
        super().__init__(mob)
        self.camera = camera
        self.get_world_point = get_world_point
        self.offset = np.array([offset[0], offset[1], 0.0])
        self.opacity = opacity
        self._op = None
        # the label's corner nearest the anchor: bottom-left when offset right, bottom-right when left
        self.corner = np.array([-1.0 if offset[0] >= 0 else 1.0, -1.0 if offset[1] >= 0 else 1.0, 0.0])
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def refresh(self):
        p = self.camera.screen_points(self.get_world_point())[0]
        self.move_to(np.array([p[0], p[1], 0.0]) + self.offset, aligned_edge=self.corner)
        if self.opacity is not None and self.opacity.get_value() != self._op:
            self._op = self.opacity.get_value()
            self.submobjects[0].set_opacity(self._op)
        return self
