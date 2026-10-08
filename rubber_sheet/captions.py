"""Kinetic captions: per-word reveals, emphasis in accent colors, scrim, timing log, overlap check.

A caption is one MarkupText (Inter; math tokens in Inter italic) so kerning and baseline are
exact; its glyphs are grouped per word for the LaggedStart reveal. Ligatures/contextual
alternates are disabled so that glyphs map 1:1 to characters (asserted at build time).

Timing comes only from rubber_sheet/script.py: `CaptionTrack.clips()` returns (local_time,
animation) pairs that a scene schedules on its timeline, so holds are met by construction.
"""

import json
import os
import re
from dataclasses import dataclass, field

import numpy as np
from manim import (
    UP,
    VMobject,
    config,
    AnimationGroup,
    Create,
    FadeIn,
    FadeOut,
    LaggedStart,
    Line,
    MarkupText,
    Rectangle,
    VGroup,
)

from manim.utils.family import extract_mobject_family_members

from rubber_sheet import script as sc
from rubber_sheet import theme as th
from rubber_sheet.timeline import clamp_local

_TOKEN = re.compile(r"\{(POLE|ZERO|SIGNAL):([^{}]*)\}|\$([^$]*)\$|(\s+)|([^\s{$]+)")
UNDERLINE_GAP = 0.05  # below the lowest descender of the row
_PHRASE_BREAK = re.compile(r"[,:;.…]$")


@dataclass
class _Char:
    ch: str
    italic: bool
    role: str | None


@dataclass
class _Word:
    chars: list = field(default_factory=list)

    @property
    def text(self):
        return "".join(c.ch for c in self.chars)

    @property
    def role(self):
        roles = {c.role for c in self.chars if c.role}
        return roles.pop() if len(roles) == 1 else None


# TeX commands allowed inside caption math tokens, set as Unicode in Inter (letters italic).
TEX_TO_UNICODE = {r"\omega": "ω", r"\zeta": "ζ", r"\sigma": "σ", r"\infty": "∞", r"\pm": "±", r"\cdot": "·"}


def math_chars(tex):
    """'j\\omega' -> [('j', italic), ('ω', italic)]; digits/operators upright. Raises on unknown TeX."""
    for cmd, uni in TEX_TO_UNICODE.items():
        tex = tex.replace(cmd, uni)
    if "\\" in tex or "{" in tex or "^" in tex or "_" in tex:
        raise ValueError(f"unsupported TeX in caption math token: {tex!r}")
    return [(ch, ch.isalpha()) for ch in tex]


def _parse(text):
    """Split caption markup into words of styled characters."""
    words, current = [], _Word()

    def flush():
        nonlocal current
        if current.chars:
            words.append(current)
        current = _Word()

    def emit(segment, role, math=False):
        chars = math_chars(segment) if math else [(ch, False) for ch in segment]
        for ch, italic in chars:
            if ch.isspace():
                flush()
            else:
                current.chars.append(_Char(ch, italic, role))

    def emit_mixed(segment, role):
        # segment may contain $...$ math
        for part in re.split(r"(\$[^$]*\$)", segment):
            if part.startswith("$") and part.endswith("$") and len(part) >= 2:
                emit(part[1:-1], role, math=True)
            else:
                emit(part, role)

    pos = 0
    for m in _TOKEN.finditer(text):
        if m.start() != pos:
            raise ValueError(f"unparsed caption markup at {pos}: {text!r}")
        pos = m.end()
        if m.group(1):
            emit_mixed(m.group(2), m.group(1))
        elif m.group(3) is not None:
            emit(m.group(3), None, math=True)
        elif m.group(4):
            flush()
        else:
            emit(m.group(5), None)
    if pos != len(text):
        raise ValueError(f"unparsed caption markup at {pos}: {text!r}")
    flush()
    return words


def _escape(ch):
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch)


def _markup(words, emphasis_weight):
    out = []
    for word in words:
        parts = []
        for c in word.chars:
            s = _escape(c.ch)
            if c.italic:
                s = f"<i>{s}</i>"
            if c.role:
                s = f'<span foreground="{th.ROLE_COLORS[c.role].to_hex()}" weight="{emphasis_weight}">{s}</span>'
            parts.append(s)
        out.append("".join(parts))
    return '<span font_features="liga=0,calt=0">' + " ".join(out) + "</span>"


