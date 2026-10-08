"""Cross-check rubber_sheet.physics against scipy.signal (independent reference)."""

import numpy as np
import pytest
from scipy import signal

from rubber_sheet import physics as ph

R_VALUES = [120.0, 40.0, 4.0]


def tf_C(R):
    return signal.TransferFunction([1.0], ph.denominator_coeffs(R))


def sort_poles(p):
    return np.array(sorted(np.asarray(p, dtype=complex), key=lambda z: (z.imag, z.real)))


@pytest.mark.parametrize("R", R_VALUES)
def test_poles_match_scipy(R):
    ours = ph.poles(R)
    ref = sort_poles(tf_C(R).poles)
    np.testing.assert_allclose(ours, ref, rtol=1e-9)


def test_poles_at_R_zero_on_axis():
    p = ph.poles(0.0)
    ref = sort_poles(tf_C(0.0).poles)
    np.testing.assert_allclose(np.abs(p), np.abs(ref), rtol=1e-9)
    np.testing.assert_allclose(np.abs(p), ph.OMEGA0, rtol=1e-9)
    assert np.all(np.abs(p.real) < 1e-9 * ph.OMEGA0)
    assert np.all(np.abs(ref.real) < 1e-9 * ph.OMEGA0)


def test_start_poles_are_3_4_5():
    np.testing.assert_allclose(ph.poles(ph.R_START), [-6000 - 8000j, -6000 + 8000j], rtol=1e-12)
    assert ph.zeta(ph.R_START) == pytest.approx(0.6)
    assert ph.OMEGA0 == pytest.approx(1e4)
    assert ph.R_CRIT == pytest.approx(200.0)


@pytest.mark.parametrize("R", np.linspace(0.0, 199.0, 12))
def test_underdamped_poles_on_circle(R):
    np.testing.assert_allclose(np.abs(ph.poles(R)), ph.OMEGA0, rtol=1e-9)


@pytest.mark.parametrize("R", R_VALUES)
def test_bode_magnitude_matches_freqresp(R):
    w = np.logspace(2, 6, 2000)
    _, H = signal.freqresp(tf_C(R), w)
    np.testing.assert_allclose(ph.to_db(ph.mag_C(1j * w, R)), 20 * np.log10(np.abs(H)), atol=1e-9)


@pytest.mark.parametrize("R", R_VALUES + [0.0])
def test_impulse_matches_scipy(R):
    t = np.linspace(0.0, 8e-3, 4001)
    _, h_ref = signal.impulse(tf_C(R), T=t)
    err = np.max(np.abs(ph.impulse_response(t, R) - h_ref))
    assert err < 1e-6 * ph.OMEGA0, err


def test_impulse_at_R_zero_never_decays():
    t = np.linspace(0.0, 8e-3, 1001)
    np.testing.assert_allclose(
        ph.impulse_response(t, 0.0), ph.OMEGA0 * np.sin(ph.OMEGA0 * t), atol=1e-9 * ph.OMEGA0
    )


@pytest.mark.parametrize("R", R_VALUES)
def test_envelope_bounds_impulse(R):
    t = np.linspace(0.0, 8e-3, 4001)
    assert np.all(np.abs(ph.impulse_response(t, R)) <= ph.impulse_envelope(t, R) * (1 + 1e-12))


def test_surface_matches_polyval():
    rng = np.random.default_rng(0)
    s = rng.uniform(-15e3, 5e3, 500) + 1j * rng.uniform(-20e3, 20e3, 500)
    for R in R_VALUES:
        ref = 1.0 / np.abs(np.polyval(ph.denominator_coeffs(R), s))
        np.testing.assert_allclose(ph.mag_C(s, R), ref, rtol=1e-12)


def test_exact_pole_is_inf_not_nan():
    m = ph.mag_C(np.array([-6000 + 8000j, -6000 - 8000j]), ph.R_START)
    assert not np.any(np.isnan(m))
    assert np.all(m > 1e10)  # +inf, or within rounding of the pole
    ceiling = (ph.DB_CEIL - ph.DB_FLOOR) * ph.Z_PER_DB
    np.testing.assert_allclose(ph.zmap(ph.to_db(np.array([np.inf, 0.0]))), [ceiling, 0.0])


