"""Pieces shared by several scenes: the H(s) formula block, the height tag, the sheet assembly."""

import numpy as np
from manim import DOWN, LEFT, RIGHT, UL, MarkupText, MathTex, Text, ValueTracker, VGroup

from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet import world
from rubber_sheet.surface import Z_CEIL, LiveSurface, TentPole

FORMULA_ANCHOR_BUFF = 0.72  # keeps the formula inside the 5% title-safe area


def formula_HC():
    """H(s) for the capacitor output, at its top-left anchor (S2 end == S3 start)."""
    f = MathTex(r"H(s)", "=", r"\frac{1}{LCs^2+RCs+1}", font_size=th.SIZE_MATH, color=th.FG)
    return f.to_corner(UL, buff=FORMULA_ANCHOR_BUFF)


def formula_HR():
    """H(s) for the resistor output, placed so its fraction bar and denominator coincide with
    formula_HC() (only the numerator differs: 1 -> RCs). Glyphs: [2][0:3] = RCs, [2][3] = bar."""
    f = MathTex(r"H(s)", "=", r"\frac{RCs}{LCs^2+RCs+1}", font_size=th.SIZE_MATH, color=th.FG)
    c = formula_HC()
    return f.shift(c[2][1].get_center() - f[2][3].get_center())


NUMERATOR_HC = slice(0, 1)  # formula_HC()[2][...]: the "1"
NUMERATOR_HR = slice(0, 3)  # formula_HR()[2][...]: "RCs"
PROBE_X = -1.35  # left edge of the probe label / disclosure column, right of the formula


def probe_label(which="C"):
    """'output: v_C' (or v_R) right of the formula, centred on its fraction bar. The last glyph
    is the subscript, which is all that changes between C and R."""
    lab = MarkupText(f"output:  <i>v</i><sub>{which}</sub>", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.FG)
    bar = formula_HC()[2][1].get_center()
    return lab.move_to([PROBE_X, bar[1], 0.0], aligned_edge=LEFT)


def disclosure_tag():
    """The zero beat's on-screen disclosure (CLAUDE.md data rules), under the probe label."""
    lines = VGroup(*[Text(t, font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED) for t in ("interpolated:", "zero moved by hand")])
    lines.arrange(DOWN, aligned_edge=LEFT, buff=0.06)
    return lines.next_to(probe_label(), DOWN, aligned_edge=LEFT, buff=0.16)


READOUT_X = -6.3  # left edge of the R / zeta readout stack (bottom-left, above the band)
READOUT_ROWS = (-1.75, -2.2)


def readouts(get_R, opacity=None):
    """'R = 120.0 Omega' and 'zeta = 0.600', left-aligned under each other (S6 onward)."""
    from rubber_sheet.panels import Readout

    return VGroup(
        Readout("<i>R</i> =", get_R, "{:.1f}", unit="Ω", n_slots=5, align="left", opacity=opacity).place([READOUT_X, READOUT_ROWS[0], 0]),
        Readout("<i>ζ</i> =", lambda: ph.zeta(get_R()), "{:.3f}", n_slots=5, align="left", opacity=opacity).place([READOUT_X, READOUT_ROWS[1], 0]),
    )


def peak_readout(get_R, bode, opacity=None):
    """'peak 28.0 dB' in SIGNAL gold on the Bode panel's title row, right-aligned to its box:
    the resonance peak of |H_C(jw)| from physics.resonance (0 dB when there is none)."""
    from rubber_sheet.panels import Readout

    r = Readout("peak", lambda: ph.to_db(ph.resonance(get_R())[1]), "{:.1f}", unit="dB", size=th.SIZE_SMALL, color=th.SIGNAL,
                n_slots=5, opacity=opacity)
    return r.place([0, bode.title.get_center()[1], 0]).align_right(bode.box[1])


def pole_values_krad(R=ph.R_START):
    p = ph.poles(R)[1] / 1e3  # upper pole, krad/s
    return p.real, p.imag


