"""Beat times shared by scenes and tests (film seconds). Captions live in script.py, camera
moves in camera.py; this holds the remaining data/display beats the layout checks need."""

S3_LIFT_START = 18.00  # sheet lift (display-only) 0 -> 1
S3_LIFT_RUN = 2.50
S3_SHEET_FADE_RUN = 2.00  # sheet opacity 0 -> 1, from S3_LIFT_START
S3_POLE_LABELS = 21.20

# Fixed overlays on screen (film time spans) — composition checks keep 3D content clear of them.
FORMULA_SPAN = (11.60, 76.0)  # H(s) at the top-left anchor (S2 end onward)
ROOTS_SPAN = (11.80, 15.80)  # "LCs^2+RCs+1 = 0 => s = ..." under the formula
TAG_SPAN = (S3_LIFT_START, 76.0)  # height tag under the formula
POLE_LABEL_SPAN = (S3_POLE_LABELS, 25.0)  # S3 only
PANEL_COLUMN_FROM = 30.40  # Bode panel flies in at the end of the S4 swing (panel column reserved)
ZERO_BEAT = (35.72, 48.31)  # S5: the sheet may carry the hand-moved zero (sigma = -15 .. 0)
APEX_SEPARATION_FROM = S3_LIFT_START  # the two tent poles must read as two spikes from here on
APEX_MIN_SEPARATION = 0.8  # frame units, screen x