def test_zmap_properties():
    db = np.linspace(-80, 80, 4001)
    z = ph.zmap(db)
    below = db <= ph.DB_KNEE
    in_lin = below & (db >= ph.DB_FLOOR)
    np.testing.assert_allclose(z[in_lin], (db[in_lin] - ph.DB_FLOOR) * ph.Z_PER_DB, atol=1e-12)
    assert np.all(np.diff(z) >= 0)
    assert z.min() == 0.0
    assert z.max() <= (ph.DB_CEIL - ph.DB_FLOOR) * ph.Z_PER_DB
    assert ph.zmap(np.inf) == pytest.approx((ph.DB_CEIL - ph.DB_FLOOR) * ph.Z_PER_DB)
    assert ph.zmap(-np.inf) == 0.0
    # C1 at the knee: one-sided slopes agree.
    eps = 1e-6
    left = (ph.zmap(ph.DB_KNEE) - ph.zmap(ph.DB_KNEE - eps)) / eps
    right = (ph.zmap(ph.DB_KNEE + eps) - ph.zmap(ph.DB_KNEE)) / eps
    assert left == pytest.approx(right, rel=1e-4)


def test_slice_exact_during_sweep():
    """The jw cut never enters the soft-clip region while R >= R_SWEEP_END."""
    w = np.linspace(0, 20e3, 20001)
    for R in ph.r_of_sweep(np.linspace(0, 1, 50)):
        assert ph.to_db(ph.mag_C(1j * w, R)).max() < ph.DB_KNEE


def test_peak_at_sweep_end():
    w = np.linspace(9e3, 11e3, 200001)
    _, H = signal.freqresp(tf_C(ph.R_SWEEP_END), w)
    peak_ref = 20 * np.log10(np.abs(H).max())
    assert peak_ref == pytest.approx(27.96, abs=0.01)
    wr, peak = ph.resonance(ph.R_SWEEP_END)
    assert 20 * np.log10(peak) == pytest.approx(peak_ref, abs=1e-4)
    assert wr == pytest.approx(w[np.abs(H).argmax()], abs=0.02)


def test_sweep_endpoints():
    assert ph.r_of_sweep(0.0) == pytest.approx(ph.R_START)
    assert ph.r_of_sweep(1.0) == pytest.approx(ph.R_SWEEP_END)


# --- zero beat: H_z family -------------------------------------------------------


def test_zero_far_left_is_H_C():
    s = 1j * np.logspace(2, 6, 500) - 3000.0
    R = ph.R_START
    np.testing.assert_allclose(
        ph.to_db(ph.mag_zero(s, R, -1e12)), ph.to_db(ph.mag_C(s, R)), atol=1e-6
    )
    np.testing.assert_array_equal(ph.mag_zero(s, R, -np.inf), ph.mag_C(s, R))


def test_zero_at_origin_is_H_R():
    s = 1j * np.logspace(2, 6, 500) - 3000.0
    R = ph.R_START
    np.testing.assert_allclose(ph.mag_zero(s, R, 0.0), ph.mag_R(s, R), rtol=1e-14)
    assert ph.mag_zero(0j, R, 0.0) == 0.0


@pytest.mark.parametrize("z", [-15e3, -8e3, -2e3, -1.0])
def test_zero_family_matches_freqresp(z):
    R = ph.R_START
    rc = R * ph.C
    num = [-rc, rc * z]  # RC (z - s)
    den = (rc * z - 1.0) * ph.denominator_coeffs(R)
    w = np.logspace(2, 6, 1500)
    _, H = signal.freqresp(signal.TransferFunction(num, den), w)
    np.testing.assert_allclose(ph.mag_zero(1j * w, R, z), np.abs(H), rtol=1e-9)
