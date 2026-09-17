"""The core: stream segments, or take the whole report. Everything else is a surface.

Two entry points, and the second is a facade over the first:

:func:`iter_segments` yields one :class:`~ductus.base.Segment` at a time as it
scores them -- the streaming surface, for long documents and for a UI that wants
to paint as results arrive.

:func:`gauge` collects them into a :class:`~ductus.base.Report`.

The three seams are keyword arguments, each defaulting to something that
genuinely works rather than to a stub. The ``aggregate=`` default normalises evidence
by how much text produced it; the length-blind :func:`ductus.score.aggregate` is still
there, and ``misc/docs/phase-2-results.md`` has the measurement that chose between
them -- on human-written text the length-blind scorer's false-accusation rate ran from
11% to 74% with document length alone.

===============  ==========================================  ==========================
seam             v1 default                                  swap in
===============  ==========================================  ==========================
``segmenter=``   ``"paragraph"``                             ``"sentence"``, a callable
``detectors=``   all four deterministic detectors            a model-based detector
``aggregate=``   :func:`ductus.score.density_aggregate`      :func:`ductus.score.aggregate`
===============  ==========================================  ==========================

``extra_signals=`` is not a seam but an input: evidence produced elsewhere --
by an agent reading the text, by a vendor API -- attached to the segment that
contains it. It is how the shipped skills feed a model's reading back in.

>>> report = gauge("Great question! Let's delve into this robust tapestry.")
>>> report.document.label
'leans-machine'
>>> report = gauge("Sent the export Friday. Two sites, not five. Call if it breaks.")
>>> report.document.label
'no-evidence'
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Iterator, Sequence

from ductus.base import Report, Segment, Signal, Span
from ductus.detect import detectors_from
from ductus.score import density_aggregate as default_aggregate
from ductus.segment import spans_of

__all__ = ["gauge", "iter_segments"]

#: The ``aggregate=`` seam. ``n_chars`` is passed by keyword so a scorer can reason
#: about how much text produced the evidence -- a rate rather than a total. The
#: default scorer ignores it; :func:`ductus.score.density_aggregate` does not.
Aggregator = Callable[..., "tuple[float, float, str]"]


def iter_segments(
    text: str,
    *,
    segmenter: str | Callable[[str], Iterator[Span]] = "paragraph",
    detectors: Sequence | None = None,
    aggregate: Aggregator = default_aggregate,
    extra_signals: Iterable[Signal] = (),
) -> Iterator[Segment]:
    """Yield one scored segment at a time.

    >>> segs = list(iter_segments("Let's delve in.\\n\\nSent it Friday."))
    >>> len(segs), segs[0].label
    (2, 'leans-machine')
    """
    fns, _ = detectors_from(detectors)
    injected = tuple(extra_signals)
    for span in spans_of(text, segmenter):
        signals: list[Signal] = []
        for fn in fns:
            signals.extend(fn(text, span))
        for s in injected:
            if s.span is None or span.contains(s.span):
                signals.append(s)
        signals.sort(key=lambda s: (s.span.start if s.span else span.start, s.name))
        lean, strength, label = aggregate(signals, n_chars=span.length)
        yield Segment(
            span=span, signals=tuple(signals), lean=lean, strength=strength, label=label
        )


def gauge(
    text: str,
    *,
    segmenter: str | Callable[[str], Iterator[Span]] = "paragraph",
    detectors: Sequence | None = None,
    aggregate: Aggregator = default_aggregate,
    extra_signals: Iterable[Signal] = (),
) -> Report:
    """Score ``text`` and roll the segments up into a report.

    The document-level lean is computed over *all* signals in the document, not
    by averaging the segment leans -- averaging would let two short, heavily
    flagged paragraphs outvote a long clean one.

    >>> r = gauge("It is important to note that this is a robust tapestry.")
    >>> r.document.lean > 0 and r.n_chars == 55
    True
    >>> r.segmenter, len(r.detectors)
    ('paragraph', 4)
    """
    _, names = detectors_from(detectors)
    segments = tuple(
        iter_segments(
            text,
            segmenter=segmenter,
            detectors=detectors,
            aggregate=aggregate,
            extra_signals=extra_signals,
        )
    )
    all_signals = tuple(s for seg in segments for s in seg.signals)
    lean, strength, label = aggregate(all_signals, n_chars=len(text))
    document = Segment(
        span=Span.of(text, 0, len(text), level="document"),
        signals=(),
        lean=lean,
        strength=strength,
        label=label,
    )
    return Report(
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        n_chars=len(text),
        document=document,
        segments=segments,
        detectors=names,
        segmenter=segmenter if isinstance(segmenter, str) else "custom",
        # Which scorer produced these labels. Still "uncalibrated" -- nothing here is
        # a calibrated probability and nothing ever will be -- but since Phase 2 there
        # is more than one scorer, and two reports that do not say which one ran are
        # not comparable. See misc/docs/what-calibration-means-here.md.
        calibration=f"uncalibrated ({getattr(aggregate, '__name__', 'custom')})",
    )
