"""Measure a detector set against the LLMTrace fixture. The Phase 1 gate lives here.

Run it directly; it needs the ``[local]`` extra and downloads the proxy models on
first use::

    python misc/measure_detectors.py              # both fixtures
    python misc/measure_detectors.py roft         # just one

The criterion is fixed before the numbers are looked at, and is stated in
``misc/docs/phase-1-results.md``:

    A detector set beats the baseline when it correctly flags **strictly more**
    machine-written decisive segments, **without** its machine-side precision
    falling below the baseline's.

Recall is what Phase 1 exists to fix; the precision floor is what stops recall being
bought with false accusations. Numbers that do not clear it are reported, not tuned.

A *decisive* segment is one the ground truth is unambiguous about: at least 80% of
its characters machine-written, or at most 20%. Segments straddling a boundary are
excluded, exactly as ``tests/test_ground_truth.py`` excludes them -- there is no
clean label to score them against.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ductus import gauge
from ductus.base import Segment

FIXTURES = {
    # Interleaved machine spans written to fill gaps in human prose -- close to a
    # worst case for a perplexity method, because the machine text was written to
    # match its surroundings.
    "llmtrace": Path(__file__).parent.parent
    / "tests"
    / "fixtures"
    / "mixed_authorship.json",
    # One human prefix, then a machine continuation: a single boundary, and a fairer
    # test of the same detectors. Different ground-truth shape on purpose.
    "roft": Path(__file__).parent.parent / "tests" / "fixtures" / "roft_boundary.json",
}

DETECTOR_SETS: dict[str, list[str]] = {
    "deterministic (baseline)": ["tells", "forensic", "rhetoric", "rhythm"],
    "fast-detect-gpt": ["fast-detect-gpt"],
    "binoculars": ["binoculars"],
    "both model-based": ["fast-detect-gpt", "binoculars"],
    "deterministic + model-based": [
        "tells",
        "forensic",
        "rhetoric",
        "rhythm",
        "fast-detect-gpt",
        "binoculars",
    ],
}


@dataclass(frozen=True)
class Score:
    """What one detector set did on the fixture."""

    name: str
    signals: int
    machine_hits: int  # decisive machine segments flagged machine
    machine_total: int  # decisive machine segments in the fixture
    machine_flagged: int  # segments flagged machine, right or wrong
    human_hits: int
    human_total: int
    human_flagged: int
    agreements: int  # decisive segments whose lean pointed the right way
    decisive: int  # decisive segments with any lean at all
    seconds: float

    @property
    def machine_recall(self) -> float:
        return self.machine_hits / self.machine_total if self.machine_total else 0.0

    @property
    def machine_precision(self) -> float:
        return self.machine_hits / self.machine_flagged if self.machine_flagged else 0.0

    @property
    def human_recall(self) -> float:
        return self.human_hits / self.human_total if self.human_total else 0.0

    @property
    def human_precision(self) -> float:
        return self.human_hits / self.human_flagged if self.human_flagged else 0.0

    @property
    def agreement(self) -> float:
        """Of decisive segments the set had any opinion about, how often it was right.

        The metric ``tests/test_ground_truth.py`` already uses. Reported beside
        precision because precision over a denominator of one is not a measurement.
        """
        return self.agreements / self.decisive if self.decisive else 0.0

    def row(self) -> str:
        return (
            f"| {self.name} | {self.signals} | "
            f"{self.machine_hits}/{self.machine_total} "
            f"({self.machine_recall:.0%}) | "
            f"{self.machine_hits}/{self.machine_flagged} "
            f"({self.machine_precision:.0%}) | "
            f"{self.human_hits}/{self.human_total} ({self.human_recall:.0%}) | "
            f"{self.human_hits}/{self.human_flagged} ({self.human_precision:.0%}) | "
            f"{self.agreements}/{self.decisive} ({self.agreement:.0%}) | "
            f"{self.seconds:.0f}s |"
        )


def ai_fraction(segment: Segment, intervals) -> float:
    """How much of a segment the ground truth says was machine-written."""
    span = segment.span
    covered = sum(max(0, min(span.end, b) - max(span.start, a)) for a, b in intervals)
    return covered / max(1, span.length)


def measure(name: str, detectors: list[str], documents, *, segmenter: str) -> Score:
    """Run one detector set over every document and tally decisive segments."""
    started = time.perf_counter()
    signals = 0
    m_hits = m_total = m_flagged = 0
    h_hits = h_total = h_flagged = 0
    agreements = decisive = 0

    for d in documents:
        report = gauge(d["text"], segmenter=segmenter, detectors=detectors)
        signals += len(report.signals)
        for segment in report.segments:
            fraction = ai_fraction(segment, d["ai_char_intervals"])
            truth_machine = fraction >= 0.8
            truth_human = fraction <= 0.2
            if not (truth_machine or truth_human):
                continue  # straddles a boundary: no clean label
            m_total += truth_machine
            h_total += truth_human
            if segment.lean != 0 and segment.signals:
                decisive += 1
                agreements += (segment.lean > 0) == truth_machine
            if segment.label == "leans-machine":
                m_flagged += 1
                m_hits += truth_machine
            elif segment.label == "leans-human":
                h_flagged += 1
                h_hits += truth_human

    return Score(
        name=name,
        signals=signals,
        machine_hits=m_hits,
        machine_total=m_total,
        machine_flagged=m_flagged,
        human_hits=h_hits,
        human_total=h_total,
        human_flagged=h_flagged,
        agreements=agreements,
        decisive=decisive,
        seconds=time.perf_counter() - started,
    )


def main() -> None:
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")] or list(FIXTURES)
    segmenters = (
        ("sentence",) if "--sentence-only" in sys.argv else ("sentence", "paragraph")
    )
    for fixture in wanted:
        documents = json.loads(FIXTURES[fixture].read_text(encoding="utf-8"))["documents"]
        for segmenter in segmenters:
            print(
                f"\n### {fixture} — segmenter {segmenter!r} "
                f"({len(documents)} documents)\n"
            )
            print(
                "| detector set | signals | machine recall | machine precision "
                "| human recall | human precision | agreement | time |"
            )
            print("|---|---|---|---|---|---|---|---|")
            baseline = None
            for name, detectors in DETECTOR_SETS.items():
                score = measure(name, detectors, documents, segmenter=segmenter)
                baseline = baseline or score
                print(score.row(), flush=True)
                if score is not baseline:
                    beats = (
                        score.machine_hits > baseline.machine_hits
                        and score.machine_precision >= baseline.machine_precision
                    )
                    print(f"<!-- gate: {name} beats baseline = {beats} -->", flush=True)


if __name__ == "__main__":
    main()
