"""Beat times shared by scenes and tests (film seconds). Captions live in script.py, camera
moves in camera.py; this holds the remaining data/display beats the layout checks need.
Spans are (start, end) in film seconds."""

S3_LIFT_START = 18.00  # sheet lift (display-only) 0 -> 1
S3_LIFT_RUN = 2.50
S3_SHEET_FADE_RUN = 2.00  # sheet opacity 0 -> 1, from S3_LIFT_START
S3_POLE_LABELS = 21.20

# --- S4 (25.00-35.72): slice along jw, hand the cut to the Bode panel, warp to log frequency ---
S4_POLE_LABELS_OUT = (25.00, 25.35)  # S3's labels leave while the camera still holds (move at 25.4)
S4_PLANE_IN = (25.30, 25.80)  # gold sigma = 0 plane (display-only opacity 0 -> 1)
S4_JW_LABEL_IN = (25.50, 26.10)  # 'jw' at the far end of the floor's jw axis (screen-anchored)
S4_SIGMA_LABEL_OUT = (25.60, 26.20)  # sigma points at the camera in the CUT view: label leaves
S4_CUT_DRAW = (25.70, 26.30)  # the exact cut grows along the plane (reveal 0 -> 1), done before the drop
S4_RIGHT_DROP = (26.30, 27.50)  # sigma > 0 half lowers by RIGHT_DROP_DEPTH and fades out
S4_PLANE_OUT = (27.40, 28.00)
S4_HANDOFF = 30.30  # camera holds CUT from 30.20: the cut's w >= 0 half becomes a fixed curve
S4_FLY = (30.40, 31.80)  # ... and flies into the Bode panel (linear w)
S4_PANEL_IN = (30.60, 31.40)  # panel frame/grid/labels (display-only opacity)
S4_SWAP = 31.80  # flyer -> the panel's live curve (identical geometry, one frame)
S4_WARP = (33.20, 35.20)  # display-only axis warp mu 0 -> 1 (linear w -> log10 w)
RIGHT_DROP_DEPTH = 0.8  # scene units
SWAP = 0.05  # duration of an invisible handoff between identical mobjects

# --- S5 (35.72-48.31): the sigma > 0 half returns while the camera goes back to ANALYSIS ---
S5_JW_LABEL_OUT = (35.80, 36.30)
S5_RIGHT_RESTORE = (36.00, 37.50)
S5_PROBE_TO_R = (36.20, 36.80)  # v_C -> v_R and numerator 1 -> RCs (CLAUDE.md: R during 36.2-46.6)
S5_EDGE_LABEL_IN = (37.20, 37.50)  # 'from -inf' at the domain edge while the zero approaches
S5_ZERO_SHOW = (37.85, 38.15)  # nail + floor ring appear as the zero reaches the edge (38.0)
S5_EDGE_LABEL_OUT = (38.00, 38.25)
S5_ZERO_LABEL_IN = (38.35, 38.85)  # 'zero' rides on the nail head (never with 'from -inf')
S5_SIGMA_LABEL_IN = (39.30, 39.90)  # the sigma billboard returns with the ANALYSIS view
S5_PROBE_TO_C = (45.60, 46.20)
S5_ZERO_LABEL_OUT = (45.75, 46.05)
S5_EDGE_LABEL_BACK = (46.15, 46.45)  # 'to -inf' while the zero leaves the domain
S5_ZERO_HIDE = (46.05, 46.35)
S5_EDGE_LABEL_GONE = (46.90, 47.20)
# Zero beat parameter u (physics.zero_slide): 0 = no zero (H_C), 1 = zero at the domain edge,
# 2 = zero at the origin (H_R). Phases: (span, u_from, u_to, easing name). Phase 1/4 move b = -1/z
# linearly (zero arriving from / leaving to -inf, off screen); 2/3 move z itself, easing out into
# the origin and back. Phase 1 ends at 15/0.8 = 18.75 krad/s, phase 2 starts at 3 * 5 = 15 krad/s.
S5_ZERO_PHASES = (
    ((37.20, 38.00), 0.0, 1.0, "LINEAR"),
    ((38.00, 41.00), 1.0, 2.0, "ENTER"),
    ((43.60, 46.20), 2.0, 1.0, "EXIT"),
    ((46.20, 47.00), 1.0, 0.0, "LINEAR"),
)

# --- S6 (48.31-61.00): lower R ---
S6_PANELS_IN = (48.31, 49.50)  # impulse panel + R/zeta/peak readouts (display-only opacity)
S6_SWEEP = (49.50, 61.00)  # R = 120 * (4/120)^u, u = SWEEP(alpha) (physics.r_of_sweep)

# Fixed overlays on screen (film time spans) — composition checks keep 3D content clear of them.
FORMULA_SPAN = (11.60, 76.0)  # H(s) at the top-left anchor (S2 end onward)
ROOTS_SPAN = (11.80, 15.80)  # "LCs^2+RCs+1 = 0 => s = ..." under the formula
TAG_SPAN = (S3_LIFT_START, 76.0)  # height tag under the formula
POLE_LABEL_SPAN = (S3_POLE_LABELS, S4_POLE_LABELS_OUT[1])  # S3 and the first 0.35 s of S4
PLANE_SPAN = (S4_PLANE_IN[0], S4_PLANE_OUT[1])
JW_LABEL_SPAN = (S4_JW_LABEL_IN[0], 35.72)  # S4 (S5 decides its own)
PROBE_SPAN = (S4_PANEL_IN[0], 76.0)  # 'output: v_C' right of the formula, with the Bode panel
DISCLOSURE_SPAN = (37.20, 47.40)  # 'interpolated: zero moved by hand' (S5 zero beat)
PANEL_COLUMN_FROM = S4_FLY[0]  # Bode panel flies in at 30.4: panel column reserved from here
BODE_SPAN = (S4_FLY[0], 76.0)
IMPULSE_SPAN = (S6_PANELS_IN[0], 76.0)
READOUTS_SPAN = (S6_PANELS_IN[0], 76.0)
ZERO_BEAT = (35.72, 48.31)  # S5: the sheet may carry the hand-moved zero (sigma = -15 .. 0)
APEX_SEPARATION_FROM = S3_LIFT_START  # the two tent poles must read as two spikes from here on
APEX_MIN_SEPARATION = 0.8  # frame units, screen x
