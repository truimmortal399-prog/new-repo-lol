"""Declarative scene timeline: clips at exact film times, played as one AnimationGroup.

Mechanics (Manim CE 0.22, verified):
- Each clip runs as Succession(Wait(offset), [EnsureIn(mob)], animation). Succession sets up its
  later animations lazily, so introducers (FadeIn, Create, Write, ...) add their mobject only
  when their clip starts.
- The outer AnimationGroup gets an explicit empty `group`. Otherwise AnimationGroup collects the
  mobjects of every non-introducer clip (FadeOut, Transform, .animate) and Scene.play adds them
  all at t = 0, i.e. before their reveal. Non-introducer clips are instead preceded by EnsureIn,
  which adds their mobject at the clip's own start time if it is not already in the scene.
- A driver mobject with a no-op updater sits at the back of the scene, so every mobject counts
  as moving and is redrawn each frame (no static-frame caching, which would freeze 3D content
  during camera moves and lose depth order between static and moving mobjects).
"""

import os

from manim import AnimationGroup, Group, Succession, VectorizedPoint, Wait, config
from manim.animation.animation import Animation, prepare_animation

from rubber_sheet import script as sc


class EnsureIn(Animation):
    """Zero-length step: add `mobject` to the scene when reached, unless already there."""

    def __init__(self, mobject):
        super().__init__(mobject, run_time=0.0)

    def _setup_scene(self, scene):
        super()._setup_scene(scene)
        if scene is not None and self.mobject not in scene.get_mobject_family_members():
            scene.add(self.mobject)

    def interpolate_mobject(self, alpha):
        pass


def clamp_local(local, fps, what):
    """A clip at a cut may sit < 1 frame before the grid-rounded scene start: start it on frame 0."""
    if local < -1.0 / fps - 1e-9:
        raise ValueError(f"{what} precedes the scene start by more than a frame")
    return max(round(local, 6), 0.0)


class Timeline:
    """Local time 0 is the scene's first frame on the global grid (script.scene_frames), so frame j
    of this scene shows film time t0 + j / fps exactly; clips are placed in that local time."""

    def __init__(self, scene_id, fps=None):
        self.scene_id = scene_id
        self.fps = float(fps or config.frame_rate)
        first, self.n_frames = sc.scene_frames(scene_id, self.fps)
        self.t0 = first / self.fps
        self.t1 = sc.SCENES[scene_id][1]
        self.clips = []  # (local_start, animation)

    @property
    def duration(self):
        """Run time that makes play() emit exactly n_frames frames (play emits ceil(rt * fps))."""
        return (self.n_frames - 0.5) / self.fps

    def at(self, t_film, *animations):
        """Schedule animations starting at film time t_film."""
        local = clamp_local(t_film - self.t0, self.fps, f"{self.scene_id}: clip at {t_film}")
        for anim in animations:
            self.clips.append((local, prepare_animation(anim)))
        return self

    def extend(self, local_clips):
        for local, anim in local_clips:
            self.clips.append((local, prepare_animation(anim)))
        return self

    def build(self, run_time=None):
        """run_time: play only the first run_time seconds (still frames, RS_STILL_AT); clips keep
        their scene-time positions."""
        run_time = self.duration if run_time is None else run_time
        parts = []
        for local, anim in self.clips:
            end = local + anim.get_run_time()
            # A clip may end on the true cut even when the grid-rounded last frame precedes it
            # (e.g. a caption exit ending at 6.62 when the cut rounds down to frame 397 at 60 fps).
            if end > (self.t1 - self.t0) + 1.0 / self.fps + 1e-6:
                raise ValueError(f"{self.scene_id}: clip ends at {end + self.t0:.3f} after scene end {self.t1}")
            steps = [] if local <= 1e-9 else [Wait(local)]
            if not anim.is_introducer() and anim.mobject is not None:
                steps.append(EnsureIn(anim.mobject))
            steps.append(anim)
            parts.append(Succession(*steps))
        parts.append(Wait(self.duration))
        # AnimationGroup runs its clock as rate_func(alpha) * (latest clip end). A clip may end up to
        # one frame after the last rendered frame (above), which would make that clock run fast by
        # the ratio and start every clip early (S4: C8's exit ends on the cut, 8 ms drift by 29.4).
        # This rate function pins the group clock to scene time exactly.
        latest = max(local + anim.get_run_time() for local, anim in self.clips) if self.clips else 0.0
        scale = run_time / max(self.duration, latest)
        return AnimationGroup(*parts, group=Group(), run_time=run_time, rate_func=lambda a: a * scale)

    def play(self, scene):
        driver = VectorizedPoint()
        driver.add_updater(lambda m, dt: None)
        scene.add(driver)
        scene.bring_to_back(driver)
        # RS_STILL_AT=<film time> (tools/still.py): run every frame up to that time but draw only the
        # last one, so the movie holds exactly that frame. (manim -s cannot do this: it skips to
        # the end of the play and finishes every clip.)
        # RS_SPAN=<t0>:<t1> (film times): the same, drawing only the frames in [t0, t1] (exact
        # per-frame timing of a slice of real content, tools/time_scenes.py).
        still, span = os.environ.get("RS_STILL_AT"), os.environ.get("RS_SPAN")
        if still is None and span is None:
            scene.play(self.build())
            return
        a, b = (float(still), float(still)) if still is not None else (float(x) for x in span.split(":"))
        lo, hi = (round((t - self.t0) * self.fps) / self.fps for t in (a, b))
        draw = scene.renderer.render
        eps = 0.25 / self.fps
        scene.renderer.render = lambda sc, t, moving: draw(sc, t, moving) if lo - eps <= t <= hi + eps else None
        scene.play(self.build(hi + 0.5 / self.fps))
