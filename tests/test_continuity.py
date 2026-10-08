"""Continuity across every cut between built scenes, without a full render: the last frame of
scene A and the first frame of scene B (adjacent frames on the 60 fps film grid) are drawn at
480x270 with the preview mesh (RS_STILL_AT, dry run) and compared like tools/check_continuity.py:
mean difference < 1.5 % and no 8x8 block jumping > 8 % (a pop: something appearing or vanishing at
the cut — e.g. a panel's curve drawn before its panel fades in, S5|S6 at Gate 4).
"""

import importlib

import numpy as np
import pytest
from manim import tempconfig

from rubber_sheet import script as sc
from rubber_sheet import theme as th

FPS = 60
BUILT = [("S3", "s03_poles_sheet", "S3PolesSheet"), ("S4", "s04_slice_bode", "S4SliceBode"),
         ("S5", "s05_zero_nail", "S5ZeroNail"), ("S6", "s06_sweep", "S6Sweep")]


def frame_at(module, cls, t, tmp_path, monkeypatch):
    monkeypatch.setenv("RS_STILL_AT", repr(t))
    monkeypatch.setenv("RS_NO_LOG", "1")
    # background_color explicitly: th.configure() runs once at a scene module's first import and
    # tempconfig reverts it, so a module imported by an earlier test would render on black
    cfg = {"frame_rate": FPS, "pixel_width": 480, "pixel_height": 270, "dry_run": True, "disable_caching": True,
           "media_dir": str(tmp_path), "progress_bar": "none", "verbosity": "ERROR", "background_color": th.BG}
    with tempconfig(cfg):
        scene = getattr(importlib.import_module(f"scenes.{module}"), cls)()
        scene.render()
        return scene.renderer.camera.pixel_array[..., :3].astype(np.float32).copy()


@pytest.mark.parametrize("a,b", list(zip(BUILT, BUILT[1:])), ids=[f"{a[0]}|{b[0]}" for a, b in zip(BUILT, BUILT[1:])])
def test_cut_is_continuous(a, b, tmp_path, monkeypatch):
    first_b, _ = sc.scene_frames(b[0], FPS)
    last_a = (first_b - 1) / FPS  # the frame before the cut on the film grid
    fa = frame_at(a[1], a[2], last_a, tmp_path, monkeypatch)
    fb = frame_at(b[1], b[2], first_b / FPS, tmp_path, monkeypatch)
    d = np.abs(fb - fa)
    mean_pct = d.mean() / 255 * 100
    k = 8
    h, w = d.shape[0] // k, d.shape[1] // k
    blocks = d[: h * k, : w * k].reshape(h, k, w, k, 3).mean(axis=(1, 3, 4))
    jump = blocks.max() / 255 * 100
    assert mean_pct < 1.5 and jump < 8.0, (mean_pct, jump, np.unravel_index(blocks.argmax(), blocks.shape))
