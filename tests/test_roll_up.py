"""The document verdict, and the properties that stop it being a percentage.

The measurement behind this is in ``misc/docs/reducing-false-accusations.md``; the
argument, written before any of it was changed, is in
``misc/docs/document-verdict-decision.md``.

The thing being fixed: pooling every signal in a document and scoring the heap made a
long human document more likely to be accused *for being long*. With a ~3% per-segment
false-flag rate, the chance that something fires is 1 - 0.97^n -- a coin toss by thirty
segments. Pooling treated accumulation as though it were corroboration.
"""

import pytest

from ductus import gauge
from ductus.base import Segment, Signal, Span
from ductus.score import SEGMENT_RATE_FULL, STRENGTH_FLOOR, roll_up


def seg(label, *, weight=0.5, direction="machine"):
    """A segment carrying one signal, or none when it reached no label."""
    found = () if label == "no-evidence" else (Signal("t", direction, weight, "d"),)
    lean = {"leans-machine": 1.0, "leans-human": -1.0}.get(label, 0.0)
    return Segment(
        span=Span(0, 1, "x"), signals=found, lean=lean, strength=1.0, label=label
    )


def test_one_stray_flag_does_not_convict_a_long_document():
    """The defect, in one assertion."""
    document = [seg("no-evidence")] * 19 + [seg("leans-machine")]
    assert roll_up(document)[2] == "no-evidence"


def test_the_same_rate_says_the_same_thing_at_any_length():
    """Length-normalised by construction, not by a constant that had to be fitted.

    Two segments in ten and twenty in a hundred are the same claim, and -- unlike the
    density scorer, which needed ``REFERENCE_CHARS`` chosen on a corpus -- nothing had
    to be measured to make that true.
    """
    verdicts = set()
    for scale in (1, 2, 5, 10, 25):
        document = [seg("leans-machine")] * (2 * scale) + [seg("no-evidence")] * (
            8 * scale
        )
        lean, _, label = roll_up(document, n_chars=1000 * scale)
        verdicts.add((lean, label))
    assert len(verdicts) == 1, verdicts


def test_a_document_must_satisfy_both_views_of_how_much_evidence_there_is():
    """One flagged paragraph in two is a rate of 50% -- unless it is 4000 characters.

    The rate view catches a long document with many segments and one stray flag; the
    density view catches a long document cut into two paragraphs where one stray flag
    is half of them. Believing the weaker of the two is the conservative direction.
    """
    pair = [seg("leans-machine"), seg("no-evidence")]
    assert roll_up(pair)[2] == "leans-machine"
    assert roll_up(pair, n_chars=4000)[2] == "no-evidence"


def test_enough_converging_segments_still_convict():
    """The point is to stop counting accumulation as corroboration, not to go silent."""
    document = [seg("leans-machine")] * 8 + [seg("no-evidence")] * 12
    lean, strength, label = roll_up(document, n_chars=2000)
    assert label == "leans-machine"
    assert lean == 1.0
    assert strength > STRENGTH_FLOOR


def test_nothing_directional_says_nothing():
    assert roll_up([]) == (0.0, 0.0, "no-evidence")
    assert roll_up([seg("no-evidence")] * 5) == (0.0, 0.0, "no-evidence")


# ------------------------------------------------- the anti-percentage guardrails


def test_lean_is_a_direction_ratio_not_a_fraction_of_the_document():
    """ "What proportion of segments lean machine" is one step from "what % is AI".

    ``lean`` must not be that step. It says which way the flagged parts point and
    nothing about how much of the document they are, so two documents with wildly
    different amounts of machine-leaning text share a lean of +1.0.
    """
    sparse = [seg("leans-machine")] + [seg("no-evidence")] * 19
    dense = [seg("leans-machine")] * 20
    assert roll_up(sparse)[0] == roll_up(dense)[0] == 1.0
    assert roll_up(sparse)[1] < roll_up(dense)[1]  # the quantity lives in strength


def test_lean_still_reaches_full_scale_on_a_single_signal():
    """The jaggedness is the guardrail; smoothing it is how a probability gets in."""
    assert roll_up([seg("leans-machine", weight=0.12)])[0] == 1.0


def test_human_leaning_evidence_below_the_label_threshold_still_counts():
    """A regression guard on a real mistake made while building this.

    Counting segment *labels* to get the lean was tried first. It silently discarded
    every signal in a segment that did not reach a label -- disproportionately the
    human-leaning ones, which this package treats as first-class -- and documents that
    should have read as mixed came out as ``leans-machine``.
    """
    quiet_human = Segment(
        span=Span(0, 1, "x"),
        signals=(Signal("h", "human", 0.45, "forensic"),),
        lean=-1.0,
        strength=0.1,
        label="no-evidence",  # below the strength floor: no label of its own
    )
    document = [seg("leans-machine", weight=0.5), quiet_human]
    lean, _, _ = roll_up(document, n_chars=500)
    assert lean < 1.0, "sub-threshold human evidence was discarded by the roll-up"


# --------------------------------------------------------- end to end, real text


def test_segment_findings_are_untouched_by_the_roll_up():
    """The roll-up changes the summary, never the evidence underneath it."""
    text = (
        "Great question! Let's delve into this robust tapestry of ideas.\n\n"
        "Sent the export Friday. Two sites, not five. Call if it breaks."
    )
    report = gauge(text)
    assert report.segments[0].label == "leans-machine"
    assert report.segments[0].signals
    assert report.document.signals == ()  # the evidence lives one level down


@pytest.mark.parametrize("segmenter", ["paragraph", "sentence"])
def test_a_wholly_machine_sounding_document_is_still_called(segmenter):
    text = (
        "Great question! It's important to note that this framework serves as a "
        "bridge between the two domains.\n\n"
        "In conclusion, let's delve into this robust tapestry of ideas.\n\n"
        "Moreover, the solution is not merely useful, but transformative."
    )
    assert gauge(text, segmenter=segmenter).document.label == "leans-machine"


def test_the_rate_constant_is_a_rate():
    """A guard on the thing that makes this length-normalised at all."""
    assert 0 < SEGMENT_RATE_FULL < 1


@pytest.mark.parametrize(
    "text",
    [
        "I did not eat from the tree but from the bush.",
        "We do not have to go to New Zealand but we could.",
        "She chose not to run too fast but to finish.",
    ],
)
def test_the_rhetoric_detector_no_longer_reads_ordinary_negation_as_antithesis(text):
    """`not-x-but-y` matched 42 human documents and zero machine spans before this.

    The pattern required no intensifier, so every "not <verb> ... but" in ordinary
    English tripped it. It now requires "just", "merely" or "simply".
    """
    from ductus.base import Span
    from ductus.detect import rhetoric

    fired = {s.name for s in rhetoric(text, Span.of(text, 0, len(text)))}
    assert "not-x-but-y" not in fired, fired


def test_the_antithesis_it_was_built_for_is_still_caught():
    from ductus.base import Span
    from ductus.detect import rhetoric

    text = "The results were not merely good, but transformative."
    assert "not-x-but-y" in {s.name for s in rhetoric(text, Span.of(text, 0, len(text)))}
