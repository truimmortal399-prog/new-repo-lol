"""Caption script and scene boundaries: the single source of on-screen copy and caption timing.

Markup inside `text`:
  $...$          inline math token (counts as 2 words)
  {ROLE:...}     emphasis in an accent role (POLE, ZERO, SIGNAL); may wrap words or math
All times are film times in seconds. No manim import (tests read this cheaply).
"""

import math
import re
from dataclasses import dataclass

WORDS_PER_SECOND = 3.33  # 200 wpm
HOLD_BASE = 0.5
MATH_TOKEN_WORDS = 2
REVEAL = 0.8
EXIT = 0.4
MAX_FILM = 78.0

# Scene cuts (start, end). Captions never cross a cut (tests/test_captions.py).
SCENES = {
    "S1": (0.0, 6.62),
    "S2": (6.62, 11.6),
    "S3": (11.6, 25.0),
    "S4": (25.0, 35.72),
    "S5": (35.72, 48.31),
    "S6": (48.31, 61.0),
    "S7": (61.0, 76.0),
}
FILM_END = 76.0

ROLES = ("POLE", "ZERO", "SIGNAL")
_EMPH = re.compile(r"\{(POLE|ZERO|SIGNAL):([^{}]*)\}")
_MATH = re.compile(r"\$[^$]*\$")


@dataclass(frozen=True)
class Line:
    id: str
    scene: str
    text: str
    n: int  # reading-time word count (math token = 2)
    reveal: float  # reveal start
    hold: float  # hold length
    region: str = "band"  # "band" (caption band) or "title" (upper third)
    style: str = "body"  # "body" or "title"
    continuation: bool = False  # may reveal at the previous caption's hold end

    @property
    def reveal_end(self):
        return self.reveal + REVEAL

    @property
    def hold_end(self):
        return self.reveal_end + self.hold

    @property
    def exit_end(self):
        return self.hold_end + EXIT


def plain_text(text):
    """Strip emphasis markup, keep math tokens."""
    return _EMPH.sub(lambda m: m.group(2), text)


def word_count(text):
    plain = plain_text(text)
    n_math = len(_MATH.findall(plain))
    rest = _MATH.sub(" ", plain)
    n_words = sum(1 for tok in rest.split() if re.search(r"\w", tok))
    return n_words + MATH_TOKEN_WORDS * n_math


def required_hold(n):
    """hold = 0.5 + n / 3.33, rounded up to 0.01 s."""
    return math.ceil((HOLD_BASE + n / WORDS_PER_SECOND) * 100 - 1e-9) / 100


LINES = [
    Line("C1", "S1", "Two invisible {POLE:points} decide how a circuit {SIGNAL:rings}.", 8, 0.30, 2.91),
    Line("T", "S1", "The Rubber Sheet", 3, 4.01, 1.41, region="title", style="title"),
    Line("C2", "S2", "An RLC circuit and its transfer function.", 7, 6.80, 2.61),
    Line("C3", "S3", "Where $H$ blows up: the {POLE:poles}.", 7, 12.00, 2.61),
    Line("C4", "S3", "Lift the gain above every point $s$.", 8, 16.40, 2.91),
    Line("C5", "S3", "Each pole is a {POLE:tent pole}.", 6, 21.20, 2.31),
    Line("C6", "S4", r"Slice along the {SIGNAL:$j\omega$} axis…", 6, 25.20, 2.31),
    Line("C7", "S4", "…the edge is the {SIGNAL:frequency response}.", 6, 29.40, 2.31),
    Line("C8", "S4", "Log frequency: a {SIGNAL:Bode plot}.", 5, 32.51, 2.01, continuation=True),
    Line("C9", "S5", "Probe the resistor: a {ZERO:zero} appears.", 6, 36.40, 2.31),
    Line("C10", "S5", "A zero {ZERO:nails} the sheet down.", 6, 40.40, 2.31),
    Line("C11", "S5", "Back to the capacitor.", 4, 45.40, 1.71),
    Line("C12", "S6", "Now lower $R$.", 4, 48.31, 1.71),
    Line("C13", "S6", "{POLE:Poles} creep toward the axis…", 5, 51.50, 2.01),
    Line("C14", "S6", "…sharper {SIGNAL:peak}, longer {SIGNAL:ringing}.", 4, 56.00, 1.71),
    Line("C15", "S7", "$R = 0$: poles on the axis.", 6, 61.20, 2.31),
    Line("C16", "S7", "{POLE:Infinite} peak. Ringing that {SIGNAL:never stops}.", 6, 65.11, 2.31),
    Line("C17", "S7", "Nearer the axis, {SIGNAL:longer the ring}.", 6, 69.20, 3.80, style="title"),
]

BY_ID = {line.id: line for line in LINES}


def lines_for(scene):
    return [line for line in LINES if line.scene == scene]


def local_time(line_time, scene):
    """Film time -> time relative to the scene's start."""
    return line_time - SCENES[scene][0]
