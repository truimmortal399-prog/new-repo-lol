"""Screen-space panels (Bode, impulse response) and live readouts.

Everything here is a persistent mobject mutated in place by updaters, so it stays registered as
fixed-in-frame in a ThreeDScene (camera.fixed_in_frame_mobjects is a family snapshot taken at
registration; objects rebuilt by always_redraw would not be in it).
"""

import numpy as np
from manim import LEFT, RIGHT, UP, Line, MarkupText, Rectangle, Text, ValueTracker, VGroup, VMobject

from rubber_sheet import physics as ph
from rubber_sheet import theme as th

KRAD = 1e3


def _straight_cubics(xy):
    """(n, 2) polyline -> (4(n-1), 3) Bezier points (straight segments)."""
    p = np.column_stack([xy, np.zeros(len(xy))])
    a, b = p[:-1], p[1:]
    return np.stack([a, a + (b - a) / 3, a + 2 * (b - a) / 3, b], axis=1).reshape(-1, 3)


def _dashes(xy, dash, gap):
    """Polyline -> Bezier points of a dashed version (separate subpaths), arc-length based."""
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    period = dash + gap
    starts = np.arange(0.0, s[-1], period)
    out = []
    for s0 in starts:
        s1 = min(s0 + dash, s[-1])
        if s1 - s0 < 1e-4:
            continue
        ss = np.linspace(s0, s1, 4)
        pts = np.column_stack([np.interp(ss, s, xy[:, 0]), np.interp(ss, s, xy[:, 1])])
        out.append(_straight_cubics(pts))
    return np.concatenate(out) if out else np.zeros((4, 3))


class Panel(VGroup):
    """Axes box with data->screen transform.

    opacity: display-only ValueTracker for fading the whole panel. Panels update every frame, and
    FadeIn/FadeOut would suspend that updater, so scenes animate this tracker instead. Each leaf
    keeps its own design opacity times the tracker value (static leaves are re-applied only when
    the tracker changes; data curves and moving ticks every frame).
    """

    def __init__(self, x0, x1, y0, y1, xlim, ylim):
        super().__init__()
        self.box = (x0, x1, y0, y1)
        self.xlim, self.ylim = xlim, ylim
        self.opacity = ValueTracker(1.0)
        self._static = []
        self._applied = None
        self.frame_rect = Rectangle(width=x1 - x0, height=y1 - y0).move_to([(x0 + x1) / 2, (y0 + y1) / 2, 0])
        self.frame_rect.set_stroke(th.FAINT, width=1.5).set_fill(th.BG, opacity=0.85)
        self.add(self.frame_rect)

    def dynamic(self):
        """Roots whose opacity refresh() sets itself every frame."""
        return []

    def freeze_design_opacities(self):
        """Record every static leaf's design opacities (end of a subclass __init__)."""
        # every leaf, including curves that get their points only in refresh() (filtering on
        # has_points() left the impulse curve and envelope out: drawn at full opacity while the
        # panel was still invisible, caught at the S5|S6 cut by tools/check_continuity.py)
        skip = {m for root in self.dynamic() for m in root.get_family()}
        self._static = [(m, m.get_fill_opacity(), m.get_stroke_opacity()) for m in self.get_family() if not m.submobjects and m not in skip]

    def apply_opacity(self):
        op = self.opacity.get_value()
        if op != self._applied:
            for m, f, s in self._static:
                m.set_fill(opacity=f * op, family=False)
                m.set_stroke(opacity=s * op, family=False)
            self._applied = op
        return op

    def to_screen(self, u, v):
        x0, x1, y0, y1 = self.box
        (a, b), (c, d) = self.xlim, self.ylim
        return np.column_stack([x0 + (np.asarray(u) - a) / (b - a) * (x1 - x0), y0 + (np.asarray(v) - c) / (d - c) * (y1 - y0)])

    def from_screen(self, xy):
        x0, x1, y0, y1 = self.box
        (a, b), (c, d) = self.xlim, self.ylim
        xy = np.asarray(xy)
        return np.column_stack([a + (xy[:, 0] - x0) / (x1 - x0) * (b - a), c + (xy[:, 1] - y0) / (y1 - y0) * (d - c)])

    def hline(self, v, color, width=1.0, opacity=1.0):
        p = self.to_screen([self.xlim[0], self.xlim[1]], [v, v])
        return Line([*p[0], 0], [*p[1], 0]).set_stroke(color, width=width, opacity=opacity)

    def vline(self, u, color, width=1.0, opacity=1.0):
        p = self.to_screen([u, u], [self.ylim[0], self.ylim[1]])
        return Line([*p[0], 0], [*p[1], 0]).set_stroke(color, width=width, opacity=opacity)

    def label(self, text, size=th.SIZE_SMALL, color=th.MUTED):
        return Text(text, font=th.FONT_BODY, font_size=size, color=color)


