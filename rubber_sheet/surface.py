"""LiveSurface: the |H(s)| rubber sheet, a fixed-topology quad mesh updated in place every frame.

- Height of every node = physics.zmap(20 log10 |H(s)|) * lift (lift is a display-only reveal).
- Grid nodes are re-warped every frame toward the current poles / zero (dense where |H| changes
  fast), with a fixed node line on sigma = 0 so the jw cut is exact and the halves split cleanly.
- One vectorized numpy pass computes all face points, colors and Lambert shading; faces get
  their arrays assigned directly (no Surface rebuild, no per-face set_fill parsing).
  Scenes must set camera.should_apply_shading = False (shading is done here, once per face).
"""

import numpy as np
from manim import ThreeDVMobject, ValueTracker, VGroup, VMobject

from rubber_sheet import physics as ph
from rubber_sheet import theme as th

KRAD = 1e3
LIGHT = np.array([-0.45, -0.55, 0.70])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
AMBIENT = 0.58
DIFFUSE = 0.42
Z_CEIL = ph.zmap(np.inf)
TENT_OVERSHOOT = 0.2  # tent poles poke this far (scene units, x lift) above the sheet's ceiling
TENT_TOP = Z_CEIL + TENT_OVERSHOOT


def warped_nodes(a, b, n_cells, centers, amp=10.0, width=0.9, samples=1601):
    """n_cells+1 nodes on [a, b], denser near `centers` (Gaussian density bumps), ends exact."""
    x = np.linspace(a, b, samples)
    rho = np.ones_like(x)
    for c in centers:
        if a - 3 * width <= c <= b + 3 * width:
            rho += amp * np.exp(-0.5 * ((x - c) / width) ** 2)
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (rho[1:] + rho[:-1]) * np.diff(x))])
    cdf /= cdf[-1]
    nodes = np.interp(np.linspace(0.0, 1.0, n_cells + 1), cdf, x)
    nodes[0], nodes[-1] = a, b
    return nodes


class SheetFace(ThreeDVMobject):
    """Sheet quad whose depth-sort reference point is precomputed by LiveSurface (bbox centre of
    its corners), instead of ThreeDCamera calling get_center() on every face every frame."""

    zref = np.zeros(3)

    def get_z_index_reference_point(self):
        return self.zref


def snap_nodes(nodes, centers):
    """Move the nearest interior node exactly onto each center (keeps order). Without this the
    pole falls between nodes by a varying amount as it moves, and the drawn peak bobs (~6 Hz,
    Gate 2 review). Switching which node is snapped moves a node by < half a (dense) cell."""
    nodes = nodes.copy()
    for c in centers:
        i = 1 + int(np.argmin(np.abs(nodes[1:-1] - c)))
        if nodes[i - 1] < c < nodes[i + 1]:
            nodes[i] = c
    return nodes


def _segment_points(corners):
    """corners (F, 5, 3) closed quad -> (F, 16, 3) cubic Bezier points of straight segments."""
    a = corners[:, :-1, :]
    b = corners[:, 1:, :]
    pts = np.stack([a, a + (b - a) / 3.0, a + 2.0 * (b - a) / 3.0, b], axis=2)  # (F, 4, 4, 3)
    return pts.reshape(corners.shape[0], 16, 3)


