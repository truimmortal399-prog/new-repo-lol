# The Rubber Sheet — merged plan (v1 + Revision 2 + Revision 3)

Silent, captioned Manim CE animation (~76 s) showing how the poles and zeros of a series-RLC
transfer function shape |H(s)| — a "rubber sheet" over the s-plane — and how its jω cut is the
frequency response. Primary master 1080p60; 4K60 only if the Gate 3 budget allows.

## 1. Environment (measured)
| Item | Status |
|---|---|
| Python | 3.13.16; venv `.venv` via `uv` |
| Manim | Community 0.22.0 (manimpango 0.7.0, pycairo 1.29.2, PyAV 19.0.1) |
| numpy / scipy | 2.5.3 / 1.18.1 |
| ffmpeg | 6.1.1 |
| LaTeX | apt TeX Live 2023 (pdfTeX 1.40.25) + dvisvgm 3.2.1. CTAN blocked → no tlmgr |
| Fonts | Inter, Inter Display (static OTFs) — resolve by name in Pango (Gate 1 width check) |
| HW | 4 vCPU Xeon 2.1 GHz, 15 GB RAM, no GPU |

Install: see requirements.txt header; `tools/smoke_test.py` checks LaTeX and fonts.

## 2. Prior art (no novelty claim)
The rubber-sheet / circus-tent reading of pole-zero plots is a common teaching device (DSP forums;
Lundberg, IEEE CSM). 3D "Bode surfaces" including σ exist (Springer CSSP 2016); the jω restriction
being the Bode diagram is standard. An MIT project proposed animating the cut; 3Blue1Brown's 2025
Laplace videos discuss poles (3D |H| surface not verified); UW's LaplaceViz3D shows |H(s)|
surfaces. This piece differs in execution: a physical component (R) drives three live linked views,
the dB-vs-linear-ω → log-ω step is shown explicitly, the zero enters as a disclosed hand-moved
family of real transfer functions, and narration is captions only.

## 3. Physics and display mapping
- L = 10 mH, C = 1 µF → ω₀ = 10⁴ rad/s, R_crit = 200 Ω, ζ = R/200.
- R = 120 Ω → ζ = 0.6, poles −6000 ± j8000 rad/s (3-4-5). Underdamped poles lie on |s| = ω₀.
- Sweep R = 120·(4/120)^u (log), then 4 → 0 (linear). R = 4 Ω → peak 27.96 dB.
- H_C = 1/(LCs²+RCs+1) (output across C). Zero beat: H_z = H_C·RC(z−s)/(RCz−1); z = −∞ → H_C,
  z = 0 → H_R = RCs·H_C. Every intermediate is a real transfer function — disclosed on screen as
  "interpolated: zero moved by hand".
- Sheet height = 20·log₁₀|H| (dB): hard floor −40, identity to +30 knee, C¹ tanh roll-off to +40
  ceiling, 0.05 units/dB, floor at z = 0. The jω cut is exact (< knee) for the whole sweep.
- h(t) = (ω₀/√(1−ζ²))·e^{−ζω₀t}·sin(ω_d t); envelope (ω₀/√(1−ζ²))·e^{Re(p)t}.

## 4. File structure
```
CLAUDE.md  requirements.txt  docs/PLAN.md
manim.cfg  pytest.ini
rubber_sheet/ physics.py theme.py script.py beats.py camera.py rig.py timeline.py captions.py
              surface.py panels.py world.py common.py layout.py      (built at Gates 1–2)
              circuit.py                                               (S2, after Gate 3)
scenes/ s03_poles_sheet.py s04_slice_bode.py s05_zero_nail.py s06_sweep.py   (built)
        probe_fixed_frame.py bench_live.py probe_fabric.py                  (diagnostics)
        s01_hook_title.py s02_circuit.py s07_limit_payoff.py                (after Gate 4)
tools/  smoke_test.py keyframes.py check_captions.py frame_search.py still.py render_scene.py
        time_bench.py time_scenes.py fabric_check.py text_sharpness.py crown_stills.py   (built)
        render.sh check_continuity.py check_palette.py                    (with the remaining scenes)
tests/  test_physics test_captions test_captions_render test_camera test_timeline test_panel_data
        test_layout test_composition test_depth_sort test_scenes_monitor test_slice_and_zero
```