class BodePanel(Panel):
    """|H(jw)| in dB against log10(w), w in rad/s. Curve is exact (physics), clipped to the box.

    mag_fn(w) -> |H(jw)| for real w (rad/s). warp: ValueTracker mu, 0 = linear w in krad/s
    [0, 15], 1 = log10 w in [3, 5] (display-only axis warp; data unchanged).
    """

    LIN = (0.0, 15.0)  # krad/s
    LOG = (3.0, 5.0)  # log10(rad/s)
    DB = (-40.0, 40.0)

    def __init__(self, mag_fn, box, warp=None, samples=None):
        x0, x1, y0, y1 = box
        super().__init__(x0, x1, y0, y1, xlim=(0.0, 1.0), ylim=self.DB)
        self.mag_fn = mag_fn
        self.warp = warp
        n = samples or th.PRESET["curve_samples"]
        self.w = np.unique(np.concatenate([np.logspace(1, 5.3, n), np.linspace(1.0, 2.2e4, n), [ph.OMEGA0]]))
        for db in (-40, -20, 0, 20, 40):
            self.add(self.hline(db, th.FAINT, width=1.0, opacity=0.9 if db == 0 else 0.5))
        self.ticks = VGroup()
        for db, txt in ((40, "+40"), (0, "0"), (-40, "−40")):
            t = self.label(txt).next_to(self.to_screen([0.0], [db])[0].tolist() + [0], LEFT, buff=0.08)
            self.ticks.add(t)
        # Frequency ticks: decades 1/10/100 krad/s stay (they slide into place during the warp);
        # 5 and 15 krad/s label the linear axis only and fade out as the warp proceeds.
        self.decade_w = (1e3, 1e4, 1e5)
        self.lin_w = (5e3, 15e3)
        self.decade_lines = VGroup(*[Line() for _ in self.decade_w])
        self.decade_labels = VGroup(*[self.label(s) for s in ("1", "10", "100")])
        self.lin_lines = VGroup(*[Line() for _ in self.lin_w])
        self.lin_labels = VGroup(*[self.label(s) for s in ("5", "15")])
        self.add(self.ticks, self.decade_lines, self.lin_lines, self.decade_labels, self.lin_labels)
        self.title = MarkupText("|<i>H</i>(<i>jω</i>)|  dB", font=th.FONT_BODY, font_size=th.SIZE_LABEL, color=th.FG)
        self.title.next_to(self.frame_rect, UP, buff=0.08, aligned_edge=LEFT)
        self.xtitle = self.label("ω  (krad/s)", size=th.SIZE_SMALL)
        self.xtitle.move_to([x1, y0 - th.PANEL_AXIS_TITLE_ROW, 0], aligned_edge=RIGHT)
        self.add(self.title, self.xtitle)
        self.curve = VMobject().set_stroke(th.SIGNAL, width=th.SIGNAL_WIDTH)
        self.curve_opacity = ValueTracker(1.0)  # display-only: hidden until the S4 handoff lands
        self.add(self.curve)
        self.freeze_design_opacities()
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def dynamic(self):
        return [self.curve, self.decade_lines, self.decade_labels, self.lin_lines, self.lin_labels]

    def mu(self):
        return 1.0 if self.warp is None else float(self.warp.get_value())

    def x_of_w(self, w, mu=None):
        """rad/s -> normalized panel x in [0, 1] (blend of linear and log axis)."""
        w = np.asarray(w, dtype=float)
        lin = (w / KRAD - self.LIN[0]) / (self.LIN[1] - self.LIN[0])
        with np.errstate(divide="ignore"):
            log = (np.log10(np.maximum(w, 1e-9)) - self.LOG[0]) / (self.LOG[1] - self.LOG[0])
        m = self.mu() if mu is None else mu
        return (1 - m) * lin + m * log

    def screen_curve(self, w, mu):
        """Screen points (n, 2) of the curve at the given frequencies (rad/s) for warp mu, without
        clipping to the box in x (used to build the S4 handoff target)."""
        db = np.clip(ph.to_db(self.mag_fn(np.asarray(w, dtype=float))), *self.DB)
        return self.to_screen(self.x_of_w(w, mu), db)

    def data(self):
        """Visible samples: (w rad/s, dB exact) inside the box."""
        db = ph.to_db(self.mag_fn(self.w))
        x = self.x_of_w(self.w)
        keep = (x >= 0.0) & (x <= 1.0)
        return self.w[keep], db[keep], x[keep]

    def refresh(self):
        op = self.apply_opacity()
        w, db, x = self.data()
        y = np.clip(db, self.DB[0], self.DB[1])
        self.curve.points = _straight_cubics(self.to_screen(x, y))
        self.curve.set_stroke(opacity=op * self.curve_opacity.get_value(), family=False)
        mu = self.mu()
        ticks = [(l, t, wd, 1.0) for l, t, wd in zip(self.decade_lines, self.decade_labels, self.decade_w)]
        ticks += [(l, t, wd, 1.0 - mu) for l, t, wd in zip(self.lin_lines, self.lin_labels, self.lin_w)]
        for line, lab, wd, fade in ticks:
            xd = float(self.x_of_w(wd))
            vis = fade * op if 0.0 <= xd <= 1.0 + 1e-9 else 0.0
            p = self.to_screen([xd, xd], [self.DB[0], self.DB[1]])
            line.points = _straight_cubics(p)
            line.set_stroke(th.FAINT, width=1.0, opacity=0.5 * vis)
            lab.move_to([p[0, 0], self.box[2] - th.PANEL_TICK_ROW, 0])
            lab.set_opacity(vis)
        return self


