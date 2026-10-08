"""Every built film scene, played for real (dry run: no files; 5 fps, 480x270, preview mesh) with
its own CaptionTrack monitor attached. Asserts, for the whole scene:
  - no protected visual enters the caption band or a title caption, and no 3D visual runs into a
    fixed overlay (formula, tags, panels, probe, disclosure)
  - no stray unregistered mobject is drawn (e.g. a copy left on screen by a transform)
  - every caption is first/last visible exactly on the frames the film grid gives it and stays on
    screen at least reveal + hold
This is the render-time guard (tools/check_captions.py on real renders) as a regular test, so a
scene is never 'done' without it. ~5-8 s per scene.
"""

import importlib

import pytest
from manim import tempconfig

from rubber_sheet import captions
from rubber_sheet import script as sc
from rubber_sheet import theme as th

FPS = 5
SCENES = [
    ("S3", "s03_poles_sheet", "S3PolesSheet"),
    ("S4", "s04_slice_bode", "S4SliceBode"),
    ("S5", "s05_zero_nail", "S5ZeroNail"),
    ("S6", "s06_sweep", "S6Sweep"),
]


@pytest.fixture(scope="module", params=SCENES, ids=[s[0] for s in SCENES])
def played(request, tmp_path_factory):
    scene_id, module, cls = request.param
    mp = pytest.MonkeyPatch()
    mp.setenv("RS_NO_LOG", "1")  # never overwrite out/captions from a test
    media = tmp_path_factory.mktemp(f"media_{scene_id}")
    cfg = {"frame_rate": FPS, "pixel_width": 480, "pixel_height": 270, "dry_run": True, "disable_caching": True,
           "media_dir": str(media), "progress_bar": "none", "verbosity": "ERROR", "background_color": th.BG}
    try:
        with tempconfig(cfg):
            scene = getattr(importlib.import_module(f"scenes.{module}"), cls)()
            scene.render()
    finally:
        mp.undo()
    return scene_id, scene.caption_track


def test_no_overlap_violations(played):
    scene_id, track = played
    by = {}
    for v in track.violations:
        by.setdefault((v["visual"], v["with_"]), []).append(v["t"])
    assert not by, {k: (ts[0], ts[-1], len(ts)) for k, ts in by.items()}


def test_no_stray_unregistered_mobjects(played):
    _, track = played
    assert not track.strays, track.strays


def test_caption_frames_on_the_film_grid(played):
    scene_id, track = played
    assert set(track.observed) == {line.id for line in sc.lines_for(scene_id)}
    for cid, seen in track.observed.items():
        problems = captions.timing_problems(sc.BY_ID[cid], scene_id, FPS, seen[0] if seen else None, seen[-1] if seen else None)
        assert not problems, (cid, problems)
