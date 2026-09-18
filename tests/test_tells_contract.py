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


# --------------------------------------------- tier and weight answer different questions


def test_a_rule_may_override_its_tier_weight_without_changing_its_tier():
    """`acquaint` enforces by **tier**; `ductus` weighs by **weight**.

    A rule can be right about one and wrong about the other. `summary-closer` catches
    "In conclusion," -- worth flagging as style advice even for a reader who tolerates
    AI-sounding prose, and worth almost nothing as evidence about *who wrote the text*
    (25 of 350 human-written documents implicated, zero machine-written spans matched).

    So its tier stays E, which is what `acquaint` reads, and its weight drops to the
    floor, which is what `ductus` reads. This test pins both halves, because changing
    the tier instead would silently alter what every `acquaint` user's linter enforces.
    """
    rules = {r.id: r for r in load_rules()}
    closer = rules["summary-closer"]
    assert closer.tier == "E", "acquaint enforces tier E even for tolerant readers"
    assert closer.weight == 0.15
    assert closer.weight < TIER_WEIGHT["E"]


def test_matches_carry_the_rules_own_weight_not_the_tiers():
    """A consumer that re-derived weight from tier would discard the override."""
    match = next(
        m
        for m in iter_tell_matches("In conclusion, we shipped it.")
        if m.rule_id == "summary-closer"
    )
    assert match.tier == "E"
    assert match.weight == 0.15


def test_rules_without_an_override_still_take_their_tier_weight():
    rules = {r.id: r for r in load_rules()}
    assert rules["chat-leftover"].weight == TIER_WEIGHT["E"]
    assert rules["ai-vocabulary"].weight == TIER_WEIGHT["W"]


# ------------------------------------- the "not only X but also Y" correlative


@pytest.mark.parametrize(
    "text",
    [
        "It is not only fast, but also simple.",
        "Not only me but also my sister went.",
        "She was not only the first to arrive but the last to leave.",
        "I did not eat from the tree but from the bush.",
        "We do not have to go to New Zealand but we could.",
    ],
)
def test_ordinary_negation_and_the_correlative_are_not_tells(text):
    """Measured, not assumed: these matched 61 human documents and zero machine spans.

    `not only X but also Y` is a correlative conjunction and `not <verb> ... but` is
    ordinary negation. Both were caught by the old patterns, neither is a model habit,
    and advising a writer to remove them would have been bad advice -- which is why the
    narrowing landed in the catalogue rather than only in this package's weights.
    """
    fired = {m.rule_id for m in iter_tell_matches(text)}
    assert "contrastive-negation" not in fired, fired


@pytest.mark.parametrize(
    "text",
    [
        "It is not merely useful, but transformative.",
        "This isn't just a tool, it's a new way of working.",
        "The result was not simply good, but remarkable.",
    ],
)
def test_the_antithesis_habit_is_still_caught(text):
    """The narrowing removed false positives; it must not have removed the rule."""
    assert "contrastive-negation" in {m.rule_id for m in iter_tell_matches(text)}