## 5. Theme
- BG `#0D1117`, FG `#E6EAF0`, MUTED `#7D8799`, FAINT `#2A3140`; accents POLE `#FF6B4A`,
  ZERO `#3DD6C6`, SIGNAL `#F5C542`; surface colormap `#1A2340 → #5B6BC0 → #C9CFF5`.
  `check_palette.py`: WCAG ≥ 4.5 for text on BG; accents distinguishable under simulated
  deuteranopia/protanopia.
- Fonts: Inter (captions/labels), Inter Display SemiBold (titles), LaTeX CM (math); readouts in
  fixed-width digit slots. Sizes: caption 36, labels 24, title 72; caption x-height ≥ 1.8 % of
  frame height, labels ≥ 1.3 %.
- Easing: ENTER ease_out_cubic (0.5–0.8 s), EXIT ease_in_cubic (0.35–0.5 s), camera = trapezoidal
  velocity profile with 0.8 s ramps, sweeps `smooth` on a log-mapped tracker.
- Camera: peak combined angular speed √(φ'²+θ'²) ≤ 15°/s, checked at 600 samples per move.
- Layout: frame 14.22×8; title-safe |x| ≤ 6.4, |y| ≤ 3.6; caption band y ∈ [−3.80, −2.70],
  x ∈ [−6.4, 6.4]; panel column x ∈ [1.9, 6.4]: BODE_BOX (2.45, 6.15, 1.35, 3.12), IMPULSE_BOX
  (2.45, 6.15, −1.95, −0.05). Enforced by tests/test_layout.py and tests/test_composition.py.

## 6. Caption system
- `Caption(id)`: one MarkupText line in Inter (ligatures off, glyphs mapped 1:1 to characters,
  asserted), grouped per word; `$…$` math tokens are converted to Unicode (`\omega`→ω, …; unknown
  TeX raises) and set in Inter italic (letters only) — consistent with the caption face, instead of
  per-token MathTex. ≤ 2 lines. Emphasis = accent colour + 0.25 s underline under the accent glyphs
  only, below the row's lowest descender.
- Reveal: word mode LaggedStart FadeIn(shift 0.08·UP, scale 0.97), lag 0.12; phrase mode lag 0.35;
  0.8 s. Exit: FadeOut(shift 0.06·UP), 0.4 s.
- Scrim: 12 stacked full-width rectangles, BG color, opacity 0 → 0.75 (ease-in). 24 if banding
  shows; fallback a stretched 1×256 PNG gradient ImageMobject.
- Rule: 200 wpm, math token = 2 words, hold = 0.5 + n/3.33 (ceil 0.01 s), slot = 0.8 + hold + 0.4.
  Same-band reveals start ≥ previous exit end, except `continuation=True` pairs (only C7/C8), which
  may start at the previous hold end.
- `CaptionTrack`: `clips()` → (local time, reveal/exit animation) pairs placed on the scene's
  Timeline at the script's times (holds met by construction; a reveal clamped onto a grid-rounded
  scene start moves the whole caption). `monitor()` scene updater: logs first/last visible frame,
  checks protected visuals against the band, 3D visuals against fixed HUD blocks (annotations
  excepted), and flags stray unregistered mobjects. `write_log()` → out/captions/<scene>.json.

## 7. Storyboard and caption table (authoritative)
R = reveal, H = hold, X = exit end; n counts words, math token = 2.

