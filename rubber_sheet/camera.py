"""Camera states, the planned camera moves, and the trapezoidal-velocity rate function.

Angles are in degrees here; scenes convert with `* DEGREES`. Every move's start state is the
previous move's end state, and the peak combined angular speed sqrt(phi'^2 + theta'^2) is
derived from those states (tests/test_camera.py), never from a hand-written table.
"""

import math
from dataclasses import dataclass

import numpy as np

RAMP = 0.8  # seconds of acceleration / deceleration at each end of a move
MAX_DEG_PER_S = 15.0
MIN_MOVE = 1.2


@dataclass(frozen=True)
class CamState:
    """phi/theta in degrees; pivot = 3D rotation center (world); pan = screen offset of the
    projected 3D content (frame units). See rubber_sheet/rig.py."""

    phi: float
    theta: float
    zoom: float = 1.0
    pivot: tuple = (0.0, 0.0, 0.0)
    pan: tuple = (0.0, 0.0)


SHEET_CENTER = (-1.25, 0.0, 0.0)  # middle of the s-plane domain (sigma -15..5 krad/s -> x)
SHEET_PIVOT = (-1.25, 0.0, 1.6)  # middle of the sheet volume
# zoom/pan values are chosen against tests/test_composition.py (band, title-safe, panel column, HUD)

TOP = CamState(phi=0.0, theta=-90.0, zoom=0.82, pivot=SHEET_CENTER, pan=(1.1, 0.475))  # looks 2D
S3_END = CamState(phi=58.0, theta=-50.0, zoom=0.74, pivot=SHEET_PIVOT, pan=(0.7, 0.76))
CUT = CamState(phi=82.0, theta=0.0, zoom=0.78, pivot=SHEET_PIVOT, pan=(-3.0, -0.88))  # jw cut reads as a 2D profile
ANALYSIS = CamState(phi=64.0, theta=-40.0, zoom=0.64, pivot=SHEET_PIVOT, pan=(-2.0, -0.1))
ANALYSIS_DRIFT = CamState(phi=64.0, theta=-48.0, zoom=0.63, pivot=SHEET_PIVOT, pan=(-1.8, 0.0))  # end of the S6 sweep
HERO = CamState(phi=62.0, theta=-60.0, zoom=0.76, pivot=SHEET_PIVOT, pan=(0.0, 0.8))


@dataclass(frozen=True)
class Frame:
    """Framing keyframe inside a move: zoom/pivot/pan at angular progress s (0 < s < 1)."""

    s: float
    zoom: float
    pivot: tuple
    pan: tuple


@dataclass(frozen=True)
class Move:
    """Angles go linearly in the move's progress s = trapezoid(alpha); framing (zoom, pivot, pan)
    follows a monotone cubic through start, the `via` keyframes and end (state_at)."""

    name: str
    scene: str
    t0: float  # film time
    t1: float
    start: CamState
    end: CamState
    via: tuple = ()

    @property
    def run_time(self):
        return self.t1 - self.t0

    @property
    def angle(self):
        """Combined angular distance sqrt(dphi^2 + dtheta^2) in degrees."""
        return math.hypot(self.end.phi - self.start.phi, self.end.theta - self.start.theta)

    @property
    def peak_speed(self):
        """Peak of sqrt(phi'^2 + theta'^2) under the trapezoidal profile, deg/s."""
        return self.angle / (self.run_time - ramp_seconds(self.run_time))


