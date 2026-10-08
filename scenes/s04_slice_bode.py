"""S4 (film 25.00–35.72 s): slice the sheet along jw; the cut's edge becomes the Bode plot.

Beats (film time; spans in rubber_sheet/beats.py):
  25.00  S3's 'pole' labels leave (camera still holding S3_END)
  25.30  gold sigma = 0 plane fades in; 'jw' labels the far end of the floor's jw axis
  25.40  one camera move to CUT (theta -50 -> 0, phi 58 -> 82), 4.8 s; the sigma label leaves
  25.80  the exact jw cut (physics, not the mesh) grows along the plane
  26.00  the sigma > 0 half lowers and fades: the cut is now the sheet's edge; plane leaves 27.4
  30.30  handoff: the w >= 0 half of the cut becomes a fixed-frame curve (same pixels), flies
         into the Bode panel (linear w) 30.4-31.8 and swaps for the panel's live curve
  33.20  display-only axis warp: linear w -> log10 w (2 s)
Captions C6, C7, C8 from rubber_sheet/script.py.

  RS_QUALITY=preview .venv/bin/manim -ql scenes/s04_slice_bode.py S4SliceBode
"""

import os
import sys

import numpy as np
from manim import FadeIn, FadeOut, MathTex, Text, ThreeDScene, Transform, ValueTracker, VGroup, VMobject

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import beats as bt  # noqa: E402
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import captions, common, world  # noqa: E402
from rubber_sheet import layout as L  # noqa: E402
from rubber_sheet import physics as ph  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.panels import BodePanel  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state, move_anims  # noqa: E402
from rubber_sheet.surface import Z_CEIL, CutCurve, _polyline_cubics  # noqa: E402
from rubber_sheet.timeline import Timeline  # noqa: E402

th.configure()
FLY_SAMPLES = 301  # w = 0..15 krad/s, the linear Bode axis


def run(span):
    return span[1] - span[0]


