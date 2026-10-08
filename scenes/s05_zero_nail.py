"""S5 (film 35.72–48.31 s): probe the resistor — a zero nails the sheet to the floor, then back.

Beats (film time; spans and the zero schedule in rubber_sheet/beats.py):
  35.72  camera returns CUT -> ANALYSIS (4.2 s); the 'jw' label leaves; 'output: v_C' appears
  36.00  the sigma > 0 half comes back (S4 lowered it)
  36.20  probe moves C -> R: v_C -> v_R, numerator 1 -> RCs (formula H_R)
  37.20  disclosure 'interpolated: zero moved by hand'; the zero arrives from -inf (b = -1/z
         linear) to the domain edge at 38.0, then slides to the origin 38.0-41.0 (H_z is a real
         transfer function at every step; z = -inf is exactly H_C, z = 0 exactly H_R)
  41.00  nail holds; 43.6 slides back; 45.6 probe R -> C, formula H_C; 47.0 zero gone (exactly H_C)
Captions C9, C10, C11 from rubber_sheet/script.py.

  RS_QUALITY=preview .venv/bin/manim -ql scenes/s05_zero_nail.py S5ZeroNail
"""

import os
import sys

from manim import UP, FadeIn, FadeOut, MathTex, Text, ThreeDScene, ValueTracker, VGroup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import beats as bt  # noqa: E402
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import captions, common, world  # noqa: E402
from rubber_sheet import layout as L  # noqa: E402
from rubber_sheet import physics as ph  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.panels import BodePanel  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state, move_anims  # noqa: E402
from rubber_sheet.surface import CutCurve, Nail  # noqa: E402
from rubber_sheet.timeline import Timeline  # noqa: E402

th.configure()


def run(span):
    return span[1] - span[0]


