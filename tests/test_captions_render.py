"""Every script line builds as a Caption: 1:1 glyph mapping, no raw TeX on screen, legible,
inside its region and title-safe; emphasis underlines cover accent glyphs only."""

import pytest

from rubber_sheet import captions
from rubber_sheet import script as sc
from rubber_sheet import theme as th


@pytest.fixture(scope="module")
def built():
    return {line.id: captions.Caption(line) for line in sc.LINES}


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_no_raw_tex_and_glyphs_match(built, line):
    cap = built[line.id]
    text = "".join(c.ch for _, c, _ in cap.glyph_info)
    assert "\\" not in text and "$" not in text and "{" not in text
    assert len(cap.glyph_info) == sum(len(w.chars) for w in cap.word_specs)


def test_c6_shows_omega(built):
    text = "".join(c.ch for _, c, _ in built["C6"].glyph_info)
    assert "jω" in text


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_legible_and_inside_region(built, line):
    cap = built[line.id]
    xh = cap.x_height()
    assert xh is None or xh >= th.MIN_CAPTION_XHEIGHT
    x0, y0, x1, y1 = captions._bbox_fixed(cap)
    assert -th.SAFE_X <= x0 and x1 <= th.SAFE_X
    if line.region == "band":
        band = th.CAPTION_BAND
        assert band["y0"] <= y0 and y1 <= band["y1"], (line.id, y0, y1)
    else:
        assert y1 <= th.SAFE_Y and y0 >= th.CAPTION_BAND["y1"]


@pytest.mark.parametrize("line", sc.LINES, ids=lambda l: l.id)
def test_underlines_cover_only_accent_glyphs(built, line):
    cap = built[line.id]
    accents = [g for g, c, _ in cap.glyph_info if c.role]
    plain = [g for g, c, _ in cap.glyph_info if not c.role]
    assert (len(cap.underlines) > 0) == (len(accents) > 0)
    for ul in cap.underlines:
        lo, hi = ul.get_left()[0], ul.get_right()[0]
        for g in plain:  # no plain glyph (e.g. trailing punctuation) sits fully under a line
            assert not (g.get_left()[0] >= lo - 1e-6 and g.get_right()[0] <= hi + 1e-6 and abs(g.get_center()[1] - ul.get_center()[1]) < 0.6)
        # the line is below every glyph of its row (never cuts a descender)
        assert ul.get_center()[1] < min(g.get_bottom()[1] for g, _, _ in cap.glyph_info)
