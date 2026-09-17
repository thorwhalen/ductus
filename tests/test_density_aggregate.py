"""The length-normalised scorer, and the guardrails that stop it becoming a probability.

``misc/docs/phase-2-results.md`` measures the defect this exists to fix: with the
length-blind scorer, the chance that a human-written document is called
``leans-machine`` rises from 11% to 74% with document length alone, because two stray
signals weigh the same in 600 characters as in 3000.

``misc/docs/what-calibration-means-here.md`` sets the rule that constrains the fix:
a scorer may change how evidence is *normalised*, but ``lean`` must not become a
quantity-integrating score -- that is how a probability gets back in under another
name. The last two tests here are that rule, executable.
"""

import itertools

import pytest

from ductus.base import Signal
from ductus.score import (
    REFERENCE_CHARS,
    STRENGTH_FLOOR,
    aggregate,
    density_aggregate,
)

SIGNAL_SETS = [
    [Signal("a", "machine", 0.3, "d")],
    [Signal("a", "machine", 0.45, "d"), Signal("b", "machine", 0.3, "d")],
    [Signal("a", "human", 0.35, "d")],
    [Signal("a", "machine", 0.4, "d"), Signal("b", "human", 0.25, "d")],
    [Signal("a", "neutral", 0.5, "d"), Signal("b", "machine", 0.2, "d")],
    [Signal(f"s{i}", "machine", 0.2, "d") for i in range(8)],
]
LENGTHS = [None, 1, 200, 999, 1000, 1001, 2500, 9000, 100_000]


@pytest.mark.parametrize("signals,n_chars", list(itertools.product(SIGNAL_SETS, LENGTHS)))
def test_it_can_only_ever_remove_an_accusation(signals, n_chars):
    """The scaling divides and never multiplies, so strength cannot go up.

    This is what makes the change safe to adopt as a default: whatever it does to a
    document, it does not manufacture a finding that was not there before.
    """
    _, blind_strength, _ = aggregate(signals)
    _, dense_strength, _ = density_aggregate(signals, n_chars=n_chars)
    assert dense_strength <= blind_strength + 1e-9


@pytest.mark.parametrize("signals", SIGNAL_SETS)
def test_short_passages_are_left_exactly_as_they_were(signals):
    """Below the reference length there is nothing to normalise away."""
    for n_chars in (None, 1, 200, REFERENCE_CHARS):
        assert density_aggregate(signals, n_chars=n_chars) == aggregate(signals)


@pytest.mark.parametrize("signals", SIGNAL_SETS)
def test_no_length_means_no_opinion(signals):
    """A scorer that is not told the length must behave like the length-blind one."""
    assert density_aggregate(signals) == aggregate(signals)


def test_the_same_evidence_spread_thinner_says_less():
    """The defect this exists to fix, in one assertion."""
    evidence = [Signal("a", "machine", 0.4, "d")]
    assert density_aggregate(evidence, n_chars=500)[2] == "leans-machine"
    assert density_aggregate(evidence, n_chars=4000)[2] == "no-evidence"


def test_strength_falls_monotonically_with_length():
    """Twice the text for the same evidence is half the evidence rate."""
    evidence = [Signal(f"s{i}", "machine", 0.3, "d") for i in range(4)]
    strengths = [
        density_aggregate(evidence, n_chars=n)[1] for n in (1000, 2000, 4000, 8000)
    ]
    assert strengths == sorted(strengths, reverse=True)
    assert len(set(strengths)) == len(strengths)


# --------------------------------------------------- the anti-percentage guardrails


@pytest.mark.parametrize("signals,n_chars", list(itertools.product(SIGNAL_SETS, LENGTHS)))
def test_normalising_never_touches_the_lean(signals, n_chars):
    """``lean`` is a ratio of evidence, not a quantity. Length cannot move it."""
    assert density_aggregate(signals, n_chars=n_chars)[0] == aggregate(signals)[0]


def test_lean_still_reaches_full_scale_on_a_single_weak_signal():
    """The jaggedness is the guardrail, not a defect waiting to be smoothed.

    A scorer where one weak signal gives +0.31 and six strong ones +0.93 has made
    ``lean`` integrate quantity -- which is what a probability does. See
    ``misc/docs/what-calibration-means-here.md``.
    """
    one_weak = [Signal("a", "machine", 0.12, "d")]
    six_strong = [Signal(f"s{i}", "machine", 0.45, "d") for i in range(6)]
    for n_chars in (500, 5000):
        assert density_aggregate(one_weak, n_chars=n_chars)[0] == 1.0
        assert density_aggregate(six_strong, n_chars=n_chars)[0] == 1.0


def test_lean_is_not_a_sufficient_statistic_for_how_much_was_found():
    """Same lean, different evidence: the reader cannot invert one into a probability."""
    one_weak = density_aggregate([Signal("a", "machine", 0.12, "d")], n_chars=800)
    six_strong = density_aggregate(
        [Signal(f"s{i}", "machine", 0.45, "d") for i in range(6)], n_chars=800
    )
    assert one_weak[0] == six_strong[0] == 1.0  # identical lean
    assert one_weak[1] < STRENGTH_FLOOR < six_strong[1]  # wholly different claims
    assert one_weak[2] == "no-evidence"
    assert six_strong[2] == "leans-machine"


def test_the_report_says_which_scorer_produced_it():
    """Two scorers now exist; a report that does not say which one ran is not comparable.

    It still says "uncalibrated", because nothing here is a calibrated probability and
    the normalisation change did not make one.
    """
    from ductus import gauge

    text = "Great question! Let's delve into this robust tapestry of ideas."
    assert gauge(text).calibration == "uncalibrated (density_aggregate)"
    assert gauge(text, aggregate=aggregate).calibration == "uncalibrated (aggregate)"
    assert "uncalibrated" in gauge(text).calibration
