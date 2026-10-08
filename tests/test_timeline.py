"""Scene spans tile the film's global frame grid exactly (no drift across cuts)."""

import pytest

from rubber_sheet import script as sc


@pytest.mark.parametrize("fps", [15, 30, 60])
def test_scene_frames_tile_the_film(fps):
    expected_first = 0
    for scene in sc.SCENES:
        first, n = sc.scene_frames(scene, fps)
        assert first == expected_first and n > 0
        expected_first = first + n
    assert expected_first == round(sc.FILM_END * fps)


@pytest.mark.parametrize("fps", [15, 60])
def test_grid_start_within_half_a_frame_of_cut(fps):
    for scene, (t0, _) in sc.SCENES.items():
        assert abs(sc.scene_start_on_grid(scene, fps) - t0) <= 0.5 / fps + 1e-12


@pytest.mark.parametrize("fps", [15, 60])
def test_caption_clips_need_at_most_one_frame_of_clamping(fps):
    for line in sc.LINES:
        t0 = sc.scene_start_on_grid(line.scene, fps)
        assert line.reveal - t0 >= -1.0 / fps
