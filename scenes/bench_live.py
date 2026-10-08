"""Gate 2/3 throwaway benchmark: the heaviest representative frame load of the film.

Live LiveSurface (mesh from RS_QUALITY), Bode + impulse panels and readouts with real updaters,
fixed HUD (formula, height tag, scrim, one caption), tent poles, floor — R sweeps 120 -> 4 ohm
(log) while theta drifts, in the ANALYSIS layout. Duration from BENCH_SECONDS (default 2).

  RS_QUALITY=final BENCH_SECONDS=2 .venv/bin/manim -qh --fps 60 scenes/bench_live.py BenchLive
"""

import os
import sys
import time

import numpy as np
from manim import DEGREES, ThreeDScene, UpdateFromAlphaFunc, VGroup, config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import camera as cam  # noqa: E402
from rubber_sheet import captions, common, world  # noqa: E402
from rubber_sheet import physics as ph  # noqa: E402
from rubber_sheet import script as sc  # noqa: E402
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.panels import BodePanel, ImpulsePanel, Readout  # noqa: E402
from rubber_sheet.rig import RigCamera, apply_state  # noqa: E402

th.configure()
SECONDS = float(os.environ.get("BENCH_SECONDS", "2"))


class BenchLive(ThreeDScene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=RigCamera, **kwargs)

    def construct(self):
        rig = self.camera
        apply_state(rig, cam.ANALYSIS)
        sheet = common.SheetAssembly(lift=1.0, opacity=1.0)
        R = sheet.R
        floor = world.SPlaneFloor()
        floor.remove(floor.ticks, floor.unit)
        labels = world.AxisLabels()
        labels.remove(labels.jw)  # faded out in S3 before the panels ever appear
        rig.add_fixed_orientation_mobjects(labels.sigma)

        formula = common.formula_HC()
        tag = common.height_tag(formula)
        bode = BodePanel(lambda w: ph.mag_C(1j * w, R.get_value()), th.BODE_BOX)
        imp = ImpulsePanel(R.get_value, th.IMPULSE_BOX)
        readouts = VGroup(
            Readout("<i>R</i> =", R.get_value, "{:.1f}", unit="Ω", n_slots=5).place([-6.3, -1.75, 0]),
            Readout("<i>ζ</i> =", lambda: ph.zeta(R.get_value()), "{:.3f}", n_slots=5).place([-6.3, -2.2, 0]),
            Readout("peak", lambda: 20 * np.log10(ph.resonance(R.get_value())[1]), "{:.1f}", unit="dB", size=th.SIZE_SMALL, color=th.SIGNAL, n_slots=5)
            .place([0, bode.title.get_center()[1], 0]).align_right(bode.box[1]),
        )
        scrim = captions.make_scrim()
        caption = captions.Caption(sc.BY_ID["C13"])
        hud = [formula, tag, bode, imp, readouts, scrim, caption]
        rig.add_fixed_in_frame_mobjects(*hud)
        self.add(floor, world.DashedCircle(), sheet.crosses, sheet.surface, sheet.tents, labels, *hud)
        # The overlap/stray monitor is part of every real scene, so it is part of the benchmark.
        track = captions.CaptionTrack(self, "S6", check_every=th.MONITOR_EVERY)
        for name, mob, fixed in [("sheet", sheet.surface, False), ("bode", bode, True), ("impulse", imp, True), ("readouts", readouts, True), ("formula", formula, True), ("height tag", tag, True)]:
            track.protect(name, mob, fixed)
        self.add_updater(track.monitor())

        t_start = time.perf_counter()
        self.play(
            _log_sweep(R, SECONDS),
            rig.theta_tracker.animate(rate_func=th.LINEAR).set_value((cam.ANALYSIS.theta + 8.0 * SECONDS / 11.5) * DEGREES),
            run_time=SECONDS,
        )
        wall = time.perf_counter() - t_start
        frames = int(round(SECONDS * config.frame_rate))
        print(f"BENCH faces={len(sheet.surface.faces)} quality={th.QUALITY} seconds={SECONDS} wall={wall:.1f}s frames={frames}")


def _log_sweep(R, seconds):
    """R from R_START to R_SWEEP_END, logarithmic in time (same mapping as the film's sweep)."""
    return UpdateFromAlphaFunc(R, lambda m, a: m.set_value(float(ph.r_of_sweep(th.SWEEP(a)))), run_time=seconds)