class LiveSurface(VGroup):
    """Rubber sheet over the s-plane.

    mag_fn(s) -> |H(s)| for complex s in rad/s.
    features_fn() -> dict(sigma=[krad/s...], omega=[krad/s >= 0 ...]) of density centers.
    lift, opacity: ValueTrackers (display-only reveal controls).
    right_drop, right_opacity: display-only controls of the sigma > 0 half (the jw cut in S4).

    Never animate the LiveSurface, its halves or faces directly: refresh() rewrites every face
    each frame (and an animation would suspend the updater). Drive the trackers instead.
    """

    def __init__(self, mag_fn, features_fn, lift, opacity, preset=None):
        super().__init__()
        preset = preset or th.PRESET
        self.mag_fn = mag_fn
        self.features_fn = features_fn
        self.lift = lift
        self.opacity = opacity
        self.right_drop = ValueTracker(0.0)
        self.right_opacity = ValueTracker(1.0)
        self.hidden = False
        self.n_left, self.n_right = preset["sigma_nodes"]
        self.n_half = preset["omega_half"]
        self.n_sigma = self.n_left + self.n_right
        self.n_omega = 2 * self.n_half
        self.lut = th.surface_lut()

        self.left = VGroup()
        self.right = VGroup()
        self.faces = []
        for i in range(self.n_sigma):
            for j in range(self.n_omega):
                face = SheetFace()
                face.set_points_as_corners(np.zeros((5, 3)))
                face.set_fill(th.SURFACE_STOPS[0][1], opacity=0.0)
                face.set_stroke(th.FAINT, width=th.SURFACE_STROKE_WIDTH, opacity=0.0)  # colour set per frame
                (self.left if i < self.n_left else self.right).add(face)
                self.faces.append(face)
        self.add(self.left, self.right)
        self.right_mask = np.repeat(np.arange(self.n_sigma) >= self.n_left, self.n_omega)
        self.nodes = None  # (sigma_krad, omega_krad) of the last refresh
        self.heights = None
        self.node_points = np.zeros((0, 3))
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    # --- geometry -----------------------------------------------------------------------
    def grid(self):
        f = self.features_fn()
        smin, smax = th.SIGMA_RANGE
        sig_c = [c for c in f.get("sigma", []) if c < 0]
        left = snap_nodes(warped_nodes(smin, 0.0, self.n_left, sig_c + [0.0]), sig_c)
        right = warped_nodes(0.0, smax, self.n_right, [0.0], amp=4.0)
        sigma = np.concatenate([left, right[1:]])
        om_c = [c for c in f.get("omega", []) if c >= 0]  # 0: the zero's knot (density only; w = 0 is a node)
        half = snap_nodes(warped_nodes(0.0, th.OMEGA_RANGE[1], self.n_half, om_c, width=1.2), [c for c in om_c if c > 0])
        omega = np.concatenate([-half[::-1], half[1:]])
        return sigma, omega

    def node_heights(self, sigma, omega):
        S = (sigma[:, None] + 1j * omega[None, :]) * KRAD
        # a NaN height would make its face vanish and corrupt the whole depth sort: floor it
        return np.nan_to_num(ph.zmap(ph.to_db(self.mag_fn(S))), nan=0.0)

    def outline_points(self):
        """Node grid in world space: a cheap, exact-enough outline for bbox/overlap checks."""
        return self.node_points

    def refresh(self):
        if self.opacity.get_value() <= 0.0:
            # Fully transparent: drop all face points so nothing is path-built or sorted.
            if not self.hidden:
                for face in self.faces:
                    face.points = np.zeros((0, 3))
                self.node_points = np.zeros((0, 3))
                self.hidden = True
            return self
        self.hidden = False
        sigma, omega = self.grid()
        Z = self.node_heights(sigma, omega) * self.lift.get_value()
        self.nodes, self.heights = (sigma, omega), Z
        X, Y = th.s_to_xy(sigma, omega)
        Xg, Yg = np.meshgrid(X, Y, indexing="ij")
        P = np.stack([Xg, Yg, Z], axis=-1)  # (Ns+1, No+1, 3)

        c0 = P[:-1, :-1]
        c1 = P[1:, :-1]
        c2 = P[1:, 1:]
        c3 = P[:-1, 1:]
        corners = np.stack([c0, c1, c2, c3, c0], axis=2).reshape(-1, 5, 3)
        drop = self.right_drop.get_value()
        if drop:
            corners[self.right_mask, :, 2] -= drop
        # Outline for overlap checks: the left half (node rows 0..n_left, sigma <= 0) as drawn, and
        # the right half (rows n_left.., incl. its own copy of the sigma = 0 edge) only while it
        # is visible, at its dropped height.
        left = P[: self.n_left + 1].reshape(-1, 3)
        if self.right_opacity.get_value() > 0.0:
            right = P[self.n_left :].reshape(-1, 3) - np.array([0.0, 0.0, drop])
            self.node_points = np.vstack([left, right])
        else:
            self.node_points = left
        pts = _segment_points(corners)

        # Lambert shading from the face normal (cross product of diagonals).
        n = np.cross((c2 - c0).reshape(-1, 3), (c3 - c1).reshape(-1, 3))
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        n[n[:, 2] < 0] *= -1.0
        shade = AMBIENT + DIFFUSE * np.clip(n @ LIGHT, 0.0, 1.0)

        zmean = 0.25 * (c0[..., 2] + c1[..., 2] + c2[..., 2] + c3[..., 2]).reshape(-1)
        lift = max(self.lift.get_value(), 1e-6)
        idx = np.clip((zmean / (Z_CEIL * lift) * (len(self.lut) - 1)).astype(int), 0, len(self.lut) - 1)
        rgb = self.lut[idx] * shade[:, None]
        alpha = np.full(len(rgb), self.opacity.get_value())
        alpha[self.right_mask] *= self.right_opacity.get_value()
        fill = np.concatenate([rgb, (th.SURFACE_OPACITY * alpha)[:, None]], axis=1)
        # Stroke = the face's own shaded colour: hides anti-aliasing seams between faces without
        # drawing mesh lines (a uniform dark stroke reads as hatch bands where the warped mesh is
        # dense, which has no physical meaning).
        # While a face fades (alpha < 1) its seam strokes overlap their neighbours at partial
        # opacity and read as a wireframe; they fade faster (alpha^3; unchanged when opaque).
        stroke = np.concatenate([rgb, (th.SURFACE_OPACITY * alpha**3)[:, None]], axis=1)
        zref = 0.5 * (corners[:, :4].min(axis=1) + corners[:, :4].max(axis=1))
        for k, face in enumerate(self.faces):
            face.points = pts[k]
            face.zref = zref[k]
            face.fill_rgbas = fill[k : k + 1]
            face.stroke_rgbas = stroke[k : k + 1]
        return self

    # --- sampling helpers for other objects ----------------------------------------------------
    def height_at(self, sigma_krad, omega_krad):
        """Exact sheet height at s (scene units), same mapping as the mesh."""
        s = (np.asarray(sigma_krad) + 1j * np.asarray(omega_krad)) * KRAD
        return ph.zmap(ph.to_db(self.mag_fn(s))) * self.lift.get_value()