| ID | Beat · scene | Caption | n | R | H (len) | X end |
|---|---|---|---|---|---|---|
| C1 | B1 Hook · S1 | "Two invisible **points** decide how a circuit **rings**." | 8 | 0.30–1.10 | 1.10–4.01 (2.91) | 4.41 |
| T | Title overlay · S1 (title region) | **The Rubber Sheet** | 3 | 4.01–4.81 | 4.81–6.22 (1.41) | 6.62 |
| C2 | B3 Circuit · S2 | "An RLC circuit and its transfer function." | 7 | 6.80–7.60 | 7.60–10.21 (2.61) | 10.61 |
| C3 | B4 Poles · S3 | "Where $H$ blows up: the **poles**." | 7 | 12.00–12.80 | 12.80–15.41 (2.61) | 15.81 |
| C4 | B5 Sheet · S3 | "Lift the gain above every point $s$." | 8 | 16.40–17.20 | 17.20–20.11 (2.91) | 20.51 |
| C5 | B5 Sheet · S3 | "Each pole is a **tent pole**." | 6 | 21.20–22.00 | 22.00–24.31 (2.31) | 24.71 |
| C6 | B6 Slice · S4 | "Slice along the $j\omega$ axis…" | 6 | 25.20–26.00 | 26.00–28.31 (2.31) | 28.71 |
| C7 | B6 Slice · S4 | "…the edge is the **frequency response**." | 6 | 29.40–30.20 | 30.20–32.51 (2.31) | 32.91 |
| C8 ✂ | B6 Log warp · S4 (continuation of C7; first to drop) | "Log frequency: a **Bode plot**." | 5 | 32.51–33.31 | 33.31–35.32 (2.01) | 35.72 |
| C9 | B7 Zero · S5 | "Probe the resistor: a **zero** appears." | 6 | 36.40–37.20 | 37.20–39.51 (2.31) | 39.91 |
| C10 | B7 Zero · S5 | "A zero **nails** the sheet down." | 6 | 40.40–41.20 | 41.20–43.51 (2.31) | 43.91 |
| C11 | B7 Return · S5 | "Back to the capacitor." | 4 | 45.40–46.20 | 46.20–47.91 (1.71) | 48.31 |
| C12 | B8 Sweep · S6 | "Now lower $R$." | 4 | 48.31–49.11 | 49.11–50.82 (1.71) | 51.22 |
| C13 | B8 Sweep · S6 | "**Poles** creep toward the axis…" | 5 | 51.50–52.30 | 52.30–54.31 (2.01) | 54.71 |
| C14 | B8 Sweep · S6 | "…sharper **peak**, longer **ringing**." | 4 | 56.00–56.80 | 56.80–58.51 (1.71) | 58.91 |
| C15 | B9 Limit · S7 | "$R = 0$: poles on the axis." | 6 | 61.20–62.00 | 62.00–64.31 (2.31) | 64.71 |
| C16 | B9 Limit · S7 | "**Infinite** peak. Ringing that **never stops**." | 6 | 65.11–65.91 | 65.91–68.22 (2.31) | 68.62 |
| C17 | B10 Takeaway · S7 (title style) | "Nearer the axis, **longer the ring**." | 6 | 69.20–70.00 | 70.00–73.80 (3.80) | 74.20 |

Emphasis colors: points/poles/tent pole/Poles/Infinite → POLE; zero/nails → ZERO;
rings/frequency response/Bode plot/peak/ringing/never stops/longer the ring/jω → SIGNAL.
Film end 76.0 s. Dropping C8 + log warp: C7 holds to 33.0, S4 shortens ≈ 2.8 s → ≈ 73.2 s.

### Scene cuts (rubber_sheet/script.py `SCENES`; no caption crosses a cut — tested)
S1 0.00–6.62 · S2 6.62–11.60 · S3 11.60–25.00 · S4 25.00–35.72 · S5 35.72–48.31 · S6 48.31–61.00 ·
S7 61.00–76.00.

