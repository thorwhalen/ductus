"""Measured against real human/AI mixed documents with character-level ground truth.

The fixture is a slice of LLMTrace (Apache-2.0), where each document carries
``ai_char_intervals``: the exact character ranges that were machine-written.

What these tests pin down is deliberately modest, because the honest result is
modest: **the deterministic detectors have high precision and very low recall.**
They fire rarely, and when they fire they are usually right. Asserting more than
that would be asserting a number we have not earned, which is the exact failure
this package exists to avoid.
"""

import json
import statistics
from pathlib import Path

import pytest

from ductus import gauge

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_authorship.json"


@pytest.fixture(scope="module")
def documents():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["documents"]


def _ai_fraction(span, intervals) -> float:
    covered = sum(max(0, min(span.end, b) - max(span.start, a)) for a, b in intervals)
    return covered / max(1, span.length)


def test_fixture_is_well_formed(documents):
    """Ground truth intervals must actually index the text they describe."""
    assert len(documents) >= 10
    for d in documents:
        text, intervals = d["text"], d["ai_char_intervals"]
        assert intervals, d["id"]
        for a, b in intervals:
            assert 0 <= a < b <= len(text), (d["id"], a, b)
        covered = sum(b - a for a, b in intervals)
        assert 0 < covered < len(text), f"{d['id']} is not actually mixed"


def test_every_signal_span_indexes_the_original_text(documents):
    """The load-bearing invariant: an offset always finds the text it claims."""
    for d in documents:
        text = d["text"]
        report = gauge(text, segmenter="sentence")
        for segment in report.segments:
            assert text[segment.span.start : segment.span.end] == segment.span.quote
            for signal in segment.signals:
                if signal.span is None:
                    continue
                s = signal.span
                assert text[s.start : s.end] == s.quote, (d["id"], signal.name)
                assert text[max(0, s.start - 40) : s.start] == s.prefix


def test_flagged_segments_land_on_the_right_side(documents):
    """When a signal fires, it should point the way the ground truth points."""
    agreements = []
    for d in documents:
        report = gauge(d["text"], segmenter="sentence")
        for segment in report.segments:
            if not segment.signals or segment.lean == 0:
                continue
            fraction = _ai_fraction(segment.span, d["ai_char_intervals"])
            if 0.2 <= fraction <= 0.8:
                continue  # straddles a boundary: no clean ground truth for it
            agreements.append((segment.lean > 0) == (fraction > 0.8))

    assert len(agreements) >= 5, "too few decisive segments to measure anything"
    rate = statistics.mean(agreements)
    assert rate >= 0.6, (
        f"flagged segments agreed with ground truth only {rate:.0%} of the time"
    )


def test_recall_is_low_and_that_is_documented(documents):
    """A regression guard on the known weakness, not a claim of strength.

    The deterministic detectors cover a small fraction of machine-written text.
    This asserts the floor (they fire at all) and records the ceiling, so that a
    change which quietly makes coverage worse fails here.
    """
    total = sum(len(gauge(d["text"], segmenter="sentence").signals) for d in documents)
    assert total >= 5, "the detectors stopped firing on known-mixed documents"
    ai_chars = sum(sum(b - a for a, b in d["ai_char_intervals"]) for d in documents)
    assert ai_chars > 3000  # the fixture really does contain a lot of machine text
