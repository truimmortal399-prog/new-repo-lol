"""S3 (film 11.60–25.00 s): the poles land in the s-plane, then the gain lifts into a rubber sheet.

Beats (film time):
  11.60  s-plane fades in under the H(s) formula (top view looks 2D)
  11.80  LCs^2+RCs+1 = 0  =>  s = -6 +/- j8 krad/s (numbers from physics); x marks fly to the plane
  15.00  one camera move to S3_END (phi 0 -> 58, theta -90 -> -50, 6 s); flat tick labels fade
  18.00  sheet lifts (display-only lift 0 -> 1); height tag "height = 20 log10|H| (dB)" appears
  21.20  "pole" labels on the tent poles (the poles are apart on screen from the lift on)
Captions C3, C4, C5 from rubber_sheet/script.py.

  RS_QUALITY=preview .venv/bin/manim -ql scenes/s03_poles_sheet.py S3PolesSheet
"""

import os
import sys

import numpy as np
from manim import RIGHT, FadeIn, FadeOut, LaggedStart, Line, Text, ThreeDScene, VGroup, Write

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import beats as bt  # noqa: E402
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
        track = self.caption_track = captions.CaptionTrack(self, "S3", check_every=th.MONITOR_EVERY)

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
        # Two small x marks leave from the end of the solution line and fly to the poles (the
        # equation itself stays intact); at 14.40 they hand over to the identical world marks.
        start = roots[1].get_right() + np.array([0.35, 0.0, 0.0])
        flyers = [screen_cross(start, 0.45 * half) for _ in targets]
        pole_labels = VGroup()
        for k in (0, 1):
            lab = Text("pole", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.POLE)
            # lower pole (nearer the camera during the theta swing): label up-left, clear of the far crown
            offset = (-0.22, 0.12) if k == 0 else (0.22, 0.12)
            pole_labels.add(world.ScreenLabel(lab, rig, lambda k=k: world.xyz(sheet.pole(k).real, sheet.pole(k).imag, Z_CEIL + 0.3), offset))
        rig.add_fixed_in_frame_mobjects(formula, scrim, roots, tag, *flyers, *pole_labels)
        track.register_fixed()
        self.add(sheet.surface, sheet.tents)  # invisible until 18.0 (opacity 0, zero-length poles)
        self.add(scrim, formula)

        # --- protected visuals (overlap checker) -----------------------------------------------
        track.allow_world(floor.ticks, floor.unit)  # flat labels on the floor, faded before the tilt
        track.protect("formula", formula, True)
        track.protect("roots", roots, True)
        track.protect("height tag", tag, True)
        track.protect("sheet", sheet.surface, False)
        track.protect("floor", floor.grid, False)
        track.protect("circle", circle, False)
        track.protect("pole marks", sheet.crosses, False)
        track.protect("axis labels", labels, False)
        track.protect("tent poles", sheet.tents, False)
        track.protect("pole labels", pole_labels, True, annotation=True)
        self.add_updater(track.monitor())

        # --- timeline (film times) ----------------------------------------------------------------
        tl.at(11.60, FadeIn(floor, run_time=0.8, rate_func=th.ENTER), FadeIn(labels, run_time=0.8, rate_func=th.ENTER))
        tl.at(11.80, Write(roots[0], run_time=0.8, rate_func=th.ENTER))
        tl.at(12.70, FadeIn(roots[1], shift=0.06 * RIGHT, run_time=0.6, rate_func=th.ENTER))
        # Only registered (fixed) mobjects may be rendered: no FadeTransform/TransformFromCopy here, they
        # put unregistered copies on screen, which a ThreeDScene projects as world objects.
        tl.at(13.30, *[FadeIn(f, scale=0.5, run_time=0.25, rate_func=th.ENTER) for f in flyers])
        tl.at(13.55, *[f.animate(run_time=0.85, rate_func=th.SWEEP).move_to(p).scale(1.0 / 0.45) for f, p in zip(flyers, targets)])
        tl.at(13.60, LaggedStart(*[FadeIn(d, rate_func=th.ENTER) for d in circle], lag_ratio=0.03, run_time=1.0))
        tl.at(14.40, *[FadeOut(m, run_time=SWAP, rate_func=th.LINEAR) for m in flyers], FadeIn(sheet.crosses, run_time=SWAP, rate_func=th.LINEAR))
        tl.at(15.40, FadeOut(roots, run_time=0.4, rate_func=th.EXIT))
        s3_move = cam.moves_in("S3")[0]
        tl.at(s3_move.t0, *move_anims(rig, s3_move))
        tl.at(s3_move.t0, FadeOut(VGroup(floor.ticks, floor.unit), run_time=0.8, rate_func=th.EXIT))
        tl.at(bt.S3_LIFT_START, sheet.opacity.animate(run_time=bt.S3_SHEET_FADE_RUN, rate_func=th.SWEEP).set_value(1.0))
        tl.at(bt.S3_LIFT_START, sheet.lift.animate(run_time=bt.S3_LIFT_RUN, rate_func=th.SWEEP).set_value(1.0))
        # Tent poles are in the scene from the start: their length is (ceiling + 0.3) * lift, so
        # they grow out of the floor with the lift. (A FadeIn would suspend their updaters.)
        tl.at(bt.S3_LIFT_START, FadeIn(tag, run_time=0.6, rate_func=th.ENTER))
        # the jw floor label would be half-covered by the lifted sheet's far edge; S4 labels the
        # jw axis on the cut itself. sigma stays (it lies outside the sheet's footprint).
        tl.at(bt.S3_LIFT_START, FadeOut(labels.jw, run_time=0.6, rate_func=th.EXIT))
        tl.at(bt.S3_POLE_LABELS, FadeIn(pole_labels, run_time=0.6, rate_func=th.ENTER))
        tl.extend(track.clips())
        tl.play(self)
        track.write_log()
