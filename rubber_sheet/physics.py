"""Numerical core: series RLC, output across C (or R), poles, |H(s)|, impulse response.

Pure numpy, no manim import. Every number drawn on screen comes from here.
Units are SI (rad/s, seconds); scenes convert to krad/s and ms for display.
"""

import numpy as np

# Components. L = 10 mH, C = 1 uF  ->  w0 = 1e4 rad/s, R_crit = 2*sqrt(L/C) = 200 ohm.
L = 10e-3
C = 1e-6
OMEGA0 = 1.0 / np.sqrt(L * C)
R_CRIT = 2.0 * np.sqrt(L / C)

R_START = 120.0  # zeta = 0.6, poles at -6000 +/- 8000j
R_SWEEP_END = 4.0  # zeta = 0.02, resonance peak ~ 27.96 dB

# Display mapping for the sheet height (dB -> scene z).
DB_FLOOR = -40.0
DB_KNEE = 30.0
DB_CEIL = 40.0
Z_PER_DB = 0.05


def zeta(R):
    return 0.5 * R * np.sqrt(C / L)


def denominator_coeffs(R):
    return np.array([L * C, R * C, 1.0])


def poles(R):
    """Roots of LC s^2 + RC s + 1, sorted by (imag, real)."""
    p = np.roots(denominator_coeffs(R))
    return np.array(sorted(p.astype(complex), key=lambda z: (z.imag, z.real)))


def denominator(s, R):
    s = np.asarray(s, dtype=complex)
    return L * C * s * s + R * C * s + 1.0


def mag_C(s, R):
    """|H_C(s)| for H_C = 1/(LCs^2+RCs+1); exact poles give +inf (no NaN)."""
    with np.errstate(divide="ignore"):
        return 1.0 / np.abs(denominator(s, R))


def mag_R(s, R):
    """|H_R(s)| for H_R = RCs/(LCs^2+RCs+1): output across the resistor."""
    s = np.asarray(s, dtype=complex)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.abs(R * C * s) / np.abs(denominator(s, R))


def mag_zero(s, R, z):
    """|H_z(s)| = |H_C(s) * (1 - s/z) / (1 - 1/(RC z))| = |H_C * RC (z - s) / (RC z - 1)|.

    A real transfer function with one zero at s = z (z <= 0). z = -inf gives H_C
    exactly; z = 0 gives RC s * H_C = H_R exactly. Used only for the zero beat.
    """
    if np.isneginf(z):
        return mag_C(s, R)
    s = np.asarray(s, dtype=complex)
    rc = R * C
    if rc == 0.0:  # H_R = RCs * H_C is identically 0 when R = 0 (avoid 0 * inf at the poles)
        return np.zeros(s.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.abs(rc * (z - s)) / (np.abs(rc * z - 1.0) * np.abs(denominator(s, R)))


ZERO_EDGE = -15e3  # rad/s: the left edge of the s-plane domain (sigma = -15 krad/s)


def zero_slide(u):
    """Hand-moved zero position (rad/s) for the S5 beat parameter u in [0, 2].

    u in [0, 1]: z = ZERO_EDGE / u, i.e. b = -1/z grows linearly from 0 (z = -inf: exactly H_C)
    to the domain edge, so the zero arrives from -inf. u in [1, 2]: z moves linearly from the edge
    to 0 (exactly H_R at u = 2). Not a physical parameter: disclosed on screen as hand-moved.
    """
    u = float(u)
    if u <= 0.0:
        return -np.inf
    if u <= 1.0:
        return ZERO_EDGE / u
    return ZERO_EDGE * (2.0 - min(u, 2.0))


def to_db(mag):
    with np.errstate(divide="ignore"):
        return 20.0 * np.log10(mag)


def zmap(db):
    """dB -> sheet height in scene units.

    Hard floor at DB_FLOOR, identity up to DB_KNEE, then a C1-smooth tanh roll-off
    towards DB_CEIL. Monotone. +inf -> ceiling, -inf -> floor.
    """
    db = np.clip(np.asarray(db, dtype=float), DB_FLOOR, np.inf)
    span = DB_CEIL - DB_KNEE
    over = np.where(db > DB_KNEE, db - DB_KNEE, 0.0)
    shaped = np.where(db > DB_KNEE, DB_KNEE + span * np.tanh(over / span), db)
    return (shaped - DB_FLOOR) * Z_PER_DB


def impulse_response(t, R):
    """Inverse Laplace transform of H_C: h(t) for t >= 0 (units 1/s)."""
    t = np.asarray(t, dtype=float)
    z = zeta(R)
    w0 = OMEGA0
    if z < 1.0:
        wd = w0 * np.sqrt(1.0 - z * z)
        return (w0 / np.sqrt(1.0 - z * z)) * np.exp(-z * w0 * t) * np.sin(wd * t)
    if z == 1.0:
        return w0 * w0 * t * np.exp(-w0 * t)
    p1, p2 = poles(R).real
    return w0 * w0 * (np.exp(p1 * t) - np.exp(p2 * t)) / (p1 - p2)


def impulse_envelope(t, R):
    """Decay envelope of h(t) for the underdamped case: (w0/sqrt(1-zeta^2)) e^{Re(p) t}."""
    z = zeta(R)
    return (OMEGA0 / np.sqrt(1.0 - z * z)) * np.exp(-z * OMEGA0 * np.asarray(t, dtype=float))


def resonance(R):
    """(omega_r, peak |H|) of |H_C(jw)|; for zeta >= 1/sqrt(2) the peak is at w = 0."""
    z = zeta(R)
    if z >= 1.0 / np.sqrt(2.0):
        return 0.0, 1.0
    if z == 0.0:
        return OMEGA0, np.inf
    return OMEGA0 * np.sqrt(1.0 - 2.0 * z * z), 1.0 / (2.0 * z * np.sqrt(1.0 - z * z))


def r_of_sweep(u):
    """Sweep parameter u in [0, 1] -> R, logarithmic from R_START to R_SWEEP_END."""
    return R_START * (R_SWEEP_END / R_START) ** np.asarray(u, dtype=float)
