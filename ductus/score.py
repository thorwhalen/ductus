"""Turning evidence into a lean -- the ``aggregate=`` seam.

The deliberate design choice of this package lives here: **there is no
percentage**. Every commercial detector emits a number like "87% AI", and that
number is how people get falsely accused, because it reads as a calibrated
probability and is nothing of the kind.

What comes out instead is three things a reader can argue with:

``lean``
    -1 (all evidence argues human) to +1 (all evidence argues machine). It is a
    ratio of the weights present, not a probability of anything.
``strength``
    0 to 1: how much evidence there was at all. A lean of +1.0 from one weak
    signal is a different claim from +1.0 from six, and collapsing those into
    one number is exactly the lie this module refuses to tell.
``label``
    One of :data:`ductus.base.LABELS`, and never finer than the evidence.

Replacing this with a scorer calibrated on labelled data is one keyword
argument; see ``misc/docs/roadmap.md``.

>>> from ductus.base import Signal
>>> aggregate([Signal("a", "machine", 0.5, "d"), Signal("b", "machine", 0.4, "d")])
(1.0, 0.6, 'leans-machine')
>>> aggregate([Signal("a", "machine", 0.5, "d"), Signal("b", "human", 0.5, "d")])
(0.0, 0.667, 'mixed-signals')
>>> aggregate([])
(0.0, 0.0, 'no-evidence')
"""

from __future__ import annotations

from collections.abc import Sequence

from ductus.base import Signal

__all__ = ["EVIDENCE_FULL", "LEAN_THRESHOLD", "STRENGTH_FLOOR", "aggregate"]

#: Beyond this, a segment is called as leaning one way.
LEAN_THRESHOLD = 0.45
#: Below this much total evidence, no label is claimed at all.
STRENGTH_FLOOR = 0.20
#: The total signal weight at which ``strength`` saturates at 1.0. Not fitted --
#: it is "about three moderate signals", chosen to be legible rather than exact.
EVIDENCE_FULL = 1.5


def aggregate(signals: Sequence[Signal]) -> tuple[float, float, str]:
    """Reduce evidence to ``(lean, strength, label)``.

    Neutral signals count toward ``strength`` but never toward ``lean`` -- they
    are real evidence that the passage is unusual without being evidence about
    who wrote it.

    >>> from ductus.base import Signal
    >>> aggregate([Signal("x", "human", 0.6, "d")])
    (-1.0, 0.4, 'leans-human')
    >>> aggregate([Signal("x", "neutral", 0.9, "d")])
    (0.0, 0.6, 'uncertain')
    """
    if not signals:
        return 0.0, 0.0, "no-evidence"

    machine = sum(s.weight for s in signals if s.direction == "machine")
    human = sum(s.weight for s in signals if s.direction == "human")
    neutral = sum(s.weight for s in signals if s.direction == "neutral")

    directional = machine + human
    total = directional + neutral
    if total == 0:
        return 0.0, 0.0, "no-evidence"

    lean = round((machine - human) / directional, 3) if directional else 0.0
    strength = round(min(total / EVIDENCE_FULL, 1.0), 3)

    if strength < STRENGTH_FLOOR:
        return lean, strength, "no-evidence"
    if lean >= LEAN_THRESHOLD:
        label = "leans-machine"
    elif lean <= -LEAN_THRESHOLD:
        label = "leans-human"
    elif machine > 0 and human > 0:
        label = "mixed-signals"
    else:
        label = "uncertain"
    return lean, strength, label
