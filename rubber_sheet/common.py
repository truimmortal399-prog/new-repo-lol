"""Pieces shared by several scenes: the H(s) formula block, the height tag, the sheet assembly."""

from manim import DOWN, LEFT, UL, MarkupText, MathTex, Text, ValueTracker, VGroup

from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet import world
from rubber_sheet.surface import Z_CEIL, LiveSurface, TentPole

FORMULA_ANCHOR_BUFF = 0.45


def formula_HC():
    """H(s) for the capacitor output, at its top-left anchor (S2 end == S3 start)."""
    f = MathTex(r"H(s)", "=", r"\frac{1}{LCs^2+RCs+1}", font_size=th.SIZE_MATH, color=th.FG)
    return f.to_corner(UL, buff=FORMULA_ANCHOR_BUFF)


def pole_values_krad(R=ph.R_START):
    p = ph.poles(R)[1] / 1e3  # upper pole, krad/s
    return p.real, p.imag


def roots_block(anchor):
    """'LCs^2+RCs+1 = 0  =>  s = -6 +/- j8 krad/s' with numbers from physics."""
    re, im = pole_values_krad()
    eq = MathTex(r"LCs^2+RCs+1=0", font_size=th.SIZE_MATH * 0.8, color=th.FG)
    sol = MathTex(
        r"\Rightarrow\ s", "=", rf"{re:g} \pm j{im:g}", r"\ \text{krad/s}",
        font_size=th.SIZE_MATH * 0.8,
        color=th.FG,
    )
    sol[2].set_color(th.POLE)
    block = VGroup(eq, sol).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
    block.next_to(anchor, DOWN, aligned_edge=LEFT, buff=0.3)
    return block


def height_tag(anchor):
    tag = MarkupText("height = 20 log<sub>10</sub>|<i>H</i>|  (dB)", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.MUTED)
    floor = Text(f"floor: {ph.DB_FLOOR:g} dB (clipped)".replace("-", "−"), font=th.FONT_BODY, font_size=th.SIZE_SMALL, color=th.MUTED)
    block = VGroup(tag, floor).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
    block.next_to(anchor, DOWN, aligned_edge=LEFT, buff=0.3)
    return block


class SheetAssembly:
    """R tracker -> poles -> sheet, pole crosses, tent poles. Display-only: lift, opacity."""

    def __init__(self, R=ph.R_START, lift=0.0, opacity=0.0, mag=None, features=None):
        self.R = ValueTracker(R)
        self.lift = ValueTracker(lift)  # display-only reveal of heights
        self.opacity = ValueTracker(opacity)  # display-only sheet fade
        self.mag = mag or (lambda S: ph.mag_C(S, self.R.get_value()))
        self.features = features or self._pole_features
        self.surface = LiveSurface(self.mag, self.features, self.lift, self.opacity)
        self.crosses = VGroup(*[world.Cross(lambda k=k: self.pole(k), th.POLE) for k in (0, 1)])
        self.tents = VGroup(
            *[
                TentPole(lambda k=k: tuple(world.xyz(self.pole(k).real, self.pole(k).imag)[:2]), lambda: (Z_CEIL + 0.3) * self.lift.get_value(), th.POLE)
                for k in (0, 1)
            ]
        )

    def pole(self, k):
        """k = 0 lower, 1 upper; complex, krad/s."""
        return ph.poles(self.R.get_value())[k] / 1e3

    def _pole_features(self):
        p = self.pole(1)
        return dict(sigma=[p.real], omega=[abs(p.imag)])

    def pole_top(self, k):
        p = self.pole(k)
        return world.xyz(p.real, p.imag, (Z_CEIL + 0.3) * self.lift.get_value())

