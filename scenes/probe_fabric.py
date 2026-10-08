"""Diagnostic (not in the film): 3 s of the moving sheet for the fabric-texture shimmer check.

The sheet's same-colour seam strokes read as a fine fabric weave. This clip stresses them the
way the film will: the camera swings at the film's top speed (~14 deg/s) while R falls, so the
warped mesh nodes slide under the strokes. Rendered at 4K60, final mesh, then Lanczos-downscaled
to 1080p exactly like the deliverable (tools/fabric_check.py).

  RS_QUALITY=final .venv/bin/manim -qk --fps 60 scenes/probe_fabric.py ProbeFabric
"""

import os
import sys

from manim import DEGREES, ThreeDScene, UpdateFromAlphaFunc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import common, world  # noqa: E402
from rubber_sheet import physics as ph  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state  # noqa: E402

th.configure()
SECONDS = 3.0
SWING_DEG = 40.0  # theta -50 -> -10: 13.3 deg/s, the film's top camera speed
# A/B switch for the check: PROBE_STROKE=0 renders the same clip without the seam strokes.
th.SURFACE_STROKE_WIDTH = float(os.environ.get("PROBE_STROKE", th.SURFACE_STROKE_WIDTH))


class ProbeFabric(ThreeDScene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=RigCamera, **kwargs)

    def construct(self):
        rig = self.camera
        apply_state(rig, cam.S3_END)
        sheet = common.SheetAssembly(lift=1.0, opacity=1.0)
        floor = world.SPlaneFloor()
        floor.remove(floor.ticks, floor.unit)
        self.add(floor, world.DashedCircle(), sheet.crosses, sheet.surface, sheet.tents)
        R = sheet.R
        theta0 = cam.S3_END.theta
        self.play(
            rig.theta_tracker.animate(rate_func=th.LINEAR).set_value((theta0 + SWING_DEG) * DEGREES),
            UpdateFromAlphaFunc(R, lambda m, a: m.set_value(float(ph.R_START * (0.5 ** a))), rate_func=th.LINEAR),
            run_time=SECONDS,
        )
