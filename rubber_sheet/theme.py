"""Single source of style: palette, fonts, sizes, easing, layout, quality presets, colormap.

Scenes must take every color/font/size/easing from here (CLAUDE.md theme rules).
"""

import os

import numpy as np
from manim import ManimColor, config, rate_functions

from rubber_sheet import camera as _camera

# --- palette ------------------------------------------------------------------------
BG = ManimColor("#0D1117")
FG = ManimColor("#E6EAF0")
MUTED = ManimColor("#7D8799")
FAINT = ManimColor("#2A3140")

POLE = ManimColor("#FF6B4A")  # poles / instability
ZERO = ManimColor("#3DD6C6")  # zeros / nails
SIGNAL = ManimColor("#F5C542")  # what you measure: jw cut, Bode, h(t)
ROLE_COLORS = {"POLE": POLE, "ZERO": ZERO, "SIGNAL": SIGNAL}

# Surface colormap by display height (0 = floor .. 1 = ceiling): desaturated indigo ramp.
SURFACE_STOPS = [(0.0, "#1A2340"), (0.55, "#5B6BC0"), (1.0, "#C9CFF5")]
SURFACE_OPACITY = 0.92
SURFACE_STROKE_OPACITY = 0.15
SURFACE_STROKE_WIDTH = 0.4

# --- type ---------------------------------------------------------------------------
FONT_BODY = "Inter"
FONT_TITLE = "Inter Display"
WEIGHT_BODY = "NORMAL"
WEIGHT_EMPH = "SEMIBOLD"
WEIGHT_TITLE = "SEMIBOLD"

SIZE_CAPTION = 36
SIZE_LABEL = 24
SIZE_SMALL = 20
SIZE_TITLE = 72
SIZE_TAKEAWAY = 48
SIZE_MATH = 40

MIN_CAPTION_XHEIGHT = 0.018  # fraction of frame height
MIN_LABEL_XHEIGHT = 0.013

# --- easing ---------------------------------------------------------------------------
ENTER = rate_functions.ease_out_cubic
EXIT = rate_functions.ease_in_cubic
SWEEP = rate_functions.smooth
camera_rate = _camera.trapezoid  # camera_rate(run_time) -> rate function

CAPTION_REVEAL = 0.8
CAPTION_EXIT = 0.4
CAPTION_LAG = 0.12
CAPTION_SHIFT_IN = 0.08
CAPTION_SHIFT_OUT = 0.06
UNDERLINE_TIME = 0.25

# --- layout (scene units; frame is 14.222 x 8) ------------------------------------------
FRAME_W = config.frame_width
FRAME_H = config.frame_height
SAFE_MARGIN = 0.05
CAPTION_BAND = dict(x0=-6.4, x1=6.4, y0=-3.80, y1=-2.70)
CAPTION_CENTER_Y = -3.25
TITLE_REGION = dict(x0=-6.4, x1=6.4, y0=1.6, y1=3.6)
PANEL_REGION = dict(x0=1.9, x1=6.75, y0=-2.55, y1=3.75)
BODE_BOX = (2.45, 6.6, 1.15, 3.3)  # (x0, x1, y0, y1) frame units
IMPULSE_BOX = (2.45, 6.6, -1.85, 0.25)
SCRIM_STEPS = 12
SCRIM_MAX_OPACITY = 0.75
SCRIM_TOP = -2.45  # scrim fades in from here down to the frame bottom

# --- 3D world (scene units) -------------------------------------------------------------
# s-plane in krad/s mapped to scene x (sigma) and y (omega). Domain sigma [-15, 5], omega [-15, 15]
# (poles never exceed |omega| = 10 krad/s; the linear-omega Bode view spans 0..15 krad/s).
SIGMA_RANGE = (-15.0, 5.0)
OMEGA_RANGE = (-15.0, 15.0)
UNITS_PER_KRAD = 0.25  # 20 krad/s -> 5 units wide, 30 krad/s -> 7.5 units deep

# --- quality presets ----------------------------------------------------------------------
QUALITY = os.environ.get("RS_QUALITY", "preview")
_PRESETS = {
    # Sheet cells: sigma_nodes = (cells on [sigma_min, 0], cells on [0, sigma_max]);
    # omega_half = cells on [0, omega_max] (mirrored). Faces = sum(sigma_nodes) * 2 * omega_half.
    "preview": dict(sigma_nodes=(12, 4), omega_half=12, cut_samples=300, curve_samples=500),  # 384 faces
    "review": dict(sigma_nodes=(28, 8), omega_half=28, cut_samples=600, curve_samples=1000),  # 2016
    "final": dict(sigma_nodes=(42, 14), omega_half=42, cut_samples=600, curve_samples=1500),  # 4704
}
PRESET = _PRESETS[QUALITY]


def configure():
    """Global manim config every scene shares."""
    config.background_color = BG


def surface_lut(n=256):
    """(n, 3) RGB lookup table, linear interpolation between SURFACE_STOPS."""
    xs = np.array([s[0] for s in SURFACE_STOPS])
    rgb = np.array([ManimColor(s[1]).to_rgb() for s in SURFACE_STOPS])
    t = np.linspace(0.0, 1.0, n)
    return np.stack([np.interp(t, xs, rgb[:, k]) for k in range(3)], axis=1)


def s_to_xy(sigma_krad, omega_krad):
    """s-plane (krad/s) -> scene (x, y)."""
    return np.asarray(sigma_krad) * UNITS_PER_KRAD, np.asarray(omega_krad) * UNITS_PER_KRAD
