"""Camera moves: continuity of states, duration, and peak combined angular speed <= 15 deg/s.

Expected peaks are computed from each move's actual start/end states and checked against a
600-sample numerical derivative of the rate function actually used.
"""

import math

import numpy as np
import pytest

from rubber_sheet import camera as cam
from rubber_sheet import script as sc


def sampled_peak_speed(move, samples=600):
    rate = cam.trapezoid(move.run_time)
    t = np.linspace(0.0, 1.0, samples + 1)
    pos = np.array([rate(x) for x in t])
    v = np.diff(pos) / np.diff(t) / move.run_time  # normalized position per second
    return move.angle * v.max()


@pytest.mark.parametrize("move", cam.MOVES, ids=lambda m: m.name)
def test_peak_speed_within_cap(move):
    analytic = move.peak_speed
    numeric = sampled_peak_speed(move)
    assert numeric == pytest.approx(analytic, rel=0.01)
    assert numeric <= cam.MAX_DEG_PER_S, (move.name, numeric)


def test_chain_is_continuous():
    for prev, nxt in zip(cam.MOVES, cam.MOVES[1:]):
        assert nxt.start == prev.end, (prev.name, nxt.name)
        assert nxt.t0 >= prev.t1


def test_s3_ends_at_phi_58_and_s4_swing_value():
    assert cam.MOVES[1].end.phi == 58.0
    s4 = next(m for m in cam.MOVES if m.name == "S4 swing to CUT")
    assert s4.start.phi == 58.0
    expected = math.hypot(82.0 - 58.0, 0.0 - (-50.0)) / (s4.run_time - cam.RAMP)
    assert s4.peak_speed == pytest.approx(expected)
    assert round(s4.peak_speed, 2) == 13.87


@pytest.mark.parametrize("move", cam.MOVES, ids=lambda m: m.name)
def test_move_duration_and_scene(move):
    assert move.run_time >= cam.MIN_MOVE
    start, end = sc.SCENES[move.scene]
    assert start <= move.t0 < move.t1 <= end


@pytest.mark.parametrize("run_time", [1.2, 2.0, 4.2, 5.0, 11.5])
def test_trapezoid_rate_function(run_time):
    rate = cam.trapezoid(run_time)
    t = np.linspace(0, 1, 2001)
    pos = np.array([rate(x) for x in t])
    assert pos[0] == 0.0 and pos[-1] == pytest.approx(1.0)
    assert np.all(np.diff(pos) >= -1e-12)
    v = np.diff(pos) / np.diff(t)
    assert v[0] < 0.05 * v.max() and v[-1] < 0.05 * v.max()  # starts and ends at rest
