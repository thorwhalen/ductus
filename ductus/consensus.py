"""Several close readers, and the sentences at least ``k`` of them agree on.

One reader's judgments are noisy in a way that hides the thing being measured. Fresh,
strict readers given the same instructions each flag dozens of shapes in a long essay,
mostly on text the previous reader passed, so a raw count does not move when a rewrite
helps and does not move when it does not. What does move is the set of **sentences
that independent readers both flag**. That is what this module counts.

Two numbers come out, and both are descriptions of how a text reads, never of who
wrote it:

- **per-reader counts** -- how many sentences each reader flagged, each direction. Large
  and unequal is normal; it is the reader variance this module exists to see past.
- **consensus density** -- sentences flagged by at least ``k`` readers, per 1,000 words.
  A density on its own is a bare number. :func:`pooled` takes the same measure over
  reference texts -- the author's own earlier writing -- so a report can put the two
  side by side instead.

The unit is the sentence, from the same segmenter ``gauge(segmenter="sentence")`` uses,
so a judgment and a sentence are anchored by the same rule as everywhere else: a quote
that no longer occurs in the text is **dropped and counted**, never re-anchored.

Pure functions over judgment records (dicts); nothing here reads a file.

>>> text = "It is a pattern. You decide, invest, regret. Sent it Friday."
>>> a = [{"quote": "You decide, invest, regret", "direction": "machine"}]
>>> b = [{"quote": "invest, regret.", "direction": "machine"},
...      {"quote": "It is a pattern", "direction": "machine"}]
>>> c = consensus(text, [a, b], names=["a", "b"])
>>> [(r["name"], r["machine"]) for r in c["readers"]]
[('a', 1), ('b', 2)]
>>> c["machine"]["count"], [u["quote"] for u in c["machine"]["units"]]
(1, ['You decide, invest, regret.'])
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any

from ductus.base import Signal, Span
from ductus.segment import spans_of

__all__ = [
    "DEFAULT_K",
    "anchor_judgment",
    "consensus",
    "consensus_signals",
    "pooled",
]

#: How many readers must flag a sentence for it to count. Two is the smallest number
#: that is agreement rather than one reader's taste.
DEFAULT_K = 2

#: The rate's denominator, in words. A rate per N words is a density, not a share.
PER_WORDS = 1000

_DIRECTIONS = ("machine", "human")

Judgment = Mapping[str, Any]


def anchor_judgment(text: str, judgment: Judgment) -> tuple[int, int] | None:
    """Where a judgment lands in ``text``, or ``None`` when its quote is gone.

    A judgment carries a ``quote`` (anchored at its first occurrence) or explicit
    ``start``/``end`` offsets. A quote that does not occur is dropped by every caller --
    mis-anchoring would attach a reason to text it was never about.

    >>> anchor_judgment("one two three", {"quote": "two"})
    (4, 7)
    >>> anchor_judgment("one two three", {"quote": "four"}) is None
    True
    >>> anchor_judgment("one two three", {"start": 0, "end": 3})
    (0, 3)
    """
    if "quote" in judgment:
        start = text.find(judgment["quote"])
        if start < 0:
            return None
        return start, start + len(judgment["quote"])
    return int(judgment["start"]), int(judgment["end"])


def _flagged(
    text: str, judgments: Sequence[Judgment], units: Sequence[Span]
) -> tuple[dict[str, dict[int, list[Judgment]]], int]:
    """Which units each direction's judgments touch, and how many quotes were dropped.

    A judgment flags every unit it overlaps, so a quote spanning two sentences flags
    both. Returns ``{direction: {unit_index: [judgments on it]}}`` and the drop count.
    """
    hits: dict[str, dict[int, list[Judgment]]] = {d: {} for d in _DIRECTIONS}
    dropped = 0
    for j in judgments:
        if j.get("direction") not in hits:
            continue
        where = anchor_judgment(text, j)
        if where is None:
            dropped += 1
            continue
        start, end = where
        for i, u in enumerate(units):
            if u.start < end and u.end > start:
                hits[j["direction"]].setdefault(i, []).append(j)
    return hits, dropped


def _density(count: int, n_words: int) -> float | None:
    return round(PER_WORDS * count / n_words, 2) if n_words else None


def consensus(
    text: str,
    readers: Sequence[Sequence[Judgment]],
    *,
    k: int = DEFAULT_K,
    names: Sequence[str] | None = None,
    segmenter: str | Callable[[str], Iterator[Span]] = "sentence",
) -> dict[str, Any]:
    """Per-reader counts and the sentences at least ``k`` readers flag, each direction.

    ``readers`` is one list of judgment records per reader. ``names`` labels them in the
    result (default ``reader 1``, ``reader 2``, ...). ``segmenter`` is the unit readers
    must agree on -- a sentence by default, any of :data:`ductus.segment.SEGMENTERS` or
    a callable.

    Everything returned is JSON-ready: counts, densities per 1,000 words, and each
    consensus unit with its offsets, its quote, the readers that flagged it and the
    shapes they named.

    >>> t = "One. Two. Three."
    >>> r = [[{"quote": "Two.", "direction": "human"}]] * 3
    >>> c = consensus(t, r, k=3)
    >>> c["human"]["count"], c["machine"]["count"], c["n_words"]
    (1, 0, 3)
    >>> consensus(t, r, k=4)
    Traceback (most recent call last):
        ...
    ValueError: k=4 needs at least 4 readers; got 3
    """
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    if len(readers) < k:
        raise ValueError(f"k={k} needs at least {k} readers; got {len(readers)}")
    names = list(names) if names is not None else []
    names += [f"reader {i + 1}" for i in range(len(names), len(readers))]

    units = list(spans_of(text, segmenter))
    n_words = len(text.split())
    per_reader = [_flagged(text, judgments, units) for judgments in readers]

    out: dict[str, Any] = {
        "k": k,
        "n_readers": len(readers),
        "unit": segmenter if isinstance(segmenter, str) else "custom",
        "n_units": len(units),
        "n_words": n_words,
        "per_words": PER_WORDS,
        "readers": [
            {
                "name": name,
                **{d: len(hits[d]) for d in _DIRECTIONS},
                "dropped": dropped,
            }
            for name, (hits, dropped) in zip(names, per_reader)
        ],
    }
    for d in _DIRECTIONS:
        agreed = []
        for i, unit in enumerate(units):
            by = [
                (name, hits[d][i])
                for name, (hits, _) in zip(names, per_reader)
                if i in hits[d]
            ]
            if len(by) < k:
                continue
            agreed.append(
                {
                    "start": unit.start,
                    "end": unit.end,
                    "quote": unit.quote,
                    "readers": [name for name, _ in by],
                    "shapes": sorted(
                        {j.get("name", "judgment") for _, js in by for j in js}
                    ),
                    # Each reader's strongest judgment on the unit, then their mean:
                    # one reader quoting a sentence twice does not count twice.
                    "weight": round(
                        sum(max(float(j.get("weight", 0.35)) for j in js) for _, js in by)
                        / len(by),
                        2,
                    ),
                }
            )
        out[d] = {
            "count": len(agreed),
            "per_1000_words": _density(len(agreed), n_words),
            "units": agreed,
        }
    return out


def consensus_signals(text: str, result: Mapping[str, Any]) -> list[Signal]:
    """One signal per consensus unit, anchored to the unit's own characters.

    This is what a multi-reader reading contributes to a report: not every reader's
    every flag -- most of which the next reader would not have made -- but the units
    they agree on, weighted by the mean of the agreeing readers' weights.

    >>> t = "One. Two. Three."
    >>> c = consensus(t, [[{"quote": "Two", "direction": "machine", "name": "x"}]] * 2)
    >>> s = consensus_signals(t, c)[0]
    >>> s.name, s.detector, s.span.quote, s.note
    ('reader-consensus', 'readers', 'Two.', 'flagged by 2 of 2 readers (reader 1, reader 2): x')
    """
    out = []
    for d in _DIRECTIONS:
        for u in result[d]["units"]:
            out.append(
                Signal(
                    name="reader-consensus",
                    direction=d,
                    weight=min(1.0, u["weight"]),
                    detector="readers",
                    value=len(u["readers"]),
                    note=(
                        f"flagged by {len(u['readers'])} of {result['n_readers']} "
                        f"readers ({', '.join(u['readers'])}): {', '.join(u['shapes'])}"
                    ),
                    # "token" is this package's level for a finding anchored to its own
                    # characters, which is what the renderers highlight.
                    span=Span.of(text, u["start"], u["end"], level="token"),
                )
            )
    out.sort(key=lambda s: s.span.start)
    return out


def pooled(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The same measure over several texts, pooled by words, with the per-text spread.

    Pooled means total consensus units over total words -- a long reference text counts
    for more than a short one, as it should. The per-text range is reported beside it,
    because two reference essays at 2.4 and 9.3 per 1,000 words say something a single
    pooled 5.0 hides.

    >>> a = {"k": 2, "n_readers": 2, "unit": "sentence", "n_words": 1000,
    ...      "machine": {"count": 2}, "human": {"count": 1}}
    >>> b = {**a, "n_words": 500, "machine": {"count": 5}, "human": {"count": 0}}
    >>> p = pooled([a, b])
    >>> p["machine"]
    {'count': 7, 'per_1000_words': 4.67, 'range': [2.0, 10.0]}
    >>> p["n_texts"], p["n_words"]
    (2, 1500)
    """
    if not results:
        raise ValueError("pooling needs at least one result")
    ks = {r["k"] for r in results}
    if len(ks) > 1:
        raise ValueError(f"cannot pool results taken at different k: {sorted(ks)}")
    n_words = sum(r["n_words"] for r in results)
    out: dict[str, Any] = {
        "k": ks.pop(),
        "unit": results[0]["unit"],
        "n_readers": sorted({r["n_readers"] for r in results}),
        "n_texts": len(results),
        "n_words": n_words,
        "per_words": PER_WORDS,
    }
    for d in _DIRECTIONS:
        count = sum(r[d]["count"] for r in results)
        each = [_density(r[d]["count"], r["n_words"]) for r in results if r["n_words"]]
        out[d] = {
            "count": count,
            "per_1000_words": _density(count, n_words),
            "range": [min(each), max(each)] if each else None,
        }
    return out
