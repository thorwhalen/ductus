"""The tells catalogue: named regular-expression patterns, tiered by confidence.

This is the cheap floor of detection -- it finds *phrases* a model overuses, and
by construction it cannot find *shapes* (see :mod:`ductus.detect` for those). It
is fast, it needs nothing installed, and every hit points at the exact characters
that matched, which is what makes it useful for highlighting rather than scoring.

The catalogue is data (``ductus/data/tells.yaml``) and a keyword argument, so a
list derived from one author's own writing can replace it without code changes.

``acquaint`` consumes :func:`iter_tell_matches` directly for the deterministic
half of its ``deslop`` check, and layers recipient calibration on top.

>>> ms = list(iter_tell_matches("Great question! Let's delve into this tapestry."))
>>> sorted({m.rule_id for m in ms})
['ai-vocabulary', 'chat-leftover', 'exclamation']
>>> m = next(m for m in ms if m.rule_id == 'chat-leftover')
>>> m.tier, m.matched.lower()
('E', 'great question')
>>> list(iter_tell_matches("Sending the export on Friday. Two sites, not five."))
[]
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

__all__ = [
    "TIER_WEIGHT",
    "TellMatch",
    "TellRule",
    "iter_tell_matches",
    "load_catalogue",
    "load_rules",
    "metrics",
]

#: How much each tier is worth as evidence, on the 0..1 Signal scale.
#: E is near-certain but still not 1.0 -- a quoted model output is not a
#: model-written document, and nothing in this package claims certainty.
TIER_WEIGHT = {"E": 0.50, "W": 0.30, "S": 0.15}

_FLAGS = re.IGNORECASE | re.MULTILINE
# `.` in a pattern stands in for an apostrophe so straight and curly both match.
_APOSTROPHES = "['’ʼ]"


@dataclass(frozen=True)
class TellRule:
    """One named rule: a tier, a message, and the patterns that trigger it."""

    id: str
    tier: str
    message: str
    patterns: tuple[re.Pattern[str], ...]
    #: An optional per-rule override of the tier's weight, read from ``weight:`` in
    #: the catalogue. It exists because a rule's **tier** and its **evidential
    #: weight** answer different questions, and a rule can be right about one and
    #: wrong about the other: ``summary-closer`` catches "In conclusion," which is
    #: reasonable style advice (``acquaint`` enforces tiers) and almost worthless as
    #: evidence about *who wrote the text* (``ductus`` uses weights). Overriding the
    #: weight changes this package only -- ``acquaint`` reads ``tier`` and never
    #: ``weight``. Changing a tier is a two-package decision; see
    #: ``misc/docs/document-verdict-decision.md``.
    weight_override: float | None = None

    @property
    def weight(self) -> float:
        """Evidential weight: the per-rule override when set, else the tier's.

        >>> TellRule("x", "E", "m", (), weight_override=0.15).weight
        0.15
        >>> TellRule("x", "E", "m", ()).weight
        0.5
        """
        if self.weight_override is not None:
            return self.weight_override
        return TIER_WEIGHT.get(self.tier, 0.15)


@dataclass(frozen=True)
class TellMatch:
    """Where a rule fired, and on what text."""

    rule_id: str
    tier: str
    message: str
    start: int
    end: int
    matched: str
    #: The rule's evidential weight -- its per-rule override when it has one, else its
    #: tier's. Carried here so a consumer never has to re-derive it from ``tier``, which
    #: would silently discard the override. Defaulted so existing constructions still
    #: work; :func:`iter_tell_matches` always fills it in.
    weight: float = 0.0


def _compile(pattern: str) -> re.Pattern[str]:
    """Compile a catalogue pattern, widening bare `.` into any apostrophe.

    Only a `.` that sits between two word characters is treated this way; a `.`
    used as a real wildcard elsewhere in the pattern is left alone.

    >>> bool(_compile(r"don.t").search("don’t"))
    True
    >>> bool(_compile(r"don.t").search("don't"))
    True
    """
    widened = re.sub(r"(?<=\w)\.(?=\w)", _APOSTROPHES, pattern)
    return re.compile(widened, _FLAGS)


@lru_cache(maxsize=4)
def load_catalogue(path: str | None = None) -> dict[str, Any]:
    """Read the catalogue file. Cached; pass a path to use a different one.

    >>> sorted(load_catalogue())
    ['metrics', 'rules']
    """
    import yaml  # deferred: keeps `import ductus` cheap

    if path is None:
        from importlib.resources import files

        text = (files("ductus.data") / "tells.yaml").read_text(encoding="utf-8")
    else:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    return yaml.safe_load(text)


def load_rules(path: str | None = None) -> tuple[TellRule, ...]:
    """The catalogue's rules, compiled.

    >>> rules = load_rules()
    >>> len(rules) > 10 and all(r.patterns for r in rules)
    True
    >>> sorted({r.tier for r in rules})
    ['E', 'S', 'W']
    """
    return tuple(
        TellRule(
            id=r["id"],
            tier=r["tier"],
            weight_override=(float(r["weight"]) if r.get("weight") is not None else None),
            message=r["message"],
            patterns=tuple(_compile(p) for p in r["patterns"]),
        )
        for r in load_catalogue(path)["rules"]
    )


def metrics(path: str | None = None) -> dict[str, Any]:
    """The catalogue's shared numeric thresholds.

    >>> metrics()["min_sentences_for_rhythm"] > 0
    True
    """
    return dict(load_catalogue(path)["metrics"])


def iter_tell_matches(
    text: str,
    *,
    rules: Sequence[TellRule] | None = None,
    tiers: Sequence[str] | None = None,
    offset: int = 0,
) -> Iterator[TellMatch]:
    """Every catalogue hit in ``text``, in document order.

    ``offset`` is added to every position, so a caller scanning one segment of a
    larger document gets offsets into the document.

    >>> [m.rule_id for m in iter_tell_matches("In conclusion, it's important to note this.")]
    ['summary-closer', 'throat-clearing']
    >>> [m.start for m in iter_tell_matches("delve", offset=100)]
    [100]
    >>> [m.rule_id for m in iter_tell_matches("delve", tiers=["E"])]
    []
    """
    rules = load_rules() if rules is None else rules
    if tiers is not None:
        rules = [r for r in rules if r.tier in tiers]
    found: list[TellMatch] = []
    for rule in rules:
        for pattern in rule.patterns:
            for m in pattern.finditer(text):
                found.append(
                    TellMatch(
                        rule_id=rule.id,
                        tier=rule.tier,
                        message=rule.message,
                        start=offset + m.start(),
                        end=offset + m.end(),
                        matched=m.group(0),
                        weight=rule.weight,
                    )
                )
    found.sort(key=lambda m: (m.start, -(m.end - m.start)))
    return iter(found)