# Chained in film order; scenes S1 (ambient orbit) and S2 (2D) have no moves in this chain.
MOVES = [
    # One combined move: theta starts turning with the tilt, so the two poles are already
    # separated on screen when the sheet lifts at 18.0 (two tilts in sequence lined them up).
    Move(
        "S3 tilt and swing", "S3", 15.0, 21.0, TOP, S3_END,
        # keeps the floor's near corner out of the caption band mid-tilt without shrinking the
        # zoom (found by tools/frame_search.py against layout.frame_violations)
        via=(Frame(s=0.5, zoom=0.74, pivot=(-1.25, 0.0, 0.8), pan=(0.9, 0.775)),),
    ),
    Move(
        "S4 swing to CUT", "S4", 25.4, 30.2, S3_END, CUT,
        # the sheet's far end sweeps through the top-left mid-swing: these keep it clear of the
        # formula and height tag (the tag stays put) with a smooth pan (tools/frame_search.py)
        # (re-searched at Gate 4 with the gold plane and the tent-pole tops in the rules)
        via=(
            Frame(s=0.45, zoom=0.68, pivot=(-1.25, 0.0, 1.6), pan=(-0.425, -0.278)),
            Frame(s=0.7, zoom=0.68, pivot=(-1.25, 0.0, 1.6), pan=(-1.52, -0.678)),
        ),
    ),
    Move(
        "S5 return to ANALYSIS", "S5", 35.72, 39.92, CUT, ANALYSIS,
        # keeps the sheet (incl. the zero beat's raised far corners and the R = 120 tent-pole tops)
        # clear of the height tag and the floor out of the band (tools/frame_search.py, Gate 4)
        via=(
            Frame(s=0.45, zoom=0.70, pivot=(-1.25, 0.0, 1.6), pan=(-2.35, -0.529)),
            Frame(s=0.75, zoom=0.66, pivot=(-1.25, 0.0, 1.6), pan=(-2.05, -0.295)),
        ),
    ),
    # slow theta drift during the R sweep: the poles' sigma motion turns a little more across the
    # screen (0.75 deg/s peak)
    Move("S6 drift", "S6", 49.5, 61.0, ANALYSIS, ANALYSIS_DRIFT),
]


def ramp_seconds(run_time, ramp=RAMP):
    return min(ramp, run_time / 2.0)


def trapezoid(run_time, ramp=RAMP):
    """Rate function with constant acceleration for `ramp` s, cruise, constant deceleration.

    Position is C1 (velocity continuous, starts and ends at rest). Peak normalized velocity is
    1 / (1 - a) with a = ramp / run_time.
    """
    a = ramp_seconds(run_time, ramp) / run_time
    vmax = 1.0 / (1.0 - a)

    def rate(t):
        t = min(max(t, 0.0), 1.0)  # manim does not clamp alpha for custom rate functions
        if t <= a:
            return vmax * t * t / (2.0 * a)
        if t >= 1.0 - a:
            return 1.0 - vmax * (1.0 - t) ** 2 / (2.0 * a)
        return vmax * (t - a / 2.0)

    return rate


def moves_in(scene):
    return [m for m in MOVES if m.scene == scene]


def _framing_vector(state):
    return np.array([state.zoom, *state.pivot, *state.pan], dtype=float)


def state_at(move, s):
    """CamState at angular progress s in [0, 1] (used by the renderer and by the tests)."""
    s = min(max(float(s), 0.0), 1.0)
    a, b = move.start, move.end
    if move.via:
        knots = [0.0] + [f.s for f in move.via] + [1.0]
        vals = np.array([_framing_vector(a)] + [_framing_vector(CamState(0, 0, f.zoom, f.pivot, f.pan)) for f in move.via] + [_framing_vector(b)])
        from scipy.interpolate import PchipInterpolator  # monotone cubic: no overshoot, C1

        v = PchipInterpolator(knots, vals, axis=0)(s)
    else:
        v = (1 - s) * _framing_vector(a) + s * _framing_vector(b)
    return CamState(
        phi=a.phi + s * (b.phi - a.phi),
        theta=a.theta + s * (b.theta - a.theta),
        zoom=float(v[0]),
        pivot=tuple(float(x) for x in v[1:4]),
        pan=tuple(float(x) for x in v[4:6]),
    )


def state_at_time(move, t):
    """CamState at film time t during the move (trapezoidal progress)."""
    return state_at(move, trapezoid(move.run_time)((t - move.t0) / move.run_time))