class Caption(VGroup):
    """One caption line from the script, laid out and ready to reveal."""

    def __init__(self, line: sc.Line):
        super().__init__()
        self.line = line
        title = line.style == "title"
        if line.region == "title":
            font, size, weight = th.FONT_TITLE, th.SIZE_TITLE, th.WEIGHT_TITLE
        elif title:
            font, size, weight = th.FONT_TITLE, th.SIZE_TAKEAWAY, th.WEIGHT_TITLE
        else:
            font, size, weight = th.FONT_BODY, th.SIZE_CAPTION, th.WEIGHT_BODY
        emph_weight = "semibold"
        words = _parse(line.text)
        rows = self._wrap(words, font, size, weight, emph_weight)
        self.words = VGroup()
        self.word_specs = []
        self.glyph_info = []  # (glyph, _Char, row index) in reading order
        self.underlines = VGroup()
        text_rows = VGroup()
        for row_idx, row in enumerate(rows):
            mt = MarkupText(_markup(row, emph_weight), font=font, font_size=size, weight=weight, color=th.FG)
            n_chars = sum(len(w.chars) for w in row)
            if len(mt.submobjects) != n_chars:
                raise RuntimeError(f"{line.id}: {len(mt.submobjects)} glyphs for {n_chars} characters")
            text_rows.add(mt)
            i = 0
            for w in row:
                k = len(w.chars)
                self.words.add(VGroup(*mt.submobjects[i : i + k]))
                self.word_specs.append(w)
                self.glyph_info += [(g, c, row_idx) for g, c in zip(mt.submobjects[i : i + k], w.chars)]
                i += k
        text_rows.arrange(np.array([0.0, -1.0, 0.0]), buff=0.18)
        center_y = th.CAPTION_CENTER_Y if line.region == "band" else 2.6
        text_rows.move_to([0.0, center_y, 0.0])
        self.rows = text_rows
        self._build_underlines()
        self.add(self.words, self.underlines)

    def _wrap(self, words, font, size, weight, emph_weight):
        max_w = th.CAPTION_BAND["x1"] - th.CAPTION_BAND["x0"]
        probe = MarkupText(_markup(words, emph_weight), font=font, font_size=size, weight=weight)
        if probe.width <= max_w or len(words) < 2:
            return [words]
        lengths = np.cumsum([len(w.text) + 1 for w in words])
        split = int(np.argmin(np.abs(lengths - lengths[-1] / 2))) + 1
        return [words[:split], words[split:]]

    def _build_underlines(self):
        """One underline per run of consecutive accent glyphs of the same role (a run may span
        words, never a non-accent glyph such as trailing punctuation). The line sits below the
        row's lowest descender, so it never cuts through letters."""
        runs, current = [], []
        for g, c, row in self.glyph_info:
            if c.role and current and current[-1][1].role == c.role and current[-1][2] == row:
                current.append((g, c, row))
            else:
                if current:
                    runs.append(current)
                current = [(g, c, row)] if c.role else []
        if current:
            runs.append(current)
        row_bottom = {}
        for g, c, row in self.glyph_info:
            row_bottom[row] = min(row_bottom.get(row, np.inf), g.get_bottom()[1])
        for run in runs:
            glyphs = VGroup(*[g for g, _, _ in run])
            y = row_bottom[run[0][2]] - UNDERLINE_GAP
            ul = Line([glyphs.get_left()[0], y, 0], [glyphs.get_right()[0], y, 0])
            ul.set_stroke(th.ROLE_COLORS[run[0][1].role], width=th.UNDERLINE_WIDTH, opacity=th.UNDERLINE_OPACITY)
            self.underlines.add(ul)

    # --- animations ---------------------------------------------------------------------
    def reveal(self):
        phrase = self.line.style == "title"
        if phrase:
            chunks, cur = [], []
            for g, s in zip(self.words, self.word_specs):
                cur.append(g)
                if _PHRASE_BREAK.search(s.text):
                    chunks.append(VGroup(*cur))
                    cur = []
            if cur:
                chunks.append(VGroup(*cur))
            units, lag = chunks, 0.35
        else:
            units, lag = list(self.words), th.CAPTION_LAG
        words_anim = LaggedStart(
            *[FadeIn(u, shift=th.CAPTION_SHIFT_IN * UP, scale=0.97, rate_func=th.ENTER) for u in units],
            lag_ratio=lag,
            run_time=th.CAPTION_REVEAL,
        )
        start = 1.0 - th.UNDERLINE_TIME / th.CAPTION_REVEAL

        def late(t, start=start):
            return th.ENTER(min(max((t - start) / (1.0 - start), 0.0), 1.0))

        lines = [Create(u, rate_func=late, run_time=th.CAPTION_REVEAL) for u in self.underlines]
        return AnimationGroup(words_anim, *lines, run_time=th.CAPTION_REVEAL)

    def exit(self):
        return FadeOut(self, shift=th.CAPTION_SHIFT_OUT * UP, rate_func=th.EXIT, run_time=th.CAPTION_EXIT)

    def x_height(self):
        """Height of a flat-topped lowercase glyph (x-height), as a fraction of frame height."""
        for g, s in zip(self.words, self.word_specs):
            for gl, c in zip(g.submobjects, s.chars):
                if c.ch in "xvwzacemnorsu" and not c.italic:
                    return gl.height / th.FRAME_H
        return None


