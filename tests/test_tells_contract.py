"""The catalogue API that `acquaint` depends on.

`acquaint.deslop` reads this package's tells catalogue instead of carrying its
own, and layers recipient calibration (which tiers are enforced for which reader,
and that reader's blocklist) on top. These tests pin the shape it relies on, so
that a change here fails loudly rather than silently breaking a downstream
package's linter.
"""

import pytest

from ductus.tells import TIER_WEIGHT, iter_tell_matches, load_rules, metrics


def test_rules_load_and_are_well_formed():
    rules = load_rules()
    assert len(rules) >= 15
    for rule in rules:
        assert rule.id and rule.message
        assert rule.tier in ("E", "W", "S")
        assert rule.patterns
        assert 0 < rule.weight <= 1


def test_tiers_are_ordered_by_confidence():
    assert TIER_WEIGHT["E"] > TIER_WEIGHT["W"] > TIER_WEIGHT["S"]


def test_metrics_carry_the_shared_thresholds():
    m = metrics()
    assert m["min_sentences_for_rhythm"] > 0
    assert 0 < m["sentence_len_cv_min"] < 1
    assert m["short_message_words"] > 0


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Great question! Happy to help.", "chat-leftover"),
        ("As of my knowledge cutoff, prices vary.", "cutoff-disclaimer"),
        ("It's important to note the risk.", "throat-clearing"),
        ("In conclusion, we shipped it.", "summary-closer"),
        ("Let's delve into this tapestry.", "ai-vocabulary"),
        ("The draft still has [ASK: the number] in it.", "unfilled-placeholder"),
    ],
)
def test_known_tells_fire(text, expected):
    assert expected in {m.rule_id for m in iter_tell_matches(text)}


def test_plain_specific_prose_fires_nothing():
    """The false-positive floor: ordinary human writing must come back clean."""
    for text in (
        "Sending the export on Friday. Two sites, not five.",
        "The migration failed at 3am because the disk filled up. Rerunning it now.",
        "I read your PR. The retry logic looks wrong when the socket times out.",
    ):
        assert list(iter_tell_matches(text)) == [], text


def test_matches_carry_usable_offsets():
    text = "Well, let's delve into it."
    m = next(m for m in iter_tell_matches(text) if m.rule_id == "ai-vocabulary")
    assert text[m.start : m.end] == m.matched == "delve"


def test_offset_shifts_a_whole_scan():
    text = "delve"
    assert [m.start for m in iter_tell_matches(text, offset=1000)] == [1000]


def test_tier_filter():
    assert {
        m.tier for m in iter_tell_matches("Great question! Let's delve.", tiers=["E"])
    } == {"E"}


def test_a_caller_can_supply_its_own_catalogue():
    """The `rules=` seam: a catalogue derived from one author's own writing."""
    from ductus.tells import TellRule
    import re

    custom = (
        TellRule(
            id="mine",
            tier="W",
            message="a habit of mine",
            patterns=(re.compile(r"\bfrankly\b", re.I),),
        ),
    )
    assert {m.rule_id for m in iter_tell_matches("Frankly, it broke.", rules=custom)} == {
        "mine"
    }
    assert list(iter_tell_matches("Let's delve in.", rules=custom)) == []
