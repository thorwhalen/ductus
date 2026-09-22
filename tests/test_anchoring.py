"""Spans must survive an edit -- the property the whole edit-and-re-score story rests on.

Character offsets alone are destroyed by any insertion before them. That is why
every Span also carries the W3C redundant selectors (quote, prefix, suffix), and
why a judgment anchored by quote is dropped rather than mis-anchored when the
quote is gone. Mis-anchoring is worse than losing a finding: it attaches a reason
to text the reason was never about.
"""

from ductus import Span, gauge
from ductus.tools import _signals_from_judgments

TEXT = (
    "We shipped on Friday.\n\n"
    "It's important to note that the rollout serves as a bridge.\n\n"
    "Two sites, not five."
)


def test_span_carries_enough_to_refind_itself():
    span = Span.of(TEXT, 30, 39)
    assert TEXT[span.start : span.end] == span.quote
    assert TEXT.find(span.prefix + span.quote + span.suffix) >= 0


def test_quote_anchoring_survives_an_insertion_before_it():
    """The offsets move; the quote still finds the right place."""
    quote = "serves as a bridge"
    before = TEXT.find(quote)
    edited = "A new opening paragraph.\n\n" + TEXT
    after = edited.find(quote)

    assert after != before  # offsets really did shift
    assert after - before == len("A new opening paragraph.\n\n")
    signals = _signals_from_judgments(edited, [{"quote": quote, "direction": "machine"}])
    assert signals[0].span.start == after  # re-anchored, not stale


def test_a_judgment_whose_quote_is_gone_is_dropped_not_misanchored():
    edited = TEXT.replace("serves as a bridge", "connects the two teams")
    signals = _signals_from_judgments(
        edited, [{"quote": "serves as a bridge", "direction": "machine", "note": "stale"}]
    )
    assert signals == []


def test_judgments_attach_to_the_segment_that_contains_them():
    judgments = [
        {
            "quote": "Two sites, not five.",
            "direction": "human",
            "name": "unhedged-specificity",
            "weight": 0.4,
        }
    ]
    extra = _signals_from_judgments(TEXT, judgments)
    report = gauge(TEXT, extra_signals=extra)

    holder = [s for s in report.segments if "Two sites" in s.span.quote]
    assert len(holder) == 1
    assert any(s.name == "unhedged-specificity" for s in holder[0].signals)
    # and nowhere else
    others = [s for s in report.segments if "Two sites" not in s.span.quote]
    assert not any(
        s.name == "unhedged-specificity" for seg in others for s in seg.signals
    )


def test_segments_tile_the_text_without_overlapping():
    report = gauge(TEXT, segmenter="sentence")
    spans = [s.span for s in report.segments]
    for a, b in zip(spans, spans[1:]):
        assert a.end <= b.start


def test_every_offset_indexes_the_text_even_when_lowercasing_changes_its_length():
    """Found while fixing ductus#11: a detector that matched against ``s.lower()``
    reported offsets into the lowered string. ``'İ'.lower()`` is two code points, so
    every finding after one was shifted -- the same symptom as #11, server-side."""
    text = (
        "İİİİ I really do appreciate the effort here. However, we need changes.\n\n"
        "İstanbul office: I value the draft. That said, it is late."
    )
    report = gauge(text)
    spans = [sig.span for seg in report.segments for sig in seg.signals if sig.span]
    assert any(
        sig.name == "concede-pivot" for seg in report.segments for sig in seg.signals
    ), "the fixture must exercise the detector it pins"
    for span in spans:
        assert text[span.start : span.end] == span.quote
    pivots = [
        sig
        for seg in report.segments
        for sig in seg.signals
        if sig.name == "concede-pivot"
    ]
    assert all(p.span.quote.lower().startswith("i ") for p in pivots)