### Camera moves (rubber_sheet/camera.py `MOVES`; peaks derived from start/end states — tested)
Framing (zoom/pan) follows monotone-cubic keyframes found by tools/frame_search.py against
layout.frame_violations; every move is checked at 120 samples (tests) and 200 (frame_search).
| Move | Time | From → to (φ, θ, zoom) | Peak √(φ'²+θ'²) | Peak pan |
|---|---|---|---|---|
| S3 tilt and swing | 15.00–21.00 | TOP (0, −90, 0.82) → S3_END (58, −50, 0.74) | 13.55°/s | 0.19/s |
| S4 swing to CUT | 25.40–30.20 | S3_END → CUT (82, 0, 0.78) | 13.87°/s | 1.26/s |
| S5 return to ANALYSIS | 35.72–39.92 | CUT → ANALYSIS (64, −40, 0.64) | 12.90°/s | 0.52/s |
| S6 drift | 49.50–61.00 | ANALYSIS → ANALYSIS_DRIFT (64, −48, 0.64) | 0.75°/s | 0.01/s |
Gate 4 re-framing: tent-pole tops (ceiling + 0.3, the highest 3D points) joined the rules and hit
the height tag at R = 120 in the old CUT (pan y −0.6) and ANALYSIS (60°, zoom 0.66) — at 0.66 there
was no room between the tag and the caption band at any angle searched; CUT pan y → −0.88, ANALYSIS
→ (64°, −40°, 0.64). S4/S5 keyframes re-searched with the gold plane and the new HUD boxes.
Post-Gate-4: tent overshoot 0.3 → 0.2 (surface.TENT_TOP); all moves still pass at 200 samples with
the same keyframes (more margin); the S6 drift became a pure rotation at zoom 0.64.

### Visual timeline
- **S1 0.00–6.62 Hook + title.** Sheet, poles punching up, gold jω glow, HERO orbit 3°/s; title
  fades in upper third over the hook (no separate card); 0.3 s dip to BG at the end.
- **S2 6.62–11.6 Circuit.** `Create` schematic (6.7–9.2) simultaneously with `Write(H(s))`
  (7.4–9.4); values R = 120 Ω, L = 10 mH, C = 1 µF; v_out bracket on C; H(s) to top-left (10.4–11.4).
- **S3 11.6–25.0 Poles → sheet (built).** s-plane fades in 11.6; `LCs²+RCs+1 = 0` writes 11.8–12.6;
  `⇒ s = −6 ± j8 krad/s` 12.7–13.3; two × fly from the end of that line 13.3–14.4 and hand over
  to the world × at 14.4; dashed |s| = 10 circle 13.6–14.6; tilt φ 0→58° 15.6–20.6 (tick labels
  fade); lift + sheet fade from 18.0 (2.5 s / 2.0 s); tag `height = 20 log₁₀|H| (dB)` with
  "floor −40 dB · soft ceiling +40 dB" at 18.0 (persists); jω floor label fades at 18.0; tent
  poles grow with the lift; θ −90→−50° 21.0–24.6; "pole" labels (screen-anchored) 21.2.