class ImpulsePanel(Panel):
    """h(t)/w0 for t in [0, 8] ms with the decay envelope (dashed, POLE color)."""

    T_MS = (0.0, 8.0)
    Y = (-1.3, 1.3)

    def __init__(self, get_R, box, samples=None):
        x0, x1, y0, y1 = box
        super().__init__(x0, x1, y0, y1, xlim=self.T_MS, ylim=self.Y)
        self.get_R = get_R
        n = samples or th.PRESET["curve_samples"]
        self.t = np.linspace(0.0, self.T_MS[1] * 1e-3, n)
        self.add(self.hline(0.0, th.FAINT, width=1.0, opacity=0.9))
        for ms in (2, 4, 6):
            self.add(self.vline(ms, th.FAINT, width=1.0, opacity=0.4))
        self.tick_labels = VGroup(*[self.label(str(ms)).move_to([self.to_screen([ms], [0])[0, 0], y0 - th.PANEL_TICK_ROW, 0]) for ms in (0, 2, 4, 6, 8)])
        self.title = self.label("impulse response  h(t)", size=th.SIZE_LABEL, color=th.FG).next_to(self.frame_rect, UP, buff=0.08, aligned_edge=LEFT)
        self.xtitle = self.label("t  (ms)", size=th.SIZE_SMALL)
        self.xtitle.move_to([x1, y0 - th.PANEL_AXIS_TITLE_ROW, 0], aligned_edge=RIGHT)
        self.envelope = VMobject().set_stroke(th.POLE, width=2.0, opacity=0.85)
        self.curve = VMobject().set_stroke(th.SIGNAL, width=2.5)
        self.add(self.tick_labels, self.title, self.xtitle, self.envelope, self.curve)
        self.freeze_design_opacities()
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def data(self):
        R = self.get_R()
        h = ph.impulse_response(self.t, R) / ph.OMEGA0
        env = ph.impulse_envelope(self.t, R) / ph.OMEGA0
        return self.t * 1e3, h, env

    def refresh(self):
        self.apply_opacity()  # curve and envelope are plain static-style leaves (points change only)
        t_ms, h, env = self.data()
        self.curve.points = _straight_cubics(self.to_screen(t_ms, np.clip(h, *self.Y)))
        up = self.to_screen(t_ms, np.clip(env, *self.Y))
        dn = self.to_screen(t_ms, np.clip(-env, *self.Y))
        self.envelope.points = np.concatenate([_dashes(up, 0.08, 0.06), _dashes(dn, 0.08, 0.06)])
        return self


