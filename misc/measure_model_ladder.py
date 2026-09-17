"""Does the curvature detectors' verdict depend on which proxy model they run?

Phase 1 shipped CPU-sized defaults (``gpt2``; ``distilgpt2``/``gpt2``) and closed by
noting that the cheapest untried lever was a better proxy pair. This climbs that ladder
and reports whether the honest recommendation is model-dependent.

Run it (needs the ``[local]`` extra; each rung downloads on first use)::

    python misc/measure_model_ladder.py

**Falcon-7B is not on the ladder.** The Binoculars paper's own pair is
``tiiuae/falcon-7b`` / ``-instruct``: ~28GB for the two, and CPU inference on 7B
parameters puts a single fixture document in the minutes, which is neither runnable
here nor runnable by a reader on the hardware this package targets. The rungs below
span 124M to 1.5B, which is enough to answer *whether* model size moves the result;
it does not establish where the curve flattens. Anyone with a GPU should pass
``model=``/``observer=``/``performer=`` and find out -- that is what the seam is for.
"""

from __future__ import annotations

import gc
import json
import time
from functools import partial
from pathlib import Path

from ductus import gauge
from ductus.curvature import (
    _binoculars_profile,
    _fast_detect_profile,
    _load,
    binoculars,
    fast_detect_gpt,
)

FIXTURES = {
    "llmtrace": Path(__file__).parent.parent
    / "tests"
    / "fixtures"
    / "mixed_authorship.json",
    "roft": Path(__file__).parent.parent / "tests" / "fixtures" / "roft_boundary.json",
}

#: Rungs, smallest first. Binoculars needs observer and performer to be a *closely
#: related* pair sharing one tokenizer, so each rung stays inside the GPT-2 family.
RUNGS = {
    "fast-detect-gpt": [
        ("gpt2 (124M, the default)", partial(fast_detect_gpt, model="gpt2")),
        ("gpt2-large (774M)", partial(fast_detect_gpt, model="gpt2-large")),
        ("gpt2-xl (1.5B)", partial(fast_detect_gpt, model="gpt2-xl")),
    ],
    "binoculars": [
        (
            "distilgpt2/gpt2 (the default)",
            partial(binoculars, observer="distilgpt2", performer="gpt2"),
        ),
        (
            "gpt2/gpt2-large",
            partial(binoculars, observer="gpt2", performer="gpt2-large"),
        ),
        (
            "gpt2-large/gpt2-xl",
            partial(binoculars, observer="gpt2-large", performer="gpt2-xl"),
        ),
    ],
}


def release_models() -> None:
    """Drop every cached model between rungs.

    :func:`ductus.curvature._load` keeps models warm, which is what you want when a
    session scores several texts with one detector. A sweep is the opposite case: it
    touches four models, and holding all of them resident is ~10GB in float32, which
    on a CPU box means swapping rather than computing -- measured at 4 minutes of CPU
    per 35 minutes of wall clock before this was added.
    """
    _fast_detect_profile.cache_clear()
    _binoculars_profile.cache_clear()
    _load.cache_clear()
    gc.collect()


def ai_fraction(span, intervals) -> float:
    covered = sum(max(0, min(span.end, b) - max(span.start, a)) for a, b in intervals)
    return covered / max(1, span.length)


def score(detector, documents) -> tuple[int, int, int, int, int, float]:
    """``(machine hits, machine flagged, machine total, agreements, decisive, seconds)``."""
    started = time.perf_counter()
    hits = flagged = total = agree = decisive = 0
    for d in documents:
        report = gauge(d["text"], segmenter="sentence", detectors=[detector])
        for segment in report.segments:
            fraction = ai_fraction(segment.span, d["ai_char_intervals"])
            truth_machine, truth_human = fraction >= 0.8, fraction <= 0.2
            if not (truth_machine or truth_human):
                continue
            total += truth_machine
            if segment.lean != 0 and segment.signals:
                decisive += 1
                agree += (segment.lean > 0) == truth_machine
            if segment.label == "leans-machine":
                flagged += 1
                hits += truth_machine
    return hits, flagged, total, agree, decisive, time.perf_counter() - started


def main() -> None:
    for fixture, path in FIXTURES.items():
        documents = json.loads(path.read_text(encoding="utf-8"))["documents"]
        print(f"\n### {fixture} ({len(documents)} documents), segmenter 'sentence'\n")
        print(
            "| detector | proxy model | machine recall | precision | agreement | time |"
        )
        print("|---|---|---|---|---|---|")
        for name, rungs in RUNGS.items():
            for label, detector in rungs:
                release_models()
                h, f, t, a, d, secs = score(detector, documents)
                print(
                    f"| {name} | {label} | {_pct(h, t)} | {_pct(h, f)} | "
                    f"{_pct(a, d)} | {secs:.0f}s |",
                    flush=True,
                )


def _pct(num: int, den: int) -> str:
    """``3/8 (38%)``, or ``0/0 (—)`` rather than a percentage of nothing."""
    return f"{num}/{den} ({num / den:.0%})" if den else f"{num}/{den} (—)"


if __name__ == "__main__":
    main()
