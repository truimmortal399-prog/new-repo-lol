"""Gate 1 environment smoke test: LaTeX (MathTex) and font resolution (Pango).

Run:  .venv/bin/manim -ql -s tools/smoke_test.py SmokeTest
Then: .venv/bin/python tools/smoke_test.py      (font fallback check, exits non-zero on failure)
"""

import sys

import manimpango
from manim import DOWN, LEFT, MathTex, Scene, Text, VGroup

REQUIRED_FAMILIES = ["Inter", "Inter Display"]
FALLBACK = "DejaVu Sans"
PROBE = "Hamburgefontsiv"
VARIANTS = [
    ("Inter", "NORMAL"),
    ("Inter", "SEMIBOLD"),
    ("Inter Display", "SEMIBOLD"),
]


class SmokeTest(Scene):
    def construct(self):
        tex = MathTex(
            r"H(s)=\frac{1}{LCs^2+RCs+1},\quad \lvert H(j\omega)\rvert,\quad s=-\zeta\omega_0\pm j\omega_0\sqrt{1-\zeta^2}",
            font_size=36,
        )
        rows = [Text(f"{fam} {w}: {PROBE}", font=fam, weight=w, font_size=36) for fam, w in VARIANTS]
        rows.append(Text(f"{FALLBACK} (reference): {PROBE}", font=FALLBACK, font_size=36))
        group = VGroup(tex, *rows).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        self.add(group)


def font_check() -> bool:
    families = set(manimpango.list_fonts())
    ok = True
    for fam in REQUIRED_FAMILIES:
        present = fam in families
        print(f"list_fonts contains {fam!r}: {present}")
        ok &= present
    ref = Text(PROBE, font=FALLBACK, font_size=48).width
    print(f"width {FALLBACK:>14} NORMAL   : {ref:.4f}")
    for fam, w in VARIANTS:
        width = Text(PROBE, font=fam, weight=w, font_size=48).width
        distinct = abs(width - ref) > 1e-3
        print(f"width {fam:>14} {w:<9}: {width:.4f}  differs from fallback: {distinct}")
        ok &= distinct
    # Regular vs SemiBold must differ too, otherwise the weight was ignored.
    reg = Text(PROBE, font="Inter", weight="NORMAL", font_size=48).width
    semi = Text(PROBE, font="Inter", weight="SEMIBOLD", font_size=48).width
    print(f"Inter NORMAL vs SEMIBOLD widths differ: {abs(reg - semi) > 1e-3}")
    ok &= abs(reg - semi) > 1e-3
    return ok


if __name__ == "__main__":
    passed = font_check()
    print("FONT CHECK:", "PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)
