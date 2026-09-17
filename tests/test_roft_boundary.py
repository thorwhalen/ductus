"""The second fixture: one human prefix, one machine continuation, one boundary.

``mixed_authorship.json`` (LLMTrace) interleaves machine spans written to *fill gaps*
in human prose -- machine text composed to match its surroundings, which Phase 1 found
to be close to a worst case for a perplexity method. ``roft_boundary.json`` has the
other shape: a human prefix, then a continuation, and the truth is a single boundary
index. Having both is the point; a detector that only works on one shape is a detector
whose result was about the fixture.

These tests pin the fixture's integrity and the anchoring invariant. What the
detectors actually *score* on it is measured, not asserted -- ``misc/measure_detectors.py``
and ``misc/docs/phase-2-results.md``.
"""

import json
from pathlib import Path

import pytest

from ductus import gauge

FIXTURE = Path(__file__).parent / "fixtures" / "roft_boundary.json"


@pytest.fixture(scope="module")
def documents():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["documents"]


def test_fixture_is_well_formed(documents):
    """The boundary must actually index the text it claims to cut."""
    assert len(documents) >= 12
    for d in documents:
        text, boundary = d["text"], d["true_boundary_char"]
        assert 0 < boundary < len(text), d["id"]
        assert d["ai_char_intervals"] == [[boundary, len(text)]], d["id"]
        # a prefix and a continuation that are both substantial: not a degenerate cut
        assert len(text[:boundary].split()) >= 5, d["id"]
        assert len(text[boundary:].split()) >= 5, d["id"]


def test_the_boundary_is_spread_across_its_whole_range(documents):
    """A fixture where every boundary sat at sentence 1 would measure nothing."""
    positions = {d["human_sentences"] for d in documents}
    assert positions == set(range(1, 10)), positions
    assert all(d["n_sentences"] == 10 for d in documents)


def test_this_fixture_has_a_different_shape_from_the_other_one(documents):
    """The reason it is worth vendoring: one interval, always running to the end."""
    for d in documents:
        assert len(d["ai_char_intervals"]) == 1, d["id"]
        assert d["ai_char_intervals"][0][1] == len(d["text"]), d["id"]


def test_every_signal_span_indexes_the_original_text(documents):
    """The load-bearing invariant, on the second fixture too."""
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


def test_the_deterministic_detectors_barely_see_this_fixture(documents):
    """A regression guard on a known, documented weakness -- not a claim of strength.

    The catalogue is built for essayistic and assistant-flavoured prose; this fixture
    is creative fiction, where it finds almost nothing. Recorded so that a change which
    quietly alters that shows up here rather than in a surprised reader.
    """
    machine = sum(
        1
        for d in documents
        for s in gauge(d["text"], segmenter="sentence").signals
        if s.direction == "machine"
    )
    assert machine <= 12, (
        "the deterministic detectors started firing much more on creative fiction; "
        "re-measure before assuming that is an improvement"
    )
