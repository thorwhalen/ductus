"""The model-based detectors: the banding arithmetic always, the models when present.

Two halves. The first needs nothing installed -- it pins the decisions argued in
``misc/docs/curvature-as-evidence.md``, which are arithmetic and belong under test
whether or not a GPU, a network or the ``[local]`` extra is anywhere nearby. The
second runs the real models and is skipped when they are not available.

The cheap-import test is the one that must never be skipped: it is what keeps the
promise that ``pip install ductus`` does not drag in ``torch``.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ductus.base import Span
from ductus.curvature import (
    BANDS,
    MIN_TOKENS,
    MIN_WINDOWS,
    _iter_chunks,
    _Profile,
    _reference_scores,
    _token_range,
    band_of,
    robust_z,
)
from ductus.detect import DEFAULT_DETECTORS, DETECTORS

FIXTURE = Path(__file__).parent / "fixtures" / "mixed_authorship.json"


# --------------------------------------------------------------- always, no extras


def test_importing_ductus_does_not_import_torch():
    """The core stays cheap. A model detector may cost a download; importing must not."""
    probe = (
        "import sys; import ductus; "
        "assert 'torch' not in sys.modules, 'ductus imported torch at import time'; "
        "assert 'transformers' not in sys.modules; print('ok')"
    )
    r = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=120
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_model_detectors_are_nameable_but_not_default():
    """Registered so ``--detectors binoculars`` works; not on by default.

    A detector joins the default only by beating the deterministic set on the
    fixture. See ``misc/docs/phase-1-results.md``.
    """
    assert {"fast-detect-gpt", "binoculars"} <= set(DETECTORS)
    assert {"fast-detect-gpt", "binoculars"}.isdisjoint(DEFAULT_DETECTORS)
    assert DEFAULT_DETECTORS == ("tells", "forensic", "rhetoric", "rhythm")


def test_a_mid_range_score_says_nothing_at_all():
    """The dead zone is the design, not an oversight.

    Mapping a continuous score linearly onto a weight is how a calibrated-probability
    claim gets back in; a mid-range standing is the detector having nothing to say.
    """
    assert band_of(0.0) is None
    assert band_of(1.4999) is None
    assert band_of(-1.4999) is None
    assert band_of(1.5) == 0.30
    assert band_of(2.5) == 0.45


def test_no_band_outweighs_the_strongest_inspectable_signal():
    """A number the reader cannot check does not get to outvote a quote they can."""
    assert max(weight for _, weight in BANDS) <= 0.45  # colon-tricolon


def test_banding_is_symmetric_so_the_detector_can_argue_human_too():
    """A detector that can only accuse is not a measuring instrument."""
    for z in (1.6, 2.0, 3.0, 9.0):
        assert band_of(z) == band_of(-z)


def test_robust_z_is_not_dragged_by_the_outliers_it_is_looking_for():
    """Median/MAD, not mean/sd: machine stretches are the outliers being hunted."""
    human_like = [1.0, 1.1, 0.9, 1.0, 1.2, 0.8]
    contaminated = human_like + [9.0, 9.5, 10.0]
    assert robust_z(9.0, contaminated) > 3.0
    assert robust_z(1.0, contaminated) < 1.0


def test_a_degenerate_reference_yields_nothing():
    """No spread means no comparison; 0.0 falls in the dead zone."""
    assert robust_z(5.0, [2.0, 2.0, 2.0]) == 0.0
    assert band_of(robust_z(5.0, [2.0, 2.0, 2.0])) is None


def test_every_token_position_is_scored_exactly_once():
    """Chunking must not drop or double-count a position, or a span's score shifts."""
    for n in (1, 2, 17, 511, 512, 513, 1200):
        for window in (8, 64, 512):
            covered = [p for s, e, k in _iter_chunks(n, window) for p in range(k, e)]
            assert covered == list(range(1, n)), (n, window)


