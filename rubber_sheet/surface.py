"""LiveSurface: the |H(s)| rubber sheet, a fixed-topology quad mesh updated in place every frame.

- Height of every node = physics.zmap(20 log10 |H(s)|) * lift (lift is a display-only reveal).
- Grid nodes are re-warped every frame toward the current poles / zero (dense where |H| changes
  fast), with a fixed node line on sigma = 0 so the jw cut is exact and the halves split cleanly.
- One vectorized numpy pass computes all face points, colors and Lambert shading; faces get
  their arrays assigned directly (no Surface rebuild, no per-face set_fill parsing).
  Scenes must set camera.should_apply_shading = False (shading is done here, once per face).
"""

import numpy as np
from manim import ThreeDVMobject, VGroup, VMobject

from rubber_sheet import physics as ph
from rubber_sheet import theme as th

KRAD = 1e3
LIGHT = np.array([-0.45, -0.55, 0.70])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
AMBIENT = 0.58
DIFFUSE = 0.42
Z_CEIL = ph.zmap(np.inf)


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
    """

    def __init__(self, mag_fn, features_fn, lift, opacity, preset=None):
        super().__init__()
        preset = preset or th.PRESET
        self.mag_fn = mag_fn
        self.features_fn = features_fn
        self.lift = lift
        self.opacity = opacity
        self.n_left, self.n_right = preset["sigma_nodes"]
        self.n_half = preset["omega_half"]
        self.n_sigma = self.n_left + self.n_right
        self.n_omega = 2 * self.n_half
        self.lut = th.surface_lut()
        self.stroke_rgb = np.array(th.FAINT.to_rgb())

        self.left = VGroup()
        self.right = VGroup()
        self.faces = []
        for i in range(self.n_sigma):
            for j in range(self.n_omega):
                face = SheetFace()
                face.set_points_as_corners(np.zeros((5, 3)))
                face.set_fill(th.SURFACE_STOPS[0][1], opacity=0.0)
                face.set_stroke(th.FAINT, width=th.SURFACE_STROKE_WIDTH, opacity=0.0)
                (self.left if i < self.n_left else self.right).add(face)
                self.faces.append(face)
        self.add(self.left, self.right)
        self.nodes = None  # (sigma_krad, omega_krad) of the last refresh
        self.heights = None
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    # --- geometry -----------------------------------------------------------------------
    def grid(self):
        f = self.features_fn()
        smin, smax = th.SIGMA_RANGE
        sig_c = [c for c in f.get("sigma", []) if c < 0] + [0.0]
        left = warped_nodes(smin, 0.0, self.n_left, sig_c)
        right = warped_nodes(0.0, smax, self.n_right, [0.0], amp=4.0)
        sigma = np.concatenate([left, right[1:]])
        om_c = list(f.get("omega", []))
        half = warped_nodes(0.0, th.OMEGA_RANGE[1], self.n_half, om_c, width=1.2)
        omega = np.concatenate([-half[::-1], half[1:]])
        return sigma, omega

    def node_heights(self, sigma, omega):
        S = (sigma[:, None] + 1j * omega[None, :]) * KRAD
        return ph.zmap(ph.to_db(self.mag_fn(S)))

    def refresh(self):
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
        alpha = th.SURFACE_OPACITY * self.opacity.get_value()
        fill = np.concatenate([rgb, np.full((len(rgb), 1), alpha)], axis=1)
        stroke = np.concatenate(
            [np.tile(self.stroke_rgb, (len(rgb), 1)), np.full((len(rgb), 1), th.SURFACE_STROKE_OPACITY * self.opacity.get_value())],
            axis=1,
        )
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


class TentPole(VGroup):
    """Vertical coral line from the floor at a pole up to the sheet, as stacked short segments
    (each depth-sorts locally against nearby faces)."""

    def __init__(self, get_xy, get_top, color, n_segments=24, width=4.0):
        super().__init__()
        self.get_xy = get_xy
        self.get_top = get_top
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
        zs = np.linspace(0.0, top, len(self.submobjects) + 1)
        for k, seg in enumerate(self.submobjects):
            a = np.array([x, y, zs[k]])
            b = np.array([x, y, zs[k + 1]])
            seg.points = np.array([a, a + (b - a) / 3, a + 2 * (b - a) / 3, b])
        return self
