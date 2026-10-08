"""S6 (film 48.31–61.00 s): lower R — the poles creep toward the jw axis; peak sharpens, ringing lengthens.

Beats (film time; spans in rubber_sheet/beats.py):
  48.31  impulse panel, R / zeta readouts and the gold Bode peak readout join (1.2 s)
  49.50  R = 120 * (4/120)^u, u = smooth(alpha), 11.5 s (physics.r_of_sweep): the poles glide on
         |s| = w0, sheet, jw cut, Bode curve, h(t) + envelope and readouts all follow R
  49.50  slow camera drift ANALYSIS -> ANALYSIS_DRIFT (theta -40 -> -48, 11.5 s)
Captions C12, C13, C14 from rubber_sheet/script.py.

  RS_QUALITY=preview .venv/bin/manim -ql scenes/s06_sweep.py S6Sweep
"""

import os
import sys

from manim import ThreeDScene, UpdateFromAlphaFunc, ValueTracker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import beats as bt  # noqa: E402
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import captions, common, world  # noqa: E402
from rubber_sheet import physics as ph  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.panels import BodePanel, ImpulsePanel  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state, move_anims  # noqa: E402
from rubber_sheet.surface import CutCurve  # noqa: E402
from rubber_sheet.timeline import Timeline  # noqa: E402

th.configure()


def run(span):
    return span[1] - span[0]


class S6Sweep(ThreeDScene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=RigCamera, **kwargs)

    def construct(self):
        rig = self.camera
        apply_state(rig, cam.ANALYSIS)
        tl = Timeline("S6")
        track = self.caption_track = captions.CaptionTrack(self, "S6", check_every=th.MONITOR_EVERY)

        # --- world: S5's end state ------------------------------------------------------------
        sheet = common.SheetAssembly(lift=1.0, opacity=1.0)
        R = sheet.R
        floor = world.SPlaneFloor()
        floor.remove(floor.ticks, floor.unit)
        labels = world.AxisLabels()
        labels.remove(labels.jw)
        circle = world.DashedCircle()
        rig.add_fixed_orientation_mobjects(labels.sigma)
        cut = CutCurve(sheet.surface)

        # --- screen (fixed in frame) ------------------------------------------------------------
        formula = common.formula_HC()
        tag = common.height_tag(formula)
        probe = common.probe_label("C")
        scrim = captions.make_scrim()
        bode = BodePanel(lambda w: ph.mag_C(1j * w, R.get_value()), th.BODE_BOX, warp=ValueTracker(1.0))
        imp = ImpulsePanel(R.get_value, th.IMPULSE_BOX)
        imp.opacity.set_value(0.0)
        readout_opacity = ValueTracker(0.0)
        readouts = common.readouts(R.get_value, opacity=readout_opacity)
        peak = common.peak_readout(R.get_value, bode, opacity=readout_opacity)
        rig.add_fixed_in_frame_mobjects(scrim, formula, tag, probe, bode, imp, readouts, peak)
        track.register_fixed()
        self.add(floor, circle, sheet.crosses, sheet.surface, sheet.tents, cut, labels)
        self.add(scrim, formula, tag, probe, bode, imp, readouts, peak)

        # --- protected visuals (overlap checker) -----------------------------------------------
        for name, mob in (("formula", formula), ("height tag", tag), ("probe", probe), ("bode", bode), ("impulse", imp),
                          ("readouts", readouts), ("peak readout", peak)):
            track.protect(name, mob, True)
        for name, mob in (("sheet", sheet.surface), ("jw cut", cut), ("floor", floor.grid), ("circle", circle),
                          ("pole marks", sheet.crosses), ("axis labels", labels), ("tent poles", sheet.tents)):
            track.protect(name, mob, False)
        self.add_updater(track.monitor())

        # --- timeline (film times) ----------------------------------------------------------------
        tl.at(bt.S6_PANELS_IN[0], imp.opacity.animate(run_time=run(bt.S6_PANELS_IN), rate_func=th.ENTER).set_value(1.0),
              readout_opacity.animate(run_time=run(bt.S6_PANELS_IN), rate_func=th.ENTER).set_value(1.0))
        # data clock: the sweep parameter is eased, R follows physics.r_of_sweep (log in R)
        tl.at(bt.S6_SWEEP[0], UpdateFromAlphaFunc(R, lambda m, a: m.set_value(float(ph.r_of_sweep(th.SWEEP(a)))),
                                                  run_time=run(bt.S6_SWEEP), rate_func=th.LINEAR))
        drift = cam.moves_in("S6")[0]
        tl.at(drift.t0, *move_anims(rig, drift))
        tl.extend(track.clips())
        tl.play(self)
        track.write_log()
