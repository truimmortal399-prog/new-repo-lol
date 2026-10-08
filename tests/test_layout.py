"""Fixed-in-frame layout: panel texts never collide, everything stays title-safe and out of the
caption band; readouts follow their label and refuse to overflow."""

import itertools

import pytest
from manim import UP, Text, ValueTracker

from rubber_sheet import captions
from rubber_sheet import common
from rubber_sheet import physics as ph
from rubber_sheet import theme as th
from rubber_sheet.panels import BodePanel, ImpulsePanel, Readout


def texts(mob):
    return [m for m in mob.get_family() if isinstance(m, Text)]


def bbox(m):
    return captions._bbox_fixed(m)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.fixture(scope="module")
def panels():
    R = 4.0
    bode = BodePanel(lambda w: ph.mag_C(1j * w, R), th.BODE_BOX, warp=ValueTracker(1.0))
    imp = ImpulsePanel(lambda: R, th.IMPULSE_BOX)
    return bode, imp


def test_panel_texts_pairwise_disjoint(panels):
    items = [t for p in panels for t in texts(p) if t.get_fill_opacity() > 0]
    for a, b in itertools.combinations(items, 2):
        assert not overlap(bbox(a), bbox(b)), (a.text, b.text)


@pytest.mark.parametrize("mu", [0.0, 0.5, 1.0])
def test_panels_inside_safe_area_and_above_band(mu):
    bode = BodePanel(lambda w: ph.mag_C(1j * w, 4.0), th.BODE_BOX, warp=ValueTracker(mu))
    for p in (bode, ImpulsePanel(lambda: 4.0, th.IMPULSE_BOX)):
        for t in texts(p) + [p.frame_rect]:
            if t.get_fill_opacity() == 0 and t is not p.frame_rect:
                continue
            x0, y0, x1, y1 = bbox(t)
            assert -th.SAFE_X <= x0 and x1 <= th.SAFE_X and y1 <= th.SAFE_Y, getattr(t, "text", "frame")
            assert y0 >= th.CAPTION_BAND["y1"], getattr(t, "text", "frame")


def test_hud_blocks_title_safe():
    f = common.formula_HC()
    for block in (f, common.roots_block(f), common.height_tag(f)):
        x0, y0, x1, y1 = bbox(block)
        assert -th.SAFE_X <= x0 and x1 <= th.SAFE_X and y1 <= th.SAFE_Y


def test_readout_follows_label_after_move():
    v = ValueTracker(120.0)
    r = Readout("<i>R</i> =", v.get_value, "{:.1f}", unit="Ω", n_slots=5).place([-6.3, -1.75, 0])
    r.shift(UP)
    v.set_value(57.3)
    r.update()
    assert abs(r.label.get_center()[1] - (-0.75)) < 1e-6
    baseline = r.label.get_center()[1] - r.digit_h / 2
    digit_bottoms = [s.get_bottom()[1] for s, ch in zip(r.slots, r.text) if ch.isdigit()]
    assert digit_bottoms and max(abs(b - baseline) for b in digit_bottoms) < 0.02
    assert abs(r.unit.get_center()[1] - r.label.get_center()[1]) < 0.05


def test_readout_overflow_raises():
    v = ValueTracker(1.0)
    r = Readout("<i>R</i> =", v.get_value, "{:.1f}", n_slots=4)
    v.set_value(12345.6)
    with pytest.raises(ValueError):
        r.update()


def test_readout_keeps_scale_after_value_change():
    v = ValueTracker(120.0)
    r = Readout("<i>R</i> =", v.get_value, "{:.1f}", unit="Ω", n_slots=5).place([0, 0, 0])
    h0 = max(s.height for s in r.slots if s.has_points())
    r.scale(0.5)
    v.set_value(57.3)
    r.update()
    h1 = max(s.height for s in r.slots if s.has_points())
    assert abs(h1 / h0 - 0.5) < 0.02


def test_left_aligned_readout_has_no_gap_and_moves_only_on_digit_count_change():
    """align='left': the number starts right after the label (no blank cells); within a digit
    count the decimal point stays put, and the label never moves."""
    v = ValueTracker(120.0)
    r = Readout("<i>R</i> =", v.get_value, "{:.1f}", unit="Ω", n_slots=5, align="left").place([-6.3, -1.75, 0])
    label_x = r.label.get_left()[0]

    def dot_x():
        return [s.get_center()[0] for s, ch in zip(r.slots, r.text) if ch == "."][0]

    def gap():
        first = next(s for s, ch in zip(r.slots, r.text) if ch.strip())
        return first.get_left()[0] - r.label.get_right()[0]

    dots = {}
    for val in (120.0, 110.4, 99.9, 57.3, 9.9, 4.0):
        v.set_value(val)
        r.update()
        assert 0.0 < gap() < 0.2 and abs(r.label.get_left()[0] - label_x) < 1e-9
        dots.setdefault(len(f"{val:.1f}"), set()).add(round(dot_x(), 9))
    assert all(len(xs) == 1 for xs in dots.values())  # fixed within each digit count