class S4SliceBode(ThreeDScene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=RigCamera, **kwargs)

    def construct(self):
        rig = self.camera
        apply_state(rig, cam.S3_END)
        tl = Timeline("S4")
        track = self.caption_track = captions.CaptionTrack(self, "S4", check_every=th.MONITOR_EVERY)

        # --- world: S3's end state ------------------------------------------------------------
        sheet = common.SheetAssembly(lift=1.0, opacity=1.0)
        R = sheet.R
        floor = world.SPlaneFloor()
        floor.remove(floor.ticks, floor.unit)  # faded out in S3
        labels = world.AxisLabels()
        labels.remove(labels.jw)  # faded out in S3; jw is labelled on screen below
        circle = world.DashedCircle()
        rig.add_fixed_orientation_mobjects(labels.sigma)
        cut = CutCurve(sheet.surface)
        cut.reveal.set_value(0.0)
        plane = world.SigmaPlane(lambda w: cut.world_points(w)[:, 2])

        # --- screen (fixed in frame) ------------------------------------------------------------
        formula = common.formula_HC()
        tag = common.height_tag(formula)
        scrim = captions.make_scrim()
        pole_labels = VGroup()
        for k in (0, 1):  # exactly as S3 leaves them
            lab = Text("pole", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.POLE)
            offset = (-0.22, 0.12) if k == 0 else (0.22, 0.12)
            pole_labels.add(world.ScreenLabel(lab, rig, lambda k=k: world.xyz(sheet.pole(k).real, sheet.pole(k).imag, Z_CEIL + 0.3), offset))
        jw_opacity = ValueTracker(0.0)
        jw_label = world.ScreenLabel(MathTex(r"j\omega", font_size=th.SIZE_MATH, color=th.MUTED), rig,
                                     lambda: world.xyz(*L.JW_LABEL_ANCHOR), L.JW_LABEL_OFFSET, opacity=jw_opacity)
        warp = ValueTracker(0.0)  # display-only axis warp: 0 linear w, 1 log10 w
        bode = BodePanel(lambda w: ph.mag_C(1j * w, R.get_value()), th.BODE_BOX, warp=warp)
        bode.opacity.set_value(0.0)
        bode.curve_opacity.set_value(0.0)
        probe = common.probe_label("C")  # what the panel measures: the voltage across C

        # Handoff: the w >= 0 half of the cut as it projects in the (static) CUT view, as one fixed
        # curve, and its target: the same frequencies on the panel's linear axis. Same sample
        # order, so the Transform moves each frequency's point straight to its place.
        w_krad = np.linspace(0.0, th.OMEGA_RANGE[1], FLY_SAMPLES)
        at_cut = RigCamera()
        apply_state(at_cut, cam.CUT)
        flyer = VMobject().set_stroke(th.SIGNAL, width=th.SIGNAL_WIDTH)
        flyer.points = _polyline_cubics(at_cut.screen_points(cut.world_points(w_krad)) * np.array([1.0, 1.0, 0.0]))
        target = VMobject().set_stroke(th.SIGNAL, width=th.SIGNAL_WIDTH)
        xy = bode.screen_curve(w_krad * 1e3, mu=0.0)
        target.points = _polyline_cubics(np.column_stack([xy, np.zeros(len(xy))]))

        rig.add_fixed_in_frame_mobjects(scrim, formula, tag, probe, *pole_labels, jw_label, bode, flyer)
        track.register_fixed()
        self.add(floor, circle, sheet.crosses, sheet.surface, sheet.tents, cut, plane, labels)
        self.add(scrim, formula, tag, pole_labels, jw_label, bode)

        # --- protected visuals (overlap checker) -----------------------------------------------
        track.protect("formula", formula, True)
        track.protect("height tag", tag, True)
        track.protect("bode", bode, True)
        track.protect("probe", probe, True)
        track.protect("sheet", sheet.surface, False)
        track.protect("jw cut", cut, False)
        track.protect("sigma plane", plane, False)
        track.protect("floor", floor.grid, False)
        track.protect("circle", circle, False)
        track.protect("pole marks", sheet.crosses, False)
        track.protect("axis labels", labels, False)
        track.protect("tent poles", sheet.tents, False)
        track.protect("pole labels", pole_labels, True, annotation=True)
        track.protect("jw label", jw_label, True, annotation=True)
        track.protect("handoff curve", flyer, True, annotation=True)  # flies over the scene on purpose
        self.add_updater(track.monitor())

        # --- timeline (film times) ----------------------------------------------------------------
        # ScreenLabels follow the camera by updater: fade them only while the camera holds.
        tl.at(bt.S4_POLE_LABELS_OUT[0], FadeOut(pole_labels, run_time=run(bt.S4_POLE_LABELS_OUT), rate_func=th.EXIT))
        tl.at(bt.S4_PLANE_IN[0], plane.opacity.animate(run_time=run(bt.S4_PLANE_IN), rate_func=th.ENTER).set_value(1.0))
        tl.at(bt.S4_JW_LABEL_IN[0], jw_opacity.animate(run_time=run(bt.S4_JW_LABEL_IN), rate_func=th.ENTER).set_value(1.0))
        swing = cam.moves_in("S4")[0]
        tl.at(swing.t0, *move_anims(rig, swing))
        tl.at(bt.S4_SIGMA_LABEL_OUT[0], FadeOut(labels.sigma, run_time=run(bt.S4_SIGMA_LABEL_OUT), rate_func=th.EXIT))
        tl.at(bt.S4_CUT_DRAW[0], cut.reveal.animate(run_time=run(bt.S4_CUT_DRAW), rate_func=th.SWEEP).set_value(1.0))
        surf = sheet.surface
        tl.at(bt.S4_RIGHT_DROP[0],
              surf.right_drop.animate(run_time=run(bt.S4_RIGHT_DROP), rate_func=th.SWEEP).set_value(bt.RIGHT_DROP_DEPTH),
              surf.right_opacity.animate(run_time=run(bt.S4_RIGHT_DROP), rate_func=th.SWEEP).set_value(0.0))
        tl.at(bt.S4_PLANE_OUT[0], plane.opacity.animate(run_time=run(bt.S4_PLANE_OUT), rate_func=th.EXIT).set_value(0.0))
        # handoff: identical pixels, then the flight (only registered mobjects are ever rendered)
        tl.at(bt.S4_HANDOFF, FadeIn(flyer, run_time=bt.SWAP, rate_func=th.LINEAR))
        tl.at(bt.S4_FLY[0], Transform(flyer, target, run_time=run(bt.S4_FLY), rate_func=th.SWEEP))
        tl.at(bt.S4_PANEL_IN[0], bode.opacity.animate(run_time=run(bt.S4_PANEL_IN), rate_func=th.ENTER).set_value(1.0),
              FadeIn(probe, run_time=run(bt.S4_PANEL_IN), rate_func=th.ENTER))
        tl.at(bt.S4_SWAP, FadeOut(flyer, run_time=bt.SWAP, rate_func=th.LINEAR),
              bode.curve_opacity.animate(run_time=bt.SWAP, rate_func=th.LINEAR).set_value(1.0))
        tl.at(bt.S4_WARP[0], warp.animate(run_time=run(bt.S4_WARP), rate_func=th.SWEEP).set_value(1.0))
        tl.extend(track.clips())
        tl.play(self)
        track.write_log()
