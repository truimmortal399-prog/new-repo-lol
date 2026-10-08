"""Gate 2 probe: which fixed-in-frame + updater patterns survive a camera move in Cairo ThreeDScene?

Patterns (each a uniquely colored mobject registered fixed-in-frame, camera moves phi 0 -> 70):
  A  persistent VMobject, points mutated in place by an updater (our panel/curve pattern)
  B  always_redraw, same structure every frame
  C  always_redraw whose submobject count grows (2 -> 4 squares)
  D  DecimalNumber driven by a ValueTracker (stock readout)
  E  our Readout (fixed digit slots, points replaced in place) driven by a ValueTracker
Rendered with the stock ThreeDCamera (ProbeStock) and with RigCamera (ProbeRig). Pixel centroids
of each color on the first and last frame are written to out/probe/<Scene>.json.

  .venv/bin/manim -ql scenes/probe_fixed_frame.py ProbeStock ProbeRig
"""

import json
import os
import sys

import numpy as np
from manim import (
    DEGREES,
    DecimalNumber,
    Square,
    ThreeDCamera,
    ThreeDScene,
    ValueTracker,
    VGroup,
    VMobject,
    always_redraw,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rubber_sheet import theme as th  # noqa: E402
from rubber_sheet.panels import Readout  # noqa: E402
from rubber_sheet.rig import RigCamera  # noqa: E402

th.configure()
COLORS = {
    "A_inplace": "#FF0000",
    "B_redraw_same": "#00FF00",
    "C_redraw_grow": "#0000FF",
    "D_decimal": "#FF00FF",
    "E_readout": "#FFFF00",
}


def centroid(frame, hex_color, tol=60):
    rgb = np.array([int(hex_color[i : i + 2], 16) for i in (1, 3, 5)])
    d = np.abs(frame[:, :, :3].astype(int) - rgb).sum(axis=2)
    ys, xs = np.nonzero(d < tol)
    if len(xs) == 0:
        return None
    return dict(x=round(float(xs.mean()), 1), y=round(float(ys.mean()), 1), n=int(len(xs)), h=int(ys.max() - ys.min() + 1))


class _Probe(ThreeDScene):
    CAMERA = ThreeDCamera

    def __init__(self, **kwargs):
        super().__init__(camera_class=self.CAMERA, **kwargs)

    def construct(self):
        t = ValueTracker(0.0)

        a = VMobject().set_fill(COLORS["A_inplace"], 1).set_stroke(width=0)

        def upd_a(m):
            x = -5.5 + 0.3 * np.sin(4 * t.get_value())
            m.set_points_as_corners([[x, 2.5, 0], [x + 1, 2.5, 0], [x + 1, 3.3, 0], [x, 3.3, 0], [x, 2.5, 0]])

        upd_a(a)
        a.add_updater(upd_a)

        b = always_redraw(lambda: Square(0.8, fill_opacity=1, stroke_width=0, color=COLORS["B_redraw_same"]).move_to([-2.5, 2.9, 0]))
        c = always_redraw(
            lambda: VGroup(*[Square(0.5, fill_opacity=1, stroke_width=0, color=COLORS["C_redraw_grow"]) for _ in range(2 + int(t.get_value() > 0.5) * 2)])
            .arrange(buff=0.1)
            .move_to([1.0, 2.9, 0])
        )
        d = DecimalNumber(0.0, num_decimal_places=2, color=COLORS["D_decimal"], font_size=60).move_to([4.5, 2.9, 0])
        d.add_updater(lambda m: m.set_value(10 * t.get_value()))
        e = Readout("<i>R</i> =", lambda: 100 * t.get_value(), "{:.1f}", unit="Ω", size=40, color=COLORS["E_readout"]).place([-1.5, -2.5, 0])

        mobs = dict(A_inplace=a, B_redraw_same=b, C_redraw_grow=c, D_decimal=d, E_readout=e)
        self.add_fixed_in_frame_mobjects(*mobs.values())
        frames = []
        recorder = VMobject()
        recorder.add_updater(lambda m: frames.append(self.renderer.get_frame().copy()))
        self.add(recorder)
        self.play(
            t.animate.set_value(1.0),
            self.camera.phi_tracker.animate.set_value(70 * DEGREES),
            self.camera.theta_tracker.animate.set_value(-40 * DEGREES),
            run_time=1.0,
        )
        first, last = frames[1], self.renderer.get_frame()
        out = {}
        for name, color in COLORS.items():
            c0, c1 = centroid(first, color), centroid(last, color)
            moved = None
            if c0 and c1:
                moved = round(float(np.hypot(c1["x"] - c0["x"], c1["y"] - c0["y"])), 1)
            out[name] = dict(first=c0, last=c1, centroid_shift_px=moved)
        os.makedirs("out/probe", exist_ok=True)
        with open(f"out/probe/{type(self).__name__}.json", "w") as f:
            json.dump(out, f, indent=1)
        print(type(self).__name__, json.dumps({k: v["centroid_shift_px"] for k, v in out.items()}))


class ProbeStock(_Probe):
    CAMERA = ThreeDCamera


class ProbeRig(_Probe):
    CAMERA = RigCamera
