# The Rubber Sheet — Manim CE project

A ~76 s, silent, captioned 1080p60 (4K60 if the Gate 3 budget allows) animation showing how the
poles and zeros of a series-RLC transfer function shape |H(s)| and the frequency response.
Full plan: docs/PLAN.md.

## Versions
- Manim Community 0.22.0, Python 3.13, scipy 1.18.1 — pinned in requirements.txt, venv at .venv
- Always run via `.venv/bin/manim` / `.venv/bin/python`. LaTeX comes from apt TeX Live 2023
  (CTAN is blocked from this container, so no tlmgr). Fonts: Inter / Inter Display (fonts-inter).

## Render
- Preview one scene:  `RS_QUALITY=preview .venv/bin/manim -ql scenes/<file>.py <Scene>`
- Still frame:        `RS_QUALITY=preview .venv/bin/manim -ql -s scenes/<file>.py <Scene>`
- All previews:       `tools/render.sh preview`    (480p15, parallel, concat -> out/preview.mp4)
- Primary master:     `tools/render.sh final1080`  (1080p60, RS_QUALITY=final, CRF 18)
- 4K master:          `tools/render.sh final4k` — ONLY after the Gate 3 timing test projects < 3 h wall.
  Otherwise 1440p60 (`-qp`) or a Lanczos upscale of the 1080p master.

## Gates (execution is gated)
Stop and report at each gate. Never start S1/S2/S4–S7 before Gates 2 and 3 are approved.
1. Install + LaTeX/font smoke test (`tools/smoke_test.py`) + `tests/test_physics.py`.
2. LiveSurface, captions, theme, S3 at preview, fixed-in-frame/updater probe, benchmark scene.
3. 2 s timing of `scenes/bench_live.py` at 4K60 and 1080p60 -> full-render estimate.

## Theme rules (non-negotiable)
- Colors, fonts, sizes, easing, z-mapping ONLY from `rubber_sheet/theme.py`. No literal hex/fonts in scenes.
- 3 accents with fixed roles: POLE (coral) = poles/instability, ZERO (teal) = zeros/nails,
  SIGNAL (gold) = what you measure (jω cut, Bode, h(t)).
- Camera: trapezoidal velocity profile (0.8 s ramps); peak combined angular speed
  sqrt(φ'² + θ'²) ≤ 15°/s (tests/test_camera.py). No move shorter than 1.2 s.

## Captions
- Only via `rubber_sheet/captions.py`, inside the caption band; never place visuals in the band.
- Caption text ONLY from `rubber_sheet/script.py`.
- Reading rule: 200 wpm (3.33 words/s), inline math token = 2 words.
  hold = 0.5 + n/3.33 (rounded up to 0.01 s); slot = reveal 0.8 + hold + exit 0.4.
- In the same band a reveal starts at or after the previous caption's exit end, except pairs
  flagged `continuation=True` (only C7/C8), which may start at the previous hold end.
- Copy is cut before the film is lengthened. Film ≤ 78 s.

## Data rules
- All numbers come from `rubber_sheet/physics.py` (pure numpy, no manim import).
- Linked quantities = ValueTracker + updaters. No hand-keyed data animation. Display-only
  transforms (camera, axis warp, lift-in scale) are allowed and named as such in code.
- Sheet height is 20·log10|H| (dB) through `physics.zmap` — the on-screen tag must say so.
- The zero slide (B7) is a hand-moved zero, disclosed on screen ("interpolated: zero moved by hand").

## Manim 0.22 mechanics (verified at Gate 2 — follow these)
- 3D scenes use `RigCamera` (`rubber_sheet/rig.py`). Never compose with stock `frame_center`: in
  Cairo it is baked into a cached context, double-shifts 3D content and moves fixed-in-frame
  mobjects. Compose with `CamState(pivot, zoom, pan)`; move with `rig.move_anims(camera, Move)`.
- Fixed-in-frame: register with `camera.add_fixed_in_frame_mobjects` (does not add to scene).
  RigCamera re-derives the fixed set from those roots every frame, so later-added children stay
  fixed. Still prefer in-place updates; never use `DecimalNumber` for live values (use
  `panels.Readout`).
- Scenes run as one `Timeline` play (`rubber_sheet/timeline.py`): explicit empty group,
  `EnsureIn` before non-introducer clips, a driver mobject at the back (everything redrawn).
- Camera shading is off; `LiveSurface` shades its faces (vectorized Lambert).
- `project_points` uses last frame's rotation inside updaters — use `RigCamera.screen_points`.
- Run `.venv/bin/ruff check --select F,E9 --line-length 140 rubber_sheet scenes tools tests`.

## Quality bar
No caption/visual overlap (automated), no caption shorter than its reading time (automated),
no text below min size, no jitter in live readouts, continuity across scene cuts,
numerics agree with scipy (pytest). 3D: no visible faceting at the jω cut, no depth-sort popping.

## Self-review procedure (after every scene change)
1. `.venv/bin/python -m pytest -q tests/`  (numerics vs scipy, panel data inversion, captions, camera)
2. Render the scene at -ql; `tools/check_captions.py` (overlap + hold-time log)
3. `tools/keyframes.py <scene>` -> out/keys/<scene>/*.png + contact sheet; LOOK at every frame
4. Checklist: legible? overlaps? clipped text/axes? colors per role? motion eased? cut continuity?
   Height tag present in every 3D frame after 18.0 s? Probe label matches the active transfer
   function (C, or R during 36.2–46.6 s)?
5. Fix, re-render, repeat. Only then a 1080p review render.

## Git
Develop on `claude/relaxed-ride-rmpexs`. Never commit media/ or out/ (except the final 1080p
deliverable if < 100 MB). 4K goes to a GitHub Release asset, not LFS.
