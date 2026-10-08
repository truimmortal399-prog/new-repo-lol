"""Caption script obeys the reading-time and sequencing rules by construction."""

import pytest

from rubber_sheet import script as sc

EPS = 1e-6
BAND = [line for line in sc.LINES if line.region == "band"]


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_word_count_matches_text(line):
    assert sc.word_count(line.text) == line.n


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_hold_meets_reading_rule(line):
    assert line.hold + EPS >= sc.required_hold(line.n)


def test_hold_values_from_plan():
    assert [sc.required_hold(n) for n in (3, 4, 5, 6, 7, 8)] == [1.41, 1.71, 2.01, 2.31, 2.61, 2.91]


def test_math_tokens_count_double():
    assert sc.word_count("Lift the gain above every point $s$.") == 8
    assert sc.word_count("$R = 0$: poles on the axis.") == 6
    assert sc.word_count(r"Slice along the {SIGNAL:$j\omega$} axis…") == 6


def test_lines_sorted_by_reveal():
    reveals = [line.reveal for line in sc.LINES]
    assert reveals == sorted(reveals)


def test_band_sequencing():
    """Same band: reveal >= previous exit end, except flagged continuations (>= previous hold end)."""
    for prev, nxt in zip(BAND, BAND[1:]):
        bound = prev.hold_end if nxt.continuation else prev.exit_end
        assert nxt.reveal + EPS >= bound, (prev.id, nxt.id, nxt.reveal, bound)


def test_only_c7_c8_is_a_continuation_pair():
    flagged = [line.id for line in sc.LINES if line.continuation]
    assert flagged == ["C8"]
    idx = [l.id for l in BAND].index("C8")
    assert BAND[idx - 1].id == "C7"


def test_title_region_does_not_overlap_band_text_while_revealing():
    t = sc.BY_ID["T"]
    c1 = sc.BY_ID["C1"]
    assert t.reveal + EPS >= c1.hold_end


def test_scenes_are_contiguous_and_within_budget():
    spans = list(sc.SCENES.values())
    assert spans[0][0] == 0.0
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert a1 == b0 and a0 < a1 < b1
    assert spans[-1][1] == sc.FILM_END <= sc.MAX_FILM


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_caption_inside_its_scene(line):
    start, end = sc.SCENES[line.scene]
    assert start - EPS <= line.reveal and line.exit_end <= end + EPS, (line.id, line.reveal, line.exit_end, start, end)


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_no_caption_crosses_a_scene_cut(line):
    cuts = [span[1] for span in sc.SCENES.values()][:-1]
    for cut in cuts:
        assert not (line.reveal + EPS < cut < line.exit_end - EPS), (line.id, cut)


def test_last_caption_ends_before_film_end():
    assert max(line.exit_end for line in sc.LINES) <= sc.FILM_END + EPS
