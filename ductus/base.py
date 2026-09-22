"""The data model: where a finding lives, what it claims, and how much it weighs.

Four types, and they are the whole contract every other module speaks in.

A :class:`Span` says *where*. It carries character offsets **and** the W3C Web
Annotation redundant selectors (quote, prefix, suffix) so a finding can be
re-anchored after the text is edited, which plain offsets cannot survive.

A :class:`Signal` is one piece of evidence: a direction, a weight, who produced
it, and a human-readable reason. Signals are never merged or averaged away --
the reason a passage scored the way it did is always recoverable.

A :class:`Segment` is a unit of text plus the signals that landed on it and the
lean derived from them. A :class:`Report` is the document-level roll-up.

>>> text = "The cat sat. It was a fine evening."
>>> span = Span.of(text, 4, 7)
>>> span.quote, span.prefix
('cat', 'The ')
>>> Signal("test", "machine", 0.5, "demo", note="an example").direction
'machine'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "DIRECTIONS",
    "LABELS",
    "SCHEMA_VERSION",
    "Report",
    "Segment",
    "Signal",
    "Span",
]

#: Bumped when the serialized shape of a Report changes incompatibly.
SCHEMA_VERSION = "1"

#: What a signal can argue for. ``neutral`` records evidence that is real but
#: does not discriminate -- it is kept because hiding it would be dishonest.
DIRECTIONS = ("machine", "human", "neutral")

#: The coarse vocabulary a segment is labelled with. Deliberately not a
#: percentage: see ``docs/why-no-percentage.md``.
LABELS = ("leans-machine", "leans-human", "mixed-signals", "uncertain", "no-evidence")

#: How much text on each side of a span is kept for re-anchoring.
CONTEXT_CHARS = 40


@dataclass(frozen=True)
class Span:
    """A character range, with redundant selectors so it survives an edit.

    Offsets count **code points** (Python ``str`` indices), not bytes and not
    UTF-16 units -- a JavaScript client must convert after any astral character.

    ``start``/``end`` are a ``TextPositionSelector``; ``quote`` with ``prefix``
    and ``suffix`` is a ``TextQuoteSelector``. Keeping both is what lets a
    viewer re-find a finding after the text around it changed.

    >>> s = Span.of("one two three", 4, 7, level="sentence")
    >>> (s.start, s.end, s.quote, s.level)
    (4, 7, 'two', 'sentence')
    >>> s.length
    3
    """

    start: int
    end: int
    quote: str
    prefix: str = ""
    suffix: str = ""
    level: str = "segment"

    @classmethod
    def of(cls, text: str, start: int, end: int, *, level: str = "segment") -> Span:
        """Build a span over ``text``, capturing its re-anchoring context.

        >>> Span.of("abcdef", 2, 4).suffix
        'ef'
        """
        return cls(
            start=start,
            end=end,
            quote=text[start:end],
            prefix=text[max(0, start - CONTEXT_CHARS) : start],
            suffix=text[end : end + CONTEXT_CHARS],
            level=level,
        )

    @property
    def length(self) -> int:
        return self.end - self.start

    def contains(self, other: Span) -> bool:
        """Whether ``other`` falls entirely inside this span.

        >>> a, b = Span.of("abcdef", 0, 6), Span.of("abcdef", 2, 4)
        >>> a.contains(b), b.contains(a)
        (True, False)
        """
        return self.start <= other.start and other.end <= self.end


@dataclass(frozen=True)
class Signal:
    """One piece of evidence about one span.

    ``weight`` is how much this moves the needle, in ``0..1``. It is a weight,
    not a probability: two 0.5 signals pointing the same way are stronger than
    one, and nothing here claims to be calibrated.

    >>> Signal("em-dash", "machine", 0.2, "forensic", value=3).name
    'em-dash'
    """

    name: str
    direction: str
    weight: float
    detector: str
    value: Any = None
    note: str = ""
    span: Span | None = None

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            raise ValueError(
                f"direction must be one of {DIRECTIONS}, got {self.direction!r}"
            )
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"weight must be in [0, 1], got {self.weight!r}")


@dataclass(frozen=True)
class Segment:
    """A unit of text, the signals on it, and the lean they add up to.

    ``lean`` runs from -1 (every signal argues human) to +1 (every signal argues
    machine). ``strength`` is how much evidence there is at all -- a lean of
    +1.0 from a single weak signal is not the same claim as +1.0 from six.
    """

    span: Span
    signals: tuple[Signal, ...] = ()
    lean: float = 0.0
    strength: float = 0.0
    label: str = "no-evidence"


@dataclass(frozen=True)
class Report:
    """Everything a downstream consumer needs, and nothing it has to guess at."""

    text_sha256: str
    n_chars: int
    document: Segment
    segments: tuple[Segment, ...]
    detectors: tuple[str, ...]
    segmenter: str
    schema_version: str = SCHEMA_VERSION
    calibration: str = "uncalibrated"
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def signals(self) -> tuple[Signal, ...]:
        """Every signal in the report, in document order."""
        return tuple(s for seg in self.segments for s in seg.signals)
