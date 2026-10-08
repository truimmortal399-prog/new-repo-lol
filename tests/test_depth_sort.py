"""RigCamera paints the sheet in a correct height-field order: no back face is ever visible.

Faces are coloured by facing (front blue, back red) and captured through RigCamera's own
get_mobjects_to_display; any red pixel is a painter's-order error (the stock bbox-centre key
leaves 4-114 such pixels at the pole spikes). Also checks layer/bias ordering of other objects."""

import numpy as np
import pytest
from manim import tempconfig

from rubber_sheet import camera as cam
from rubber_sheet import theme as th
from rubber_sheet import world
from rubber_sheet.common import SheetAssembly
from rubber_sheet.rig import RigCamera, apply_state
from rubber_sheet.surface import ABOVE_SHEET_BIAS, UNDER_SHEET_BIAS


def capture_red_pixels(R, state):
    with tempconfig({"pixel_width": 854, "pixel_height": 480}):
        # final mesh: the coarse preview mesh has a few genuinely visible silhouette back faces
        sheet = SheetAssembly(R=R, lift=1.0, opacity=1.0, preset=th._PRESETS["final"])
        c = RigCamera()
        apply_state(c, state)
        c.reset_rotation_matrix()
        eye = c.eye()
        for f in sheet.surface.faces:
            p = f.points[[0, 4, 8, 12]]
            n = np.cross(p[2] - p[0], p[3] - p[1])
            front = np.dot(n, eye - p.mean(0)) > 0
            f.fill_rgbas = np.array([[0.1, 0.3, 1.0, 1.0]]) if front else np.array([[1.0, 0.0, 0.0, 1.0]])
            f.stroke_rgbas = np.zeros((1, 4))
        c.capture_mobjects([sheet.surface])
        px = c.pixel_array[..., :3].astype(int)
        return int(((px[..., 0] > 150) & (px[..., 2] < 80)).sum())


@pytest.mark.parametrize("state", ["S3_END", "ANALYSIS", "HERO"])
@pytest.mark.parametrize("R", [120.0, 4.0])
def test_no_back_faces_visible(R, state):
    assert capture_red_pixels(R, getattr(cam, state)) == 0


def test_layers_and_biases():
    sheet = SheetAssembly(R=4.0, lift=1.0, opacity=1.0)
    floor = world.SPlaneFloor()
    c = RigCamera()
    apply_state(c, cam.ANALYSIS)
    c.reset_rotation_matrix()
    order = c.get_mobjects_to_display([floor.grid, sheet.crosses, sheet.surface, sheet.tents])
    pos = {id(m): i for i, m in enumerate(order)}
    faces = [pos[id(f)] for f in sheet.surface.faces]
    floor_leaves = [pos[id(m)] for m in floor.grid.get_family() if m.has_points()]
    cross_leaves = [pos[id(m)] for m in sheet.crosses.get_family() if m.has_points()]
    assert max(floor_leaves) < min(cross_leaves) < min(faces)  # floor, then markers, then sheet
    for tent in sheet.tents:
        segs = tent.submobjects
        assert any(s.depth_bias == UNDER_SHEET_BIAS for s in segs) and any(s.depth_bias == ABOVE_SHEET_BIAS for s in segs)
        under = [pos[id(s)] for s in segs if s.depth_bias == UNDER_SHEET_BIAS]
        assert max(under) < min(faces)  # the part below the sheet is painted before the sheet