def make_scrim():
    """Stacked rectangles fading from transparent to BG at the bottom (behind captions)."""
    top, bottom = th.SCRIM_TOP, -th.FRAME_H / 2
    h = (top - bottom) / th.SCRIM_STEPS
    scrim = VGroup()
    for i in range(th.SCRIM_STEPS):
        frac = (i + 1) / th.SCRIM_STEPS  # 0 at top -> 1 at bottom
        opacity = th.SCRIM_MAX_OPACITY * frac**2
        rect = Rectangle(width=th.FRAME_W + 0.2, height=h + 0.002)
        rect.set_stroke(width=0).set_fill(th.BG, opacity=opacity)
        rect.move_to([0.0, top - (i + 0.5) * h, 0.0])
        scrim.add(rect)
    return scrim


class CaptionTrack:
    """Captions of one scene: timeline clips, fixed-in-frame registration, log, overlap check."""

    def __init__(self, scene, scene_id, check_every=1):
        self.scene = scene
        self.scene_id = scene_id
        self.fps = float(config.frame_rate)
        self.t0 = sc.scene_start_on_grid(scene_id, self.fps)  # same grid origin as Timeline
        self.captions = {line.id: Caption(line) for line in sc.lines_for(scene_id)}
        self.protected = []  # (name, mobject or callable returning mobject, is_fixed)
        self.violations = []
        self.world_flat = set()  # non-3D mobjects intentionally drawn as world objects (floor ticks)
        self.strays = {}  # description -> [first_t, last_t]
        self.observed = {cid: [] for cid in self.captions}
        self.check_every = check_every
        self._frame = 0

    def register_fixed(self):
        cam = self.scene.camera
        if hasattr(cam, "add_fixed_in_frame_mobjects"):
            for cap in self.captions.values():
                cam.add_fixed_in_frame_mobjects(cap)

    def clips(self):
        """[(local_start, animation)] for every reveal and exit in this scene."""
        out = []
        for cid, cap in self.captions.items():
            line = cap.line
            raw = line.reveal - self.t0
            reveal = clamp_local(raw, self.fps, cid)
            # a reveal clamped onto the scene's first frame moves the whole caption, so the hold
            # never drops below the reading-time rule
            out.append((reveal, cap.reveal()))
            out.append((round(line.hold_end - self.t0 + (reveal - raw), 6), cap.exit()))
        return out

    def allow_world(self, *mobs):
        """Declare non-3D mobjects that are meant to be projected as world objects."""
        for m in mobs:
            self.world_flat.update(m.get_family())

    def protect(self, name, mob, fixed, annotation=False):
        """Register a key visual that must never enter the caption band or a caption's box.

        Fixed (HUD) visuals are also kept clear of projected 3D visuals, except annotations:
        labels that deliberately sit next to the 3D geometry they name."""
        self.protected.append((name, mob, fixed, annotation))

    # --- per-frame monitoring ---------------------------------------------------------------
    def monitor(self):
        """Scene-level updater: logs caption visibility and checks overlap every frame."""

        def update(dt):
            self._frame += 1
            t_local = self.scene.renderer.time
            visible = {}
            in_scene = set(self.scene.get_mobject_family_members())
            for cid, cap in self.captions.items():
                glyphs = [gl for w in cap.words for gl in w.submobjects if gl in in_scene]
                if glyphs:
                    op = max(gl.get_fill_opacity() for gl in glyphs)
                    if op > 0.01:
                        visible[cid] = cap
                        self.observed[cid].append(round(t_local + self.t0, 4))
            if self._frame % self.check_every:
                return
            self._check_strays(in_scene, t_local + self.t0)
            band = (th.CAPTION_BAND["x0"], th.CAPTION_BAND["y0"], th.CAPTION_BAND["x1"], th.CAPTION_BAND["y1"])
            boxes = [("band", band)] + [(cid, _bbox_fixed(c.words)) for cid, c in visible.items() if c.line.region != "band"]
            t = round(t_local + self.t0, 3)
            hud, world_pts = [], []
            for name, mob, fixed, annotation in self.protected:
                m = mob() if callable(mob) else mob
                if m is None or not any(f in in_scene for f in m.get_family()):
                    continue
                if _max_opacity(m) < 0.02:
                    continue
                if fixed:
                    box = _bbox_fixed(m)
                    if not annotation:
                        hud.append((name, box))
                else:
                    pts = _projected_points(self.scene.camera, m)
                    world_pts.append((name, pts))
                    box = _bbox(pts)
                for other, obox in boxes:
                    if _intersects(box, obox):
                        self.violations.append(dict(t=t, visual=name, with_=other))
            # 3D visuals must not run into fixed overlays (formula, tags, panels): any projected
            # outline point inside an overlay's box is a collision.
            for name, pts in world_pts:
                for hname, (x0, y0, x1, y1) in hud:
                    inside = (pts[:, 0] > x0) & (pts[:, 0] < x1) & (pts[:, 1] > y0) & (pts[:, 1] < y1)
                    if inside.any():
                        self.violations.append(dict(t=t, visual=name, with_=hname))

        return update

    def _check_strays(self, in_scene, t):
        """Visible non-3D VMobjects in a 3D scene that are neither fixed-in-frame, fixed-orientation
        nor declared world-flat: e.g. copies put on screen by FadeTransform. They render projected."""
        cam = self.scene.camera
        if not hasattr(cam, "fixed_in_frame_mobjects"):
            return
        fixed = cam.fixed_in_frame_mobjects
        if hasattr(cam, "fixed_roots"):  # RigCamera re-derives this set at capture time
            fixed = set(extract_mobject_family_members(cam.fixed_roots))
        for m in in_scene:
            if not isinstance(m, VMobject) or getattr(m, "shade_in_3d", False) or not m.has_points():
                continue
            if m in fixed or m in cam.fixed_orientation_mobjects or m in self.world_flat:
                continue
            if max(m.get_fill_opacity(), m.get_stroke_opacity() if m.get_stroke_width() > 0 else 0.0) < 0.02:
                continue
            key = f"{type(m).__name__}#{id(m):x}"
            if key not in self.strays:
                self.strays[key] = [round(t, 3), round(t, 3), np.round(m.get_center(), 2).tolist()]
            self.strays[key][1] = round(t, 3)

    def write_log(self, path=None):
        path = path or os.path.join("out", "captions", f"{self.scene_id}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entries = []
        for cid, cap in self.captions.items():
            seen = self.observed[cid]
            line = cap.line
            entries.append(
                dict(
                    id=cid,
                    planned_reveal=line.reveal,
                    planned_hold_end=line.hold_end,
                    planned_exit_end=line.exit_end,
                    first_visible=seen[0] if seen else None,
                    last_visible=seen[-1] if seen else None,
                    x_height=cap.x_height(),
                    bbox=_bbox_fixed(cap.words),
                )
            )
        with open(path, "w") as f:
            json.dump(dict(scene=self.scene_id, captions=entries, violations=self.violations, strays=self.strays), f, indent=2)
        return path


def _max_opacity(mob):
    ops = [m.get_fill_opacity() for m in mob.get_family() if m.has_points()]
    ops += [m.get_stroke_opacity() for m in mob.get_family() if m.has_points() and m.get_stroke_width() > 0]
    return max(ops, default=0.0)


def _leaf_points(mob):
    """All points of a mobject's family in one concatenate (Mobject.get_all_points builds the
    array with repeated np.append: ~200 ms for the 4704-face sheet). LiveSurface supplies its
    own small outline instead."""
    if hasattr(mob, "outline_points"):
        return mob.outline_points()
    leaves = [m.points for m in mob.get_family() if m.has_points()]
    return np.concatenate(leaves) if leaves else np.zeros((0, 3))


def _bbox(pts):
    if len(pts) == 0:
        return (0.0, 0.0, 0.0, 0.0)
    return (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))


def _bbox_fixed(mob):
    return _bbox(_leaf_points(mob))


def _projected_points(camera, mob):
    pts = _leaf_points(mob)
    if len(pts) and hasattr(camera, "screen_points"):
        pts = camera.screen_points(pts)  # fresh rotation (project_points is a frame stale here)
    elif len(pts) and hasattr(camera, "project_points"):
        camera.reset_rotation_matrix()
        pts = camera.project_points(pts)
    return pts


def _bbox_projected(camera, mob):
    return _bbox(_projected_points(camera, mob))


def _intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
