"""RigCamera: a ThreeDCamera whose frame_center is only the 3D rotation pivot.

Stock Cairo ThreeDCamera uses frame_center twice: as the pivot in project_points and again in
the base pixel mapping (points_to_subpixel_coords, the cairo context matrix, is_in_frame). That
double-shifts 3D content and also moves fixed-in-frame mobjects. Here the base mapping always
sees ORIGIN; the pivot is ThreeDCamera's own `_frame_center` point (so set_camera_orientation /
move_camera(frame_center=...) still drive it), and pan_x / pan_y translate projected 3D content
on screen without touching fixed-in-frame mobjects.
"""

import numpy as np
from manim import DEGREES, Camera, ThreeDCamera, ValueTracker
from manim.utils.family import extract_mobject_family_members

from rubber_sheet import camera as cam


class RigCamera(ThreeDCamera):
    """Also re-derives the fixed-in-frame set from the registered roots on every capture, so
    children that join a fixed mobject later (always_redraw padding, VGroup.add) stay fixed.
    Shading is off: LiveSurface shades its faces itself (vectorized)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pan_x = ValueTracker(0.0)
        self.pan_y = ValueTracker(0.0)
        self.fixed_roots = []
        self.should_apply_shading = False

    def add_fixed_in_frame_mobjects(self, *mobjects):
        for m in mobjects:
            if m not in self.fixed_roots:
                self.fixed_roots.append(m)
        super().add_fixed_in_frame_mobjects(*mobjects)

    def remove_fixed_in_frame_mobjects(self, *mobjects):
        self.fixed_roots = [m for m in self.fixed_roots if m not in mobjects]
        super().remove_fixed_in_frame_mobjects(*mobjects)

    def capture_mobjects(self, mobjects, **kwargs):
        self.fixed_in_frame_mobjects = set(extract_mobject_family_members(self.fixed_roots))
        super().capture_mobjects(mobjects, **kwargs)

    @property
    def frame_center(self):
        return np.zeros(3)

    @frame_center.setter
    def frame_center(self, point):
        if hasattr(self, "_frame_center"):
            self._frame_center.move_to(point)

    def pivot(self):
        return self._frame_center.points[0]

    def eye(self):
        """World position of the eye (perspective centre)."""
        rot = self.get_rotation_matrix()
        return self.pivot() + rot.T @ np.array([0.0, 0.0, self.get_focal_distance()])

    def get_mobjects_to_display(self, *args, **kwargs):
        """Painter's order for a height field seen from above.

        Stock ThreeDCamera sorts by each leaf's bbox-centre view depth, which mis-sorts the steep
        faces at the pole spikes (4-114 back-face pixels at 1080p, Gate 2 probe). Here 3D leaves
        are drawn far-to-near by HORIZONTAL distance from the eye (0 back-face pixels), with:
          depth_layer -1  floor objects (always first: the camera is always above the floor)
          depth_bias      per-object offset inside its layer (e.g. tent pole below/above sheet)
        Leaves without shade_in_3d (text, fixed overlays) keep +inf: drawn last, in scene order.
        """
        mobs = Camera.get_mobjects_to_display(self, *args, **kwargs)
        eye = self.eye()
        keys = np.empty(len(mobs))
        for i, m in enumerate(mobs):
            if not getattr(m, "shade_in_3d", False):
                keys[i] = np.inf
                continue
            ref = m.zref if hasattr(m, "zref") else m.get_center()
            dist = np.hypot(ref[0] - eye[0], ref[1] - eye[1])
            keys[i] = getattr(m, "depth_layer", 0) * 1e6 - dist + getattr(m, "depth_bias", 0.0)
        return [mobs[i] for i in np.argsort(keys, kind="stable")]

    def project_points(self, points):
        focal_distance = self.get_focal_distance()
        zoom = self.get_zoom()
        rot_matrix = self.get_rotation_matrix()
        points = np.dot(np.asarray(points) - self.pivot(), rot_matrix.T)
        zs = points[:, 2]
        for i in 0, 1:
            if self.exponential_projection:
                factor = np.exp(zs / focal_distance)
                lt0 = zs < 0
                factor[lt0] = focal_distance / (focal_distance - zs[lt0])
            else:
                factor = focal_distance / (focal_distance - zs)
                factor[(focal_distance - zs) < 0] = 10**6
            points[:, i] *= factor * zoom
        points[:, 0] += self.pan_x.get_value()
        points[:, 1] += self.pan_y.get_value()
        return points

    def screen_points(self, points):
        """World points -> frame coordinates (same space as fixed-in-frame mobjects).

        Refreshes the rotation matrix first: the stock camera only does that inside
        capture_mobjects, so calls from updaters would otherwise use last frame's angles."""
        self.reset_rotation_matrix()
        return self.project_points(np.atleast_2d(np.asarray(points, dtype=float)))


def apply_state(camera, state):
    camera.phi_tracker.set_value(state.phi * DEGREES)
    camera.theta_tracker.set_value(state.theta * DEGREES)
    camera.zoom_tracker.set_value(state.zoom)
    camera._frame_center.move_to(np.array(state.pivot, dtype=float))
    camera.pan_x.set_value(state.pan[0])
    camera.pan_y.set_value(state.pan[1])


def move_anims(camera, move):
    """Animations for a planned camera Move (all components on the same trapezoid profile)."""
    rate = cam.trapezoid(move.run_time)
    kw = dict(run_time=move.run_time, rate_func=rate)
    end = move.end
    return [
        camera.phi_tracker.animate(**kw).set_value(end.phi * DEGREES),
        camera.theta_tracker.animate(**kw).set_value(end.theta * DEGREES),
        camera.zoom_tracker.animate(**kw).set_value(end.zoom),
        camera._frame_center.animate(**kw).move_to(np.array(end.pivot, dtype=float)),
        camera.pan_x.animate(**kw).set_value(end.pan[0]),
        camera.pan_y.animate(**kw).set_value(end.pan[1]),
    ]
