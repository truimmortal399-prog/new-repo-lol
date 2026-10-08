"""Framing along EVERY planned camera move and hold, at R = 120, 4, 0 (and the hand-moved zero
during S5): projected floor/sheet/labels stay out of the caption band, inside title-safe, left of
the panel column once panels exist, clear of the formula/roots/height-tag blocks, and the two
tent-pole apexes are >= 0.8 frame units apart on screen from the lift (18.0 s) on.
The rule set itself lives in rubber_sheet.layout.frame_violations."""

import numpy as np
import pytest

from rubber_sheet import beats as bt
from rubber_sheet import camera as cam
from rubber_sheet import layout as L
from rubber_sheet import physics as ph

RS = [ph.R_START, ph.R_SWEEP_END, 0.0]
HOLDS = [("TOP", 11.6, 15.0, cam.TOP), ("S3_END", 21.0, 25.4, cam.S3_END), ("CUT", 30.2, 35.72, cam.CUT), ("ANALYSIS", 39.92, 49.5, cam.ANALYSIS),
         ("ANALYSIS_DRIFT", 61.0, 61.0, cam.ANALYSIS_DRIFT)]  # S7 extends the last hold


def zeros_at(t):
    """The hand-moved zero as scheduled (S5), plus no zero: the zero may be faded out early."""
    z = L.zero_at(t)
    return [None] if z is None else [None, z]


def violations(state, t):
    out = []
    for R in RS:
        # the zero beat happens at R = 120 (S5); other R values are checked without the zero
        for z in zeros_at(t) if R == ph.R_START else [None]:
            out += [f"t={t:.2f} R={R} zero={z}: {v}" for v in L.frame_violations(state, t, R, z)]
    return out


@pytest.mark.parametrize("move", cam.MOVES, ids=lambda m: m.name)
def test_every_move_is_framed(move):
    bad = []
    for t, state in L.states_along(move, 120):  # dense: grazing hits between samples were real (Gate 4)
        bad += violations(state, t)
    assert not bad, bad[:5]


@pytest.mark.parametrize("name,t0,t1,state", HOLDS, ids=[h[0] for h in HOLDS])
def test_every_hold_is_framed(name, t0, t1, state):
    bad = []
    for t in np.linspace(t0, t1, 8):
        bad += violations(state, float(t))
    assert not bad, bad[:5]


def test_apexes_apart_from_the_lift_on():
    """Explicit form of the rule inside frame_violations: >= 0.8 frame units in screen x."""
    samples = [(t, s) for m in cam.MOVES for t, s in L.states_along(m, 40) if t >= bt.APEX_SEPARATION_FROM]
    samples += [(t, s) for _, a, b, s in HOLDS for t in np.linspace(max(a, bt.APEX_SEPARATION_FROM), b, 5) if b >= bt.APEX_SEPARATION_FROM]
    assert samples
    for t, state in samples:
        for R in RS:
            tops = L._project(state, L.pole_tops(R, max(L.lift_at(t), 1e-6)))
            assert abs(tops[0, 0] - tops[1, 0]) >= bt.APEX_MIN_SEPARATION, (t, R)


def test_moves_are_chained_and_cover_the_holds():
    """Holds start where a move ends (or at a scene start) with the same state."""
    ends = {round(m.t1, 2): m.end for m in cam.MOVES}
    for name, t0, _, state in HOLDS[1:]:
        assert ends.get(round(t0, 2)) == state, name