UNDER_SHEET_BIAS = -1e3  # RigCamera depth bias: below the sheet -> painted before every face
ABOVE_SHEET_BIAS = 0.05  # poking out on top -> just after the faces at its own location
# The jw cut lies on the sigma = 0 node line; the faces either side of it have sort points up to
# about half a cell (~0.08 units at preview) nearer the eye. The eye is always on the sigma > 0
# side once the cut exists (theta in (-90, 90)), where the sheet slopes down away from the cut, so
# those faces never cover it: paint each cut piece after them.
CUT_BIAS = 0.25


def _polyline_cubics(pts):
    """(m, 3) polyline -> (4(m-1), 3) Bezier points of its straight segments."""
    a, b = pts[:-1], pts[1:]
    return np.stack([a, a + (b - a) / 3.0, a + 2.0 * (b - a) / 3.0, b], axis=1).reshape(-1, 3)


class CutCurve(VGroup):
    """The exact jw cut: the sheet's height along sigma = 0, drawn in SIGNAL gold.

    Heights are exact samples of the surface's own mag_fn and lift (not read off the mesh), so the
    cut follows whatever the sheet shows (R sweep, hand-moved zero). It is n_pieces short
    shade_in_3d polylines: the painter's order then places each piece among the faces around it
    (one long curve would sort as a single object). Consecutive pieces share one sample of
    overlap, so no gap opens at a joint where the curve bends.

    reveal: drawn fraction, growing from omega_min (display-only). opacity: display-only.
    """

    def __init__(self, surface, n_pieces=60, samples=None, width=th.SIGNAL_WIDTH):
        super().__init__()
        self.surface = surface
        n = samples or th.PRESET["cut_samples"]
        self.omega = np.linspace(*th.OMEGA_RANGE, n + 1)  # krad/s
        self.bounds = np.linspace(0, n, n_pieces + 1).round().astype(int)
        self.reveal = ValueTracker(1.0)
        self.opacity = ValueTracker(1.0)
        self._op = None
        for _ in range(n_pieces):
            piece = VMobject(shade_in_3d=True)
            piece.set_points_as_corners(np.zeros((2, 3)))
            piece.set_stroke(th.SIGNAL, width=width, opacity=1.0)
            piece.depth_bias = CUT_BIAS
            piece.zref = np.zeros(3)
            self.add(piece)
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def world_points(self, omega_krad):
        """Exact points of the cut (scene units) at the given omega values (krad/s)."""
        omega_krad = np.asarray(omega_krad, dtype=float)
        sigma = np.zeros_like(omega_krad)
        x, y = th.s_to_xy(sigma, omega_krad)
        z = np.nan_to_num(self.surface.height_at(sigma, omega_krad), nan=0.0)
        return np.column_stack([x, y, z])

    def refresh(self):
        op, r = self.opacity.get_value(), self.reveal.get_value()
        if op <= 0.0 or r <= 0.0:
            for piece in self.submobjects:
                piece.points = np.zeros((0, 3))
            return self
        pts = self.world_points(self.omega)
        n = len(self.omega) - 1
        end = r * n  # fractional sample index of the drawn tip
        for k, piece in enumerate(self.submobjects):
            a, b = self.bounds[k], min(self.bounds[k + 1] + 1, n)
            if a >= end:
                piece.points = np.zeros((0, 3))
                continue
            seg = pts[a : b + 1]
            if b > end:
                j = int(np.floor(end))
                tip = pts[j] + (end - j) * (pts[min(j + 1, n)] - pts[j])
                seg = np.vstack([pts[a : j + 1], tip])
            piece.points = _polyline_cubics(seg)
            piece.zref = pts[(a + b) // 2]
        if op != self._op:
            for piece in self.submobjects:
                piece.set_stroke(opacity=op, family=False)
            self._op = op
        return self


class TentPole(VGroup):
    """Vertical coral line from the floor at a pole up through the sheet, as stacked short
    segments. Segments under the sheet surface (z < get_sheet_z()) paint before the sheet (seen
    faintly through it); segments above it sort just after the faces at the pole."""

    def __init__(self, get_xy, get_top, get_sheet_z, color, n_segments=24, width=4.0, opacity=None):
        super().__init__()
        self.get_xy = get_xy
        self.get_top = get_top
        self.get_sheet_z = get_sheet_z
        self.opacity = opacity  # optional display-only tracker (a FadeIn would freeze the updater)
        self._op = None
        for _ in range(n_segments):
            seg = VMobject(shade_in_3d=True)
            seg.set_points_as_corners(np.zeros((2, 3)))
            seg.set_stroke(color, width=width, opacity=1.0)
            self.add(seg)
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def refresh(self):
        x, y = self.get_xy()
        top = self.get_top()
        sheet_z = self.get_sheet_z()
        zs = np.linspace(0.0, top, len(self.submobjects) + 1)
        for k, seg in enumerate(self.submobjects):
            a = np.array([x, y, zs[k]])
            b = np.array([x, y, zs[k + 1]])
            seg.points = np.array([a, a + (b - a) / 3, a + 2 * (b - a) / 3, b])
            seg.depth_bias = ABOVE_SHEET_BIAS if zs[k] >= sheet_z - 1e-9 else UNDER_SHEET_BIAS
        if self.opacity is not None and self.opacity.get_value() != self._op:
            self._op = self.opacity.get_value()
            for seg in self.submobjects:
                seg.set_stroke(opacity=self._op, family=False)
        return self


NAIL_RIM_OFFSET = 1.2  # krad/s: where the nail head's height is read (the funnel's rim)
NAIL_HEAD_CLEARANCE = 0.45  # scene units above the rim
NAIL_HEAD_RADIUS = 0.09


class Nail(VGroup):
    """The zero's teal nail: a line from the floor at the zero (where the sheet touches the -40 dB
    floor) up through the funnel to a small flat head just above its rim. Its lower segments sort
    like the tent poles, so the funnel's near wall covers them; the head sits on top.
    get_sigma() -> zero position in krad/s (on the real axis). opacity: display-only tracker."""

    def __init__(self, surface, get_sigma, color=th.ZERO, opacity=None, width=4.0):
        super().__init__()
        self.surface = surface
        self.get_sigma = get_sigma
        self.opacity = opacity
        self.line = TentPole(lambda: tuple(th.s_to_xy(self.get_sigma(), 0.0)), self.top, lambda: 0.0, color, n_segments=12, width=width, opacity=opacity)
        self.head = VMobject(shade_in_3d=True)
        self.head.set_fill(color, opacity=1.0).set_stroke(color, width=1.0, opacity=1.0)
        self.head.depth_bias = ABOVE_SHEET_BIAS + 0.01
        self.add(self.line, self.head)
        self._op = None
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def top(self):
        rim = float(self.surface.height_at(self.get_sigma() + NAIL_RIM_OFFSET, 0.0))
        return (rim + NAIL_HEAD_CLEARANCE) if np.isfinite(rim) else NAIL_HEAD_CLEARANCE

    def refresh(self):
        x, y = th.s_to_xy(self.get_sigma(), 0.0)
        z = self.top()
        a = np.linspace(0.0, 2.0 * np.pi, 25)
        self.head.set_points_as_corners(np.column_stack([x + NAIL_HEAD_RADIUS * np.cos(a), y + NAIL_HEAD_RADIUS * np.sin(a), np.full(25, z)]))
        self.head.zref = np.array([float(x), float(y), z])
        if self.opacity is not None and self.opacity.get_value() != self._op:
            self._op = self.opacity.get_value()
            self.head.set_fill(opacity=self._op, family=False).set_stroke(opacity=self._op, family=False)
        return self

    def outline_points(self):
        x, y = th.s_to_xy(self.get_sigma(), 0.0)
        return np.array([[x, y, 0.0], [x, y, self.top()]]) if (self.opacity is None or self.opacity.get_value() > 0) else np.zeros((0, 3))