class S5ZeroNail(ThreeDScene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=RigCamera, **kwargs)

    def construct(self):
        rig = self.camera
        apply_state(rig, cam.CUT)
        tl = Timeline("S5")
        track = self.caption_track = captions.CaptionTrack(self, "S5", check_every=th.MONITOR_EVERY)

        # --- the hand-moved zero: u in [0, 2] (physics.zero_slide), u = 0 -> none (H_C) ---------
        u = ValueTracker(0.0)

        def zero():
            return ph.zero_slide(u.get_value())  # rad/s, -inf = no zero

        # --- world: S4's end state ------------------------------------------------------------
        sheet = common.SheetAssembly(lift=1.0, opacity=1.0, zero=zero)
        surf = sheet.surface
        surf.right_drop.set_value(bt.RIGHT_DROP_DEPTH)
        surf.right_opacity.set_value(0.0)
        floor = world.SPlaneFloor()
        floor.remove(floor.ticks, floor.unit)
        labels = world.AxisLabels()
        labels.remove(labels.jw)
        circle = world.DashedCircle()
        rig.add_fixed_orientation_mobjects(labels.sigma)
        cut = CutCurve(surf)

        def zero_sigma():  # krad/s, clamped onto the domain edge while the zero is off it
            return max(zero() / 1e3, th.SIGMA_RANGE[0])

        zero_opacity = ValueTracker(0.0)
        nail = Nail(surf, zero_sigma, opacity=zero_opacity)
        ring = world.ZeroMark(zero_sigma, opacity=zero_opacity)

        # --- screen (fixed in frame) ------------------------------------------------------------
        formula = common.formula_HC()
        formula_R = common.formula_HR()
        num_C = VGroup(*formula[2][common.NUMERATOR_HC])
        num_R = VGroup(*formula_R[2][common.NUMERATOR_HR])
        tag = common.height_tag(formula)
        scrim = captions.make_scrim()
        probe = common.probe_label("C")
        probe_R = common.probe_label("R")
        sub_C, sub_R = probe[-1], probe_R[-1]  # only the subscript changes
        # Faded-out mobjects stay faded until the scene's single play ends, so the way back uses
        # its own (registered) copies of the C glyphs.
        sub_C_back, num_C_back = sub_C.copy(), num_C.copy()
        disclosure = common.disclosure_tag()
        jw_opacity = ValueTracker(1.0)
        jw_label = world.ScreenLabel(MathTex(r"j\omega", font_size=th.SIZE_MATH, color=th.MUTED), rig,
                                     lambda: world.xyz(*L.JW_LABEL_ANCHOR), L.JW_LABEL_OFFSET, opacity=jw_opacity)
        label_opacity = ValueTracker(0.0)
        zero_label = world.ScreenLabel(Text("zero", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.ZERO), rig,
                                       lambda: world.xyz(zero_sigma(), 0.0, nail.top()), (0.16, 0.1), opacity=label_opacity)
        edge_opacity = ValueTracker(0.0)
        edge_text = Text("from −∞", font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.ZERO)
        edge_label = world.ScreenLabel(edge_text, rig, lambda: world.xyz(th.SIGMA_RANGE[0], 0.0, nail.top()), (0.16, 0.1), opacity=edge_opacity)
        exit_opacity = ValueTracker(0.0)
        exit_text = Text("to −∞", font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.ZERO)
        exit_label = world.ScreenLabel(exit_text, rig, lambda: world.xyz(th.SIGMA_RANGE[0], 0.0, nail.top()), (0.16, 0.1), opacity=exit_opacity)
        bode = BodePanel(lambda w: sheet.mag(1j * w), th.BODE_BOX, warp=ValueTracker(1.0))

        hud = [scrim, formula, num_R, num_C_back, tag, probe, sub_R, sub_C_back, disclosure, jw_label, zero_label, edge_label, exit_label, bode]
        rig.add_fixed_in_frame_mobjects(*hud)
        track.register_fixed()
        self.add(floor, circle, sheet.crosses, ring, surf, sheet.tents, nail, cut)  # sigma label: faded in S4, back at 39.3
        self.add(scrim, formula, tag, probe, jw_label, zero_label, edge_label, exit_label, bode)

        # --- protected visuals (overlap checker) -----------------------------------------------
        track.protect("formula", formula, True)
        track.protect("formula numerators", VGroup(num_R, num_C_back), True)
        track.protect("height tag", tag, True)
        track.protect("probe", VGroup(probe, sub_R, sub_C_back), True)
        track.protect("disclosure", disclosure, True)
        track.protect("bode", bode, True)
        track.protect("sheet", surf, False)
        track.protect("jw cut", cut, False)
        track.protect("nail", nail, False)
        track.protect("floor", floor.grid, False)
        track.protect("circle", circle, False)
        track.protect("pole marks", sheet.crosses, False)
        track.protect("axis labels", labels, False)
        track.protect("tent poles", sheet.tents, False)
        track.protect("jw label", jw_label, True, annotation=True)
        track.protect("zero label", zero_label, True, annotation=True)
        track.protect("edge label", edge_label, True, annotation=True)
        track.protect("exit label", exit_label, True, annotation=True)
        self.add_updater(track.monitor())

        # --- timeline (film times) ----------------------------------------------------------------
        back = cam.moves_in("S5")[0]
        tl.at(back.t0, *move_anims(rig, back))
        tl.at(bt.S5_JW_LABEL_OUT[0], jw_opacity.animate(run_time=run(bt.S5_JW_LABEL_OUT), rate_func=th.EXIT).set_value(0.0))
        tl.at(bt.S5_RIGHT_RESTORE[0],
              surf.right_drop.animate(run_time=run(bt.S5_RIGHT_RESTORE), rate_func=th.SWEEP).set_value(0.0),
              surf.right_opacity.animate(run_time=run(bt.S5_RIGHT_RESTORE), rate_func=th.SWEEP).set_value(1.0))
        # probe C -> R: only the subscript and the numerator change (registered mobjects only)
        swap = dict(run_time=run(bt.S5_PROBE_TO_R), rate_func=th.SWEEP)
        tl.at(bt.S5_PROBE_TO_R[0], FadeOut(sub_C, shift=0.12 * UP, **swap), FadeIn(sub_R, shift=0.12 * UP, **swap),
              FadeOut(num_C, shift=0.12 * UP, **swap), FadeIn(num_R, shift=0.12 * UP, **swap))
        tl.at(bt.DISCLOSURE_SPAN[0], FadeIn(disclosure, run_time=0.5, rate_func=th.ENTER))
        tl.at(bt.S5_EDGE_LABEL_IN[0], edge_opacity.animate(run_time=run(bt.S5_EDGE_LABEL_IN), rate_func=th.ENTER).set_value(1.0))
        for (t0, t1), a, b, ease in bt.S5_ZERO_PHASES:
            tl.at(t0, u.animate(run_time=t1 - t0, rate_func=getattr(th, ease)).set_value(b))
        tl.at(bt.S5_ZERO_SHOW[0], zero_opacity.animate(run_time=run(bt.S5_ZERO_SHOW), rate_func=th.ENTER).set_value(1.0))
        tl.at(bt.S5_EDGE_LABEL_OUT[0], edge_opacity.animate(run_time=run(bt.S5_EDGE_LABEL_OUT), rate_func=th.EXIT).set_value(0.0))
        tl.at(bt.S5_ZERO_LABEL_IN[0], label_opacity.animate(run_time=run(bt.S5_ZERO_LABEL_IN), rate_func=th.ENTER).set_value(1.0))
        tl.at(bt.S5_SIGMA_LABEL_IN[0], FadeIn(labels.sigma, run_time=run(bt.S5_SIGMA_LABEL_IN), rate_func=th.ENTER))
        # return
        swap_back = dict(run_time=run(bt.S5_PROBE_TO_C), rate_func=th.SWEEP)
        tl.at(bt.S5_PROBE_TO_C[0], FadeOut(sub_R, shift=0.12 * UP, **swap_back), FadeIn(sub_C_back, shift=0.12 * UP, **swap_back),
              FadeOut(num_R, shift=0.12 * UP, **swap_back), FadeIn(num_C_back, shift=0.12 * UP, **swap_back))
        tl.at(bt.S5_ZERO_LABEL_OUT[0], label_opacity.animate(run_time=run(bt.S5_ZERO_LABEL_OUT), rate_func=th.EXIT).set_value(0.0))
        tl.at(bt.S5_EDGE_LABEL_BACK[0], exit_opacity.animate(run_time=run(bt.S5_EDGE_LABEL_BACK), rate_func=th.ENTER).set_value(1.0))
        tl.at(bt.S5_ZERO_HIDE[0], zero_opacity.animate(run_time=run(bt.S5_ZERO_HIDE), rate_func=th.EXIT).set_value(0.0))
        tl.at(bt.S5_EDGE_LABEL_GONE[0], exit_opacity.animate(run_time=run(bt.S5_EDGE_LABEL_GONE), rate_func=th.EXIT).set_value(0.0))
        tl.at(bt.DISCLOSURE_SPAN[1] - 0.4, FadeOut(disclosure, run_time=0.4, rate_func=th.EXIT))
        tl.extend(track.clips())
        tl.play(self)
        track.write_log()
