"""Camera states, the planned camera moves, and the trapezoidal-velocity rate function.

Angles are in degrees here; scenes convert with `* DEGREES`. Every move's start state is the
previous move's end state, and the peak combined angular speed sqrt(phi'^2 + theta'^2) is
derived from those states (tests/test_camera.py), never from a hand-written table.
"""

import math
from dataclasses import dataclass

RAMP = 0.8  # seconds of acceleration / deceleration at each end of a move
MAX_DEG_PER_S = 15.0
MIN_MOVE = 1.2


@dataclass(frozen=True)
class CamState:
    phi: float
    theta: float
    zoom: float = 1.0
    frame_center: tuple = (0.0, 0.0, 0.0)


TOP = CamState(phi=0.0, theta=-90.0)  # looks exactly like a 2D scene
S3_TILTED = CamState(phi=58.0, theta=-90.0)
S3_END = CamState(phi=58.0, theta=-50.0)
CUT = CamState(phi=82.0, theta=0.0)  # looking along -sigma: the jw cut reads as a 2D profile
ANALYSIS = CamState(phi=60.0, theta=-40.0, frame_center=(1.9, 0.0, 0.0))
HERO = CamState(phi=62.0, theta=-60.0)


@dataclass(frozen=True)
class Move:
    name: str
    scene: str
    t0: float  # film time
    t1: float
    start: CamState
    end: CamState

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
    Move("S3 tilt", "S3", 15.6, 20.6, TOP, S3_TILTED),
    Move("S3 theta swing", "S3", 21.0, 24.6, S3_TILTED, S3_END),
    Move("S4 swing to CUT", "S4", 25.4, 30.2, S3_END, CUT),
    Move("S5 return to ANALYSIS", "S5", 35.72, 39.92, CUT, ANALYSIS),
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
        if t <= a:
            return vmax * t * t / (2.0 * a)
        if t >= 1.0 - a:
            return 1.0 - vmax * (1.0 - t) ** 2 / (2.0 * a)
        return vmax * (t - a / 2.0)

    return rate


def move_kwargs(move):
    """Keyword arguments for ThreeDScene.move_camera for a planned move."""
    from manim import DEGREES

    return dict(
        phi=move.end.phi * DEGREES,
        theta=move.end.theta * DEGREES,
        zoom=move.end.zoom,
        frame_center=list(move.end.frame_center),
        run_time=move.run_time,
        rate_func=trapezoid(move.run_time),
    )


def moves_in(scene):
    return [m for m in MOVES if m.scene == scene]