def roots_block(anchor):
    """'LCs^2+RCs+1 = 0  =>  s = -6 +/- j8 krad/s' with numbers from physics."""
    re, im = pole_values_krad()
    eq = MathTex(r"LCs^2+RCs+1=0", font_size=th.SIZE_MATH * 0.8, color=th.FG)
    sol = MathTex(r"\Rightarrow\ s", "=", rf"{re:g} \pm j{im:g}", font_size=th.SIZE_MATH * 0.8, color=th.FG)
    sol[2].set_color(th.POLE)
    # units are set in Inter everywhere (axis unit, panels), so not in LaTeX \text here
    unit = Text("krad/s", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.FG)
    unit.next_to(sol, RIGHT, buff=0.14).align_to(sol[0], DOWN)
    block = VGroup(eq, VGroup(sol, unit)).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    block.next_to(anchor, DOWN, aligned_edge=LEFT, buff=0.3)
    return block


def height_tag(anchor):
    tag = MarkupText("height = 20 log<sub>10</sub>|<i>H</i>|  (dB)", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.MUTED)
    clip = f"floor {ph.DB_FLOOR:g} dB · soft ceiling {ph.DB_CEIL:+g} dB"
    floor = Text(clip.replace("-", "−"), font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
    block = VGroup(tag, floor).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
    block.next_to(anchor, DOWN, aligned_edge=LEFT, buff=0.3)
    return block


class SheetAssembly:
    """R tracker -> poles -> sheet, pole crosses, tent poles. Display-only: lift, opacity.

    zero: optional callable -> the hand-moved zero in rad/s (-inf = none) for the S5 beat; the
    sheet is then H_z (physics.mag_zero) and the zero is a mesh knot like the poles."""

    def __init__(self, R=ph.R_START, lift=0.0, opacity=0.0, mag=None, features=None, preset=None, zero=None):
        self.R = ValueTracker(R)
        self.lift = ValueTracker(lift)  # display-only reveal of heights
        self.opacity = ValueTracker(opacity)  # display-only sheet fade
        self.zero = zero
        self.mag = mag or self._mag
        self.features = features or self._pole_features
        self.surface = LiveSurface(self.mag, self.features, self.lift, self.opacity, preset=preset)
        self.crosses = VGroup(*[world.Cross(lambda k=k: self.pole(k), th.POLE) for k in (0, 1)])
        self.tents = VGroup(
            *[
                TentPole(
                    lambda k=k: tuple(world.xyz(self.pole(k).real, self.pole(k).imag)[:2]),
                    lambda: (Z_CEIL + 0.3) * self.lift.get_value(),
                    lambda: Z_CEIL * self.lift.get_value(),
                    th.POLE,
                )
                for k in (0, 1)
            ]
        )

    def pole(self, k):
        """k = 0 lower, 1 upper; complex, krad/s."""
        return ph.poles(self.R.get_value())[k] / 1e3

    def _mag(self, S):
        if self.zero is None:
            return ph.mag_C(S, self.R.get_value())
        return ph.mag_zero(S, self.R.get_value(), self.zero())

    def zero_krad(self):
        """The zero in krad/s if it lies on the s-plane domain, else None."""
        z = -np.inf if self.zero is None else self.zero() / 1e3
        return float(z) if np.isfinite(z) and z >= th.SIGMA_RANGE[0] else None

    def _pole_features(self):
        p = self.pole(1)
        f = dict(sigma=[p.real], omega=[abs(p.imag)])
        z = self.zero_krad()
        if z is not None:  # zero first: if both want the same sigma node, the pole keeps it
            f["sigma"].insert(0, z)
            f["omega"].append(0.0)
        return f

    def pole_top(self, k):
        p = self.pole(k)
        return world.xyz(p.real, p.imag, (Z_CEIL + 0.3) * self.lift.get_value())