class Readout(VGroup):
    """`label value unit` in Inter with fixed-width digit slots (no jitter).

    label_markup: Pango markup, e.g. "<i>R</i> =". value_fn() -> float, formatted with fmt and
    right-aligned in n_slots. The anchor is the left end of the label, vertically centered on
    the digits.
    """

    GLYPHS = "0123456789.−+∞"

    def __init__(self, label_markup, value_fn, fmt, unit="", size=th.SIZE_LABEL, color=th.FG, n_slots=6, align="right", opacity=None):
        super().__init__()
        # opacity: optional display-only ValueTracker (a FadeIn would suspend the value updater)
        self.opacity = opacity
        self._op = None
        # align="right": fixed-width field, decimal point never moves (blank cells when short).
        # align="left": the number starts right after the label (no gap; stacked readouts keep
        # their '=' signs in one column); it shifts only when its digit count changes (e.g. R
        # crossing 100 and 10), never per frame.
        self.align = align
        self.value_fn = value_fn
        self.fmt = fmt
        self.label = MarkupText(label_markup, font=th.FONT_BODY, font_size=size, color=color)
        # One Text for all glyphs keeps their relative baselines; slots copy their points.
        ref = Text(self.GLYPHS, font=th.FONT_BODY, font_size=size, color=color)
        self.glyphs = dict(zip(self.GLYPHS, ref.submobjects))
        zero = self.glyphs["0"]
        self.digit_h = zero.height
        self.zero_bottom = zero.get_bottom()[1]
        self.slot_w = max(self.glyphs[d].width for d in "0123456789") * 1.12  # digits, signs, ∞
        self.dot_w = self.glyphs["."].width * 2.2  # the decimal point gets a narrow cell
        self.label_h0 = self.label.height  # layout scales with the label if the readout is scaled
        self.slots = VGroup(*[VMobject().set_fill(color, opacity=1.0).set_stroke(width=0) for _ in range(n_slots)])
        self.unit = Text(unit, font=th.FONT_BODY, font_size=size, color=color) if unit else VGroup()
        self.add(self.label, self.slots, self.unit)
        self.anchor = None
        self.text = ""
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def align_right(self, x):
        """Shift the whole readout so its right edge (unit, or last digit) sits at x."""
        self.shift(np.array([x - self.get_right()[0], 0.0, 0.0]))
        self.text = ""
        self.refresh()
        return self

    def field_width(self):
        """Width of the number field: all cells digit-wide except one decimal point cell."""
        has_dot = "." in self.fmt.format(1.0)
        return (len(self.slots) - has_dot) * self.slot_w + has_dot * self.dot_w

    def place(self, point):
        """Put the left end of the label at `point` (digits are vertically centred on it)."""
        self.label.move_to(np.array(point, dtype=float), aligned_edge=LEFT)
        self.text = ""
        self.refresh()
        return self

    def format(self, value):
        if not np.isfinite(value):
            return "∞"
        return self.fmt.format(value).replace("-", "−")

    def refresh(self):
        if self.opacity is not None and self.opacity.get_value() != self._op:
            self._op = self.opacity.get_value()
            self.label.set_opacity(self._op)
            self.unit.set_opacity(self._op)
            self.slots.set_fill(opacity=self._op)
        raw = self.format(self.value_fn())
        if len(raw) > len(self.slots):
            raise ValueError(f"readout overflow: {raw!r} needs more than {len(self.slots)} slots")
        text = raw.rjust(len(self.slots)) if self.align == "right" else raw.ljust(len(self.slots))
        # Layout follows the label wherever it is now (the readout may have been moved).
        k = self.label.height / self.label_h0
        anchor = (self.label.get_left()[0], self.label.get_center()[1], k)
        if text == self.text and anchor == self.anchor:
            return self
        self.text, self.anchor = text, anchor
        baseline = anchor[1] - k * self.digit_h / 2
        # Lay out from a fixed right edge, so the decimal point never moves as values change.
        widths = [k * (self.dot_w if ch == "." else self.slot_w) for ch in text]
        field_left = self.label.get_right()[0] + k * 0.12
        if self.align == "right":
            right = field_left + k * self.field_width()
        else:
            right = field_left + sum(w for w, ch in zip(widths, text) if ch.strip())
        x = right - sum(widths) if self.align == "right" else field_left
        for slot, ch, w in zip(self.slots, text, widths):
            g = self.glyphs.get(ch)
            if g is None:
                slot.points = np.zeros((0, 3))
            else:
                # glyph drawn at scale k, horizontally centred in its cell, on the shared baseline
                local = (g.points - np.array([g.get_center()[0], self.zero_bottom, 0.0])) * k
                slot.points = local + np.array([x + w / 2, baseline, 0.0])
            x += w
        if len(self.unit):
            self.unit.move_to([right + k * 0.08, anchor[1], 0.0], aligned_edge=LEFT)
        return self