def test_the_reference_never_includes_the_span_it_judges():
    """A span compared against a distribution it helped define is comparing to itself.

    Built so the property is visible: only the span's own tokens carry any value, so
    if a single reference window overlapped it, that window's score would be nonzero.
    """
    lo, hi = 40, 60
    a = [100.0 if lo <= i < hi else 0.0 for i in range(200)]
    profile = _Profile((), tuple(a), (1.0,) * 200, "ratio", 1.0, "m")
    reference = _reference_scores(profile, lo, hi)
    assert len(reference) >= MIN_WINDOWS
    assert set(reference) == {0.0}
    assert profile.score(lo, hi) == 100.0  # the span itself is the only nonzero window


def test_token_range_is_empty_for_a_span_outside_the_text():
    profile = _Profile(((0, 3), (3, 7)), (), (), "ratio", 1.0, "m")
    assert _token_range(profile, Span(99, 120, "x")) == (0, 0)


# ---------------------------------------------------------------- needs the models
#
# Skipped, never failed, when the [local] extra or the weights are absent -- and
# scoped as a fixture rather than a module-level `importorskip` so that the
# cheap-import test above still runs on an installation without torch, which is
# precisely the installation it is making a promise about.


@pytest.fixture(scope="module")
def models_available():
    """Skip rather than fail when the extra is missing or the weights are unreachable."""
    pytest.importorskip("torch", reason="the [local] extra is not installed")
    pytest.importorskip("transformers", reason="the [local] extra is not installed")
    from ductus.curvature import _load

    try:
        _load("gpt2", "cpu")
        _load("distilgpt2", "cpu")
    except Exception as e:  # network off, no cache, no disk
        pytest.skip(f"proxy models unavailable: {e}")


@pytest.fixture(scope="module")
def document():
    docs = json.loads(FIXTURE.read_text(encoding="utf-8"))["documents"]
    return max(docs, key=lambda d: len(d["text"]))


@pytest.mark.parametrize("detector", ["fast-detect-gpt", "binoculars"])
def test_every_signal_span_indexes_the_original_text(
    models_available, document, detector
):
    """The load-bearing invariant, held by the model detectors too."""
    from ductus import gauge

    text = document["text"]
    report = gauge(text, segmenter="sentence", detectors=[detector])
    assert report.signals, f"{detector} found nothing on a long mixed document"
    for signal in report.signals:
        span = signal.span
        assert text[span.start : span.end] == span.quote
        assert text[max(0, span.start - 40) : span.start] == span.prefix
        assert 0.0 <= signal.weight <= 1.0
        assert signal.direction in ("machine", "human")


@pytest.mark.parametrize("detector", ["fast-detect-gpt", "binoculars"])
def test_the_reason_names_the_model_and_admits_what_it_is(
    models_available, document, detector
):
    """The reader cannot inspect this evidence, so the note has to say so."""
    from ductus import gauge

    report = gauge(document["text"], segmenter="sentence", detectors=[detector])
    for signal in report.signals:
        assert "not a quotation from it" in signal.note
        assert "comparable windows" in signal.note
        assert "gpt2" in signal.note  # the model is named, so it is reproducible


@pytest.mark.parametrize("detector", ["fast-detect-gpt", "binoculars"])
def test_a_one_segment_document_yields_nothing(models_available, document, detector):
    """No rest-of-the-document, no claim. This is the cost documented in the design."""
    from ductus import gauge

    report = gauge(document["text"], segmenter="document", detectors=[detector])
    assert report.signals == ()


def test_a_short_span_is_below_the_token_floor(models_available):
    """Too few tokens for the statistic to mean anything: say nothing."""
    from ductus import gauge
    from ductus.curvature import MIN_TOKENS as floor

    assert floor == MIN_TOKENS
    report = gauge("Short. Also short. Tiny.", detectors=["fast-detect-gpt"])
    assert report.signals == ()


def test_both_directions_actually_occur_on_real_text(models_available):
    """Not a design claim but an observed one: the detectors do argue human."""
    from ductus import gauge

    docs = json.loads(FIXTURE.read_text(encoding="utf-8"))["documents"]
    directions = set()
    for d in docs:
        report = gauge(
            d["text"], segmenter="sentence", detectors=["fast-detect-gpt", "binoculars"]
        )
        directions |= {s.direction for s in report.signals}
    assert directions == {"machine", "human"}
