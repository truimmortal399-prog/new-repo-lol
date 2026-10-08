"""S3 (film 11.60–25.00 s): the poles land in the s-plane, then the gain lifts into a rubber sheet.

Beats (film time):
  11.60  s-plane fades in under the H(s) formula (top view looks 2D)
  11.80  LCs^2+RCs+1 = 0  =>  s = -6 +/- j8 krad/s (numbers from physics); x marks fly to the plane
  15.60  camera tilts (phi 0 -> 58, trapezoid); flat tick labels fade
  18.00  sheet lifts (display-only lift 0 -> 1); height tag "height = 20 log10|H| (dB)" appears
  21.00  theta swing -90 -> -50; "pole" labels on the tent poles (21.2)
Captions C3, C4, C5 from rubber_sheet/script.py.

  RS_QUALITY=preview .venv/bin/manim -ql scenes/s03_poles_sheet.py S3PolesSheet
"""

import os
import sys

import numpy as np
from manim import RIGHT, FadeIn, FadeOut, LaggedStart, Line, Text, ThreeDScene, Transform, VGroup, Write

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import captions, common, world  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state, move_anims  # noqa: E402
from rubber_sheet.surface import Z_CEIL  # noqa: E402
from rubber_sheet.timeline import Timeline  # noqa: E402

th.configure()
SWAP = 0.05  # duration of the invisible fixed-frame -> world handoff


def screen_cross(center, half, width=world.CROSS_WIDTH):
    a = Line(center + np.array([-half, -half, 0]), center + np.array([half, half, 0]))
    b = Line(center + np.array([-half, half, 0]), center + np.array([half, -half, 0]))
    return VGroup(a, b).set_stroke(th.POLE, width=width)


class S3PolesSheet(ThreeDScene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=RigCamera, **kwargs)

    def construct(self):
        rig = self.camera
        apply_state(rig, cam.TOP)
        tl = Timeline("S3")
        track = self.caption_track = captions.CaptionTrack(self, "S3", check_every=2)

        # --- world -------------------------------------------------------------------------
        sheet = common.SheetAssembly()
        floor = world.SPlaneFloor()
        labels = world.AxisLabels()
        circle = world.DashedCircle()
        rig.add_fixed_orientation_mobjects(labels.sigma, labels.jw)

        # --- screen (fixed in frame) ---------------------------------------------------------
        formula = common.formula_HC()
        roots = common.roots_block(formula)
        tag = common.height_tag(formula)
        scrim = captions.make_scrim()
        # x marks at the exact screen positions of the world poles in the (static) top view
        half = world.CROSS_HALF * cam.TOP.zoom
        targets = [rig.screen_points(world.xyz(sheet.pole(k).real, sheet.pole(k).imag, 0.012))[0] for k in (0, 1)]
        targets = [np.array([p[0], p[1], 0.0]) for p in targets]
        flyers = [roots[1][2].copy() for _ in (0, 1)]
        landing = [screen_cross(p, half) for p in targets]
        pole_labels = VGroup()
        for k in (0, 1):
            lab = Text("pole", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.POLE)
            p = sheet.pole(k)
            lab.move_to(world.xyz(p.real, p.imag, Z_CEIL + 0.55)).shift(0.42 * RIGHT)  # above the lifted tent pole
            pole_labels.add(lab)
        rig.add_fixed_orientation_mobjects(*pole_labels, use_static_center_func=True)

        rig.add_fixed_in_frame_mobjects(formula, scrim, roots, tag, *flyers)
        track.register_fixed()
        self.add(sheet.surface)  # invisible until 18.0 (opacity tracker 0); its updater runs throughout
        self.add(scrim, formula)

        # --- protected visuals (overlap checker) -----------------------------------------------
        track.protect("formula", formula, True)
        track.protect("roots", roots, True)
        track.protect("height tag", tag, True)
        track.protect("sheet", sheet.surface, False)
        track.protect("tent poles", sheet.tents, False)
        track.protect("pole labels", pole_labels, False)
        self.add_updater(track.monitor())

        # --- timeline (film times) ----------------------------------------------------------------
        tl.at(11.60, FadeIn(floor, run_time=0.8, rate_func=th.ENTER), FadeIn(labels, run_time=0.8, rate_func=th.ENTER))
        tl.at(11.80, Write(roots[0], run_time=0.8))
        tl.at(12.70, FadeIn(roots[1], shift=0.06 * RIGHT, run_time=0.6, rate_func=th.ENTER))
        tl.at(13.40, *[Transform(f, l, run_time=1.0, rate_func=th.SWEEP) for f, l in zip(flyers, landing)])
        tl.at(13.60, LaggedStart(*[FadeIn(d) for d in circle], lag_ratio=0.03, run_time=1.0))
        tl.at(14.40, *[FadeOut(f, run_time=SWAP) for f in flyers], FadeIn(sheet.crosses, run_time=SWAP))
        tl.at(15.40, FadeOut(roots, run_time=0.4, rate_func=th.EXIT))
        tl.at(15.60, *move_anims(rig, cam.MOVES[0]))
        tl.at(15.60, FadeOut(VGroup(floor.ticks, floor.unit), run_time=0.8, rate_func=th.EXIT))
        tl.at(18.00, sheet.opacity.animate(run_time=0.8, rate_func=th.ENTER).set_value(1.0))
        tl.at(18.00, sheet.lift.animate(run_time=2.5, rate_func=th.SWEEP).set_value(1.0))
        tl.at(18.00, FadeIn(sheet.tents, run_time=0.4), FadeIn(tag, run_time=0.6, rate_func=th.ENTER))
        tl.at(21.00, *move_anims(rig, cam.MOVES[1]))
        tl.at(21.20, FadeIn(pole_labels, run_time=0.6, rate_func=th.ENTER))
        tl.extend(track.clips())
        tl.play(self)
        track.write_log()