- **S4 25.0–35.72 Slice → Bode (built).** S3's pole labels leave 25.0–25.35 (camera holding);
  gold σ = 0 plane 25.3 (split at the cut height: no painter's-order teeth); 'jω' at the far end of
  the floor's jω axis 25.5; σ label leaves 25.6; exact jω cut grows 25.7–26.3; σ > 0 half lowers
  and fades 26.3–27.5 (the plane's lower part shows as the gold cross-section); plane leaves
  27.4–28.0; swing to CUT 25.4–30.2; handoff 30.3 (identical fixed curve), fly to the panel's
  linear-ω axis 30.4–31.8 with panel + 'output: v_C' fading in 30.6–31.4; swap to the live curve
  31.8; log warp 33.2–35.2 (5/15 ticks fade, 1/10/100 slide); hold to 35.72.
- **S5 35.72–48.31 Zero (built).** Return to ANALYSIS 35.72–39.92; 'jω' leaves 35.8; σ > 0 half
  rises back 36.0–37.5; probe v_C → v_R and numerator 1 → RCs 36.2–36.8 (only those glyphs);
  disclosure 'interpolated: zero moved by hand' 37.2–47.4; zero u: −∞ → edge 37.2–38.0 (b = −1/z
  linear, 'from −∞' label), edge → 0 38.0–41.0 (ease out), hold, 0 → edge 43.6–46.2 (ease in),
  edge → −∞ 46.2–47.0 ('to −∞'); teal nail + floor ring 37.85–46.35, 'zero' label 38.35–46.05; the
  sheet, the jω cut (dives to the floor at ω = 0) and the Bode panel (band-pass) follow H_z; probe
  v_R → v_C, numerator back 45.6–46.2; σ label returns 39.3. (Plan rev. 3 had 37.4/46.8 for the
  zero's off-screen phases: lengthened to 0.8 s so the speed matches at the domain edge.)
- **S6 48.31–61.0 Sweep (built).** Impulse panel + R/ζ readouts + gold Bode peak readout join
  48.31–49.5 (opacity trackers); sweep 49.5–61.0, R = 120·(4/120)^u, u = smooth(α); poles glide on
  |s| = ω₀; sheet, cut, Bode, h(t) + envelope, readouts follow; camera drift θ −40 → −48°.
- **S7 61.0–76.0 Limit + payoff.** R 4 → 0 61.3–64.3 with push-in 61.5–64.8; ∞ marker; sustained
  ringing. Pull back 68.2–70.8; R eases to 40 Ω; C17; clean final frame 74.2–75.6; fade 75.6–76.0.

## 8. Technical design
- **LiveSurface:** fixed-topology quads, one vectorized numpy pass per frame writes `face.points`,
  `fill_rgbas` and `stroke_rgbas` in place, with vectorized Lambert shading (camera shading off).
  Pole-tracking grid: nodes re-warped every frame by a density with Gaussian bumps at the poles
  (and the zero in B7); σ = 0 is always a node line (exact cut, clean half split). Mesh peak at
  the pole reaches ≥ 38 dB at final quality for all R. Presets (σ cells left|right × ω cells):
  preview 16×24 = 384 faces, review 36×56 = 2016, final 56×84 = 4704; refresh ≈ 9 ms/frame.
  Domain σ ∈ [−15, 5], ω ∈ [−15, 15] krad/s (changed at Gate 2 from ±20: poles never exceed
  |ω| = 10 and ±15 lets the top view fit legibly; the linear-ω Bode view spans 0–15 krad/s).
- **Depth (RigCamera):** 3D leaves are painted far-to-near by horizontal distance from the eye
  (stock bbox-centre key left 4–114 back-face pixels at the spikes; this gives 0 — test_depth_sort).
  Floor objects (grid, axes, circle, ×, axis labels) are a layer painted first; tent-pole segments
  below the sheet are painted before it, those above sort just after the faces at the pole.
  Sheet faces carry precomputed sort points (137 → 11 ms/frame). Nodes snap onto each pole, so
  the drawn peak is exactly the ceiling at every R (no bobbing during the sweep).
- **jω cut → panel:** exact 600-sample polyline (not read off the mesh); at handoff project with
  `camera.project_points`, swap in an identical fixed-frame VMobject, `Transform` to the panel
  curve. BodePanel x(ω) = (1−μ)·lin + μ·log (data exact, axis warped); +∞ at R = 0 → clipped with
  "↑ ∞" marker.
- **Fixed-in-frame in ThreeDScene (settled at Gate 2, `scenes/probe_fixed_frame.py`):** stock
  ThreeDCamera keeps in-place updates and same-structure always_redraw fixed, but projects
  DecimalNumber digits, padded always_redraw children and later-added children. `RigCamera`
  re-derives the fixed set from registered roots every frame → all five probe patterns fixed.
- **RigCamera:** stock Cairo `frame_center` is broken for composition (cached cairo context,
  double shift of 3D content, moves fixed-in-frame mobjects). RigCamera: frame_center = pivot
  only, base mapping at ORIGIN, plus pan_x/pan_y for screen placement of 3D content.
- **Timeline:** one play per scene; outer AnimationGroup with explicit empty group (else every
  non-introducer clip's mobject is added at t = 0), `EnsureIn` before non-introducer clips, driver
  mobject at the back so all mobjects redraw every frame.
- **Impulse panel:** 1500 samples, t ∈ [0, 8] ms, y = h/ω₀ ∈ ±1.3, coral dashed envelope.
- **Camera presets** (`rubber_sheet/camera.py`): TOP (φ 0), S3_TILTED/S3_END, HERO, CUT, ANALYSIS;
  zoom/pan chosen against tests/test_composition.py (projected floor/sheet/labels clear of the
  band, inside title-safe, left of the panel column, clear of the formula and height tag, along
  every move). Scene boundary states are these CamStates; `check_continuity.py` (to build with
  the remaining scenes) will require < 1.5 % mean pixel diff across cuts.

## 9. Risks
| Risk | Mitigation |
|---|---|
| LaTeX failures | Pre-compile all MathTex; amsmath only; no circuitikz |
| 3D render time | In-place LiveSurface, mesh presets, parallel scenes, partial-movie caching, Gate 3 timing |
| Artifacts near poles | Pole-tracking grid, soft knee, exact separate cut curve, zoomed keyframes |
| Depth-sort popping | Segmented lines, z offsets, 15 fps frame review |
| Fixed-in-frame + updaters | Gate 2 probe; fallback transparent pass + overlay |
| Caption overlap | Fixed band + scrim + per-frame projection checker + RS_DEBUG overlays |
| Readout jitter | Fixed-slot digits |
| Encoder quality/banding | Check SceneFileWriter; lossless .mov intermediates if needed |
| Pango font fallback | Gate 1 width check (PASSED); fallback `manimpango.register_font` |
| Scrim banding | 24 steps or PNG fallback |
| 4K over budget | Gate 3 → 1440p or upscale |
| B6 rushed | Drop C8 + log warp |
| Container recycled | Commit/push often; background renders with cached partials |

## 10. Verification
1. `pytest tests/` (pytest.ini sets pythonpath): physics vs scipy (poles sorted by (imag, real);
   R = 0 compares |p| and |Re p| < 1e-9·ω₀; freqresp; impulse atol 1e-6; polyval; zmap; H_z family),
   panel-data inversion, caption rule (n recomputed from text, holds, sequencing, no caption
   crosses a scene cut, ≤ 78 s), camera (state continuity, peak speed from start/end states,
   600-sample numeric check, ≤ 15°/s).
2. Renders + `check_captions.py`: first/last visible frame equal to the exact frames expected on
   the film grid (±0.5 frame), on-screen ≥ reveal + hold, x-height, overlap violations, strays.
3. `keyframes.py <scene>`: clears out/keys/<scene>, extracts scene edges, every caption's
   mid-hold and beat times (plus extras) from the newest render, builds a labelled contact sheet;
   every frame inspected at 1080p.
4. `check_continuity.py` across scene cuts.
5. Final: ffprobe (resolution, 60 fps, duration, no audio) + 4K/1080p keyframe spot-check.

## 11. Render and delivery
**Encode path (decided before Gate 3; one lossy generation, BT.709).**
1. Every scene is rendered **lossless in RGB**: `manim.cfg` sets `codec = libx264rgb`,
   `pixel_format = rgb24` (stored as `gbrp`), `qp = 0`, `preset = veryfast`. No YUV conversion
   happens inside Manim (its PyAV path would otherwise convert RGBA → BT.601 yuv420p, untagged).
   Never pass `--encoder-option`/`--config_file` (they replace this table instead of merging).
2. Scenes are joined by **stream copy** (all share one encoder spec):
   `ffmpeg -f concat -safe 0 -i out/scenes.txt -c copy out/concat_rgb.mkv`
3. **One final lossy encode**, RGB → BT.709 limited-range 4:2:0, tagged bt709:
   ```bash
   ffmpeg -i out/concat_rgb.mkv -an \
     -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
     -c:v libx264 -preset slow -crf 18 -tune animation \
     -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
     -movflags +faststart out/the_rubber_sheet_1080p60.mp4
   ```
   4K/1440p master: the same from the 4K/1440p scene renders, CRF 16.
   Verified on a colour swatch: lossless intermediates are bit-exact; after the final encode every
   accent decodes within 3 levels of its theme value (the old untagged-BT.601 path could shift
   accents by ~15 levels in BT.709-assuming players).
4. Deliverables: 1080p committed if < 100 MB. 4K hand-over: this session's GitHub tools cannot
   create releases or upload assets (read-only release tools only) — see Gate 3 below.

**Gate 3 measurements** (`tools/time_bench.py` on `scenes/bench_live.py`: final mesh 4704 faces,
Bode + impulse panels, readouts, caption, monitor; lossless encode included; 4 vCPU):
| | s/frame | setup |
|---|---|---|
| 1080p60 | 0.543 | 2.8 s |
| 2160p60 | 0.614 | 5.1 s |
| 2160p60, 3 renders in parallel | 0.72 each | — |
Frame cost is Python-bound (Cairo path building per face), so 4K costs only +13 % per frame.
Final encodes (measured on 4 s of bench): 4K CRF 16 ≈ 6.0 s per film second, 3.4 Mbit/s;
1080p CRF 18 ≈ 2.2 s per film second, 1.1 Mbit/s.
**Projection** (4560 frames at 60 fps, 4261 of them 3D, all costed at bench load): 3 parallel
workers, longest-processing-time schedule → critical path S6 + S5 = 1517 frames × 0.72 s ≈ 18 min
(≈ 28 min with a 1.5× margin for heavier scenes); serial would be ≈ 45 min. Plus final encodes
≈ 8 min (4K) + 3 min (1080p). **≈ 30–40 min wall ≪ 3 h → 4K is GO.**
Proposed: render 4K once and derive the 1080p master by a Lanczos downscale of the lossless 4K
concat in its final encode (supersampled anti-aliasing, no second render).
Projected file sizes (bench bitrate; real content varies): 4K ≈ 30–80 MB, 1080p ≈ 10–25 MB.
Lossless intermediates ≈ 1.5 GB at 4K (disk has > 25 GB free).

## 11b. Gate 4 measurements
See the Gate 4 report: real-scene timing (tools/time_scenes.py, tools/render_scene.py), fabric
shimmer check (tools/fabric_check.py), text sharpness (tools/text_sharpness.py).

## 12. Gates
1. Install, LaTeX + font smoke test, test_physics.py. (done; pre-Gate-2 fixes: scene cuts moved
   so no caption crosses one, pytest.ini, state-derived camera test, impulse atol 1e-6)
2. LiveSurface, captions, theme, S3 at preview + keyframes; fixed-in-frame probe; bench_live.py.
   (done, pending approval; reviewed by a 4-lens adversarial workflow, findings fixed)
3. 2 s timing of bench_live.py at 4K60 and 1080p60 → full estimate, 4K go/no-go.
   (approved: 4K GO; 1080p by Lanczos downscale of the 4K master)
4. S4, S5, S6 built, tested (test_scenes_monitor, test_slice_and_zero, dense composition), rendered
   at 1080p60 final mesh; fabric shimmer, text sharpness, real-scene timing. (pending approval)
Then S7, S1, S2; then the full 4K render.
