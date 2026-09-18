"""Per-rule accounting: what each rule costs on human writing, and what it earns.

Phase 2 established that the deterministic layer over-flags formal, fluent prose and
named three rules that fire hardest on a native-speaker control. This turns that
observation into a table: for every rule and every deterministic detector signal, how
many *human-written* documents it falsely implicates, against how many of its matches
land inside machine-written ground truth on the two mixed fixtures.

A rule with false positives and no true positives is negative value and should be cut
or demoted. Which of those, and in which package, is decided by the gates in
``misc/docs/document-verdict-decision.md`` -- not here. This script only counts.

Run it (the human corpus downloads on first use)::

    python misc/measure_rules.py

**What counts as a true positive.** A signal is credited when its span lies inside a
ground-truth machine-written interval. Signals that argue *human* are counted
separately and are never called false positives on the human corpus -- arguing that a
person wrote a person's text is the detector being right.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ductus import gauge
from ductus.base import Signal

sys.path.insert(0, str(Path(__file__).parent))  # the corpus fetcher lives beside this
from measure_false_positives import BANDS, fetch_corpus, load_band  # noqa: E402

FIXTURES = {
    "llmtrace": Path(__file__).parent.parent
    / "tests"
    / "fixtures"
    / "mixed_authorship.json",
    "roft": Path(__file__).parent.parent / "tests" / "fixtures" / "roft_boundary.json",
}

#: Gate 2, from the decision doc: no true positives anywhere, and this many human
#: documents implicated, is negative value.
NEGATIVE_VALUE_HUMAN_DOCS = 5


@dataclass
class Tally:
    """What one rule did, everywhere it was looked at."""

    name: str
    detector: str
    direction: str = "machine"
    weight: float = 0.0
    human_docs: set[int] = field(default_factory=set)  # human docs it implicated
    human_hits: int = 0  # raw matches on human text
    true_positive: int = 0  # matches inside machine ground truth
    false_on_mixed: int = 0  # matches outside it, on the mixed fixtures

    @property
    def negative_value(self) -> bool:
        return (
            self.direction == "machine"
            and self.true_positive == 0
            and len(self.human_docs) >= NEGATIVE_VALUE_HUMAN_DOCS
        )

    def row(self) -> str:
        verdict = "**negative value**" if self.negative_value else ""
        if self.direction == "human":
            verdict = "argues human"
        return (
            f"| `{self.name}` | {self.detector} | {self.weight:.2f} | "
            f"{len(self.human_docs)} | {self.human_hits} | "
            f"{self.true_positive} | {self.false_on_mixed} | {verdict} |"
        )


def _inside_machine_span(signal: Signal, intervals) -> bool:
    """Whether a signal's span lies mostly inside machine-written ground truth."""
    span = signal.span
    if span is None or span.length == 0:
        return False
    covered = sum(max(0, min(span.end, b) - max(span.start, a)) for a, b in intervals)
    return covered / span.length >= 0.5


def tally_all(*, segmenter: str = "sentence") -> dict[str, Tally]:
    """Count every rule across the human corpus and both mixed fixtures."""
    tallies: dict[str, Tally] = {}

    def get(signal: Signal) -> Tally:
        key = f"{signal.detector}:{signal.name}"
        if key not in tallies:
            tallies[key] = Tally(
                name=signal.name, detector=signal.detector, direction=signal.direction
            )
        t = tallies[key]
        t.weight = max(t.weight, signal.weight)
        return t

    root = fetch_corpus()
    doc_index = 0
    for stem in BANDS.values():
        for text in load_band(root, stem):
            for signal in gauge(text, segmenter=segmenter).signals:
                t = get(signal)
                if signal.direction == "machine":
                    t.human_docs.add(doc_index)
                    t.human_hits += 1
            doc_index += 1

    for path in FIXTURES.values():
        for d in json.loads(path.read_text(encoding="utf-8"))["documents"]:
            for signal in gauge(d["text"], segmenter=segmenter).signals:
                t = get(signal)
                if signal.direction != "machine":
                    continue
                if _inside_machine_span(signal, d["ai_char_intervals"]):
                    t.true_positive += 1
                else:
                    t.false_on_mixed += 1

    return tallies


def main() -> None:
    tallies = tally_all()
    ordered = sorted(
        tallies.values(), key=lambda t: (-len(t.human_docs), -t.human_hits, t.name)
    )

    print("\n### Every deterministic rule, by what it costs on human writing\n")
    print(
        "| rule | detector | weight | human docs implicated | human matches | "
        "true positives | matched outside truth | |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for t in ordered:
        print(t.row())

    negative = [t for t in ordered if t.negative_value]
    print(
        f"\n**Negative value under Gate 2** (no true positives anywhere, "
        f"≥{NEGATIVE_VALUE_HUMAN_DOCS} human documents implicated): "
        + (", ".join(f"`{t.name}`" for t in negative) if negative else "none")
    )

    by_detector: dict[str, int] = defaultdict(int)
    for t in ordered:
        if t.direction == "machine":
            by_detector[t.detector] += len(t.human_docs)
    print(
        "\n**Human documents implicated, by detector**: "
        + ", ".join(
            f"{k} {v}" for k, v in sorted(by_detector.items(), key=lambda kv: -kv[1])
        )
    )


if __name__ == "__main__":
    main()
