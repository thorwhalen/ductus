"""False-positive rate on human-written text, by writer proficiency. The Phase 2 headline.

This is the number that decides whether this package can be used responsibly, and it
matters more than any recall figure. Phase 1 found that *every* false machine flag the
model-based detectors produced was plain human prose -- casual email, wire-service
sport, flat narration. That is the Liang et al. failure mode, and the only honest
response is to measure our own tooling against the population it hurts.

Run it::

    python misc/measure_false_positives.py                 # deterministic default
    python misc/measure_false_positives.py --blind         # the pre-Phase-2 scorer
    python misc/measure_false_positives.py --local         # the [local] detectors
    python misc/measure_false_positives.py --sweep         # how REFERENCE_CHARS was chosen
    python misc/measure_false_positives.py --pair-check    # binoculars, two proxy pairs

**The corpus is not vendored, and cannot be.** Cambridge English Write & Improve and
LOCNESS are released for non-commercial research use with no redistribution, so this
script downloads them on first run into ``~/.local/share/ductus/corpora/`` -- never
into the repository. The *numbers* are committed, in ``misc/docs/phase-2-results.md``;
the corpus is fetched by whoever wants to reproduce them. Measuring a corpus does not
require vendoring it.

Why this corpus: it is the closest license-obtainable analogue of the TOEFL11 essays
Liang et al. used, and it is better in one respect -- every text carries a **CEFR
level**, so the false-positive rate can be reported *by proficiency band* against a
native-speaker control from LOCNESS, rather than as one aggregate number that hides
which writers pay for it.

    A   beginner        (CEFR A1-A2)   non-native
    B   intermediate    (CEFR B1-B2)   non-native
    C   advanced        (CEFR C1-C2+)  non-native
    N   native control  (LOCNESS)

Every document here was written by a person. Any ``leans-machine`` verdict is wrong.
"""

from __future__ import annotations

import json
import sys
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ductus import gauge
from ductus.score import aggregate as length_blind_aggregate
from ductus.score import density_aggregate

#: Non-commercial research licence, no redistribution. Fetched, never committed.
CORPUS_URL = (
    "https://www.cl.cam.ac.uk/research/nl/bea2019st/data/wi+locness_v2.1.bea19.tar.gz"
)

#: Downloaded data lives under the user's data dir, never in the app directory.
CACHE = Path.home() / ".local" / "share" / "ductus" / "corpora"

BANDS = {
    "A (beginner, non-native)": "A.dev",
    "B (intermediate, non-native)": "B.dev",
    "C (advanced, non-native)": "C.dev",
    "N (native control)": "N.dev",
}

LICENCE_NOTICE = """
This script is about to download the BEA-2019 W&I+LOCNESS corpus from
    {url}
It is released for NON-COMMERCIAL research and educational purposes only, and may not
be redistributed. By downloading it you accept those terms; see the licence files in
the archive. It is cached under {cache} and is never written into this repository.
"""


def fetch_corpus() -> Path:
    """Download and unpack the corpus on first use; reuse the cache afterwards."""
    root = CACHE / "wi+locness"
    if (root / "json" / "A.dev.json").is_file():
        return root
    print(LICENCE_NOTICE.format(url=CORPUS_URL, cache=CACHE), file=sys.stderr)
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / "wi+locness_v2.1.bea19.tar.gz"
    if not archive.is_file():
        print(f"downloading {CORPUS_URL} ...", file=sys.stderr)
        urllib.request.urlretrieve(CORPUS_URL, archive)
    with tarfile.open(archive) as tar:
        # `filter="data"` refuses absolute paths, parent traversal and special files.
        # It is the default from 3.14 and unavailable before 3.12, hence the guard.
        if sys.version_info >= (3, 12):
            tar.extractall(CACHE, filter="data")
        else:
            tar.extractall(CACHE)
    return root


def load_band(root: Path, stem: str) -> list[str]:
    """The texts of one CEFR band. Every one of them was written by a person."""
    path = root / "json" / f"{stem}.json"
    return [
        json.loads(line)["text"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@dataclass(frozen=True)
class Rate:
    """How often a detector set accused a human writer."""

    band: str
    documents: int
    accused: int  # documents labelled leans-machine -- always wrong here
    defended: int  # documents labelled leans-human -- right, and worth knowing
    silent: int  # no evidence either way
    segments: int
    segments_accused: int

    @property
    def fpr(self) -> float:
        return self.accused / self.documents if self.documents else 0.0

    @property
    def segment_fpr(self) -> float:
        return self.segments_accused / self.segments if self.segments else 0.0

    def row(self) -> str:
        return (
            f"| {self.band} | {self.documents} | "
            f"**{self.accused}/{self.documents} ({self.fpr:.1%})** | "
            f"{self.defended} | {self.silent} | "
            f"{self.segments_accused}/{self.segments} ({self.segment_fpr:.1%}) |"
        )


def measure_band(
    band: str, texts: list[str], detectors, *, segmenter: str, aggregate
) -> Rate:
    """Run one detector set over one band and count the accusations."""
    accused = defended = silent = segments = segments_accused = 0
    for text in texts:
        report = gauge(
            text, segmenter=segmenter, detectors=detectors, aggregate=aggregate
        )
        label = report.document.label
        accused += label == "leans-machine"
        defended += label == "leans-human"
        silent += label in ("no-evidence", "uncertain")
        segments += len(report.segments)
        segments_accused += sum(s.label == "leans-machine" for s in report.segments)
    return Rate(band, len(texts), accused, defended, silent, segments, segments_accused)


def sweep(bands: dict[str, list[str]]) -> None:
    """How :data:`ductus.score.REFERENCE_CHARS` was chosen, and what it cost.

    The constant is selected **on the human corpus** -- the population it exists to
    protect -- and the cost is then read off the two mixed fixtures, which the
    selection never looks at. Reported in full rather than as a single winning row,
    because the choice is a judgement about a trade and a reader may weigh it
    differently.

    The caveat that decided it: every fixture document is under ~1600 characters, which
    is below where the normalisation starts to bite. So the *benefit* is measured on
    long documents and the *cost* only on short ones, and the honest response to an
    asymmetry like that is to take the least aggressive setting that does the work.
    """
    from ductus import score

    fixtures = {
        name: json.loads(path.read_text(encoding="utf-8"))["documents"]
        for name, path in (
            (
                "llmtrace",
                Path(__file__).parent.parent
                / "tests"
                / "fixtures"
                / "mixed_authorship.json",
            ),
            (
                "roft",
                Path(__file__).parent.parent
                / "tests"
                / "fixtures"
                / "roft_boundary.json",
            ),
        )
    }

    def machine_hits(documents, aggregate) -> int:
        found = 0
        for d in documents:
            report = gauge(d["text"], segmenter="sentence", aggregate=aggregate)
            for seg in report.segments:
                covered = sum(
                    max(0, min(seg.span.end, b) - max(seg.span.start, a))
                    for a, b in d["ai_char_intervals"]
                )
                if (
                    seg.label == "leans-machine"
                    and covered / max(1, seg.span.length) >= 0.8
                ):
                    found += 1
        return found

    original = score.REFERENCE_CHARS
    print(
        "\n### choosing REFERENCE_CHARS — selected on human text, cost read off the fixtures\n"
    )
    print("| REFERENCE_CHARS | A | B | C | N | all human | llmtrace hits | roft hits |")
    print("|---|---|---|---|---|---|---|---|")
    for reference in (None, 4000, 2000, 1500, 1000, 750, 500):
        if reference is None:
            aggregate, label = length_blind_aggregate, "length-blind (pre-Phase-2)"
        else:
            score.REFERENCE_CHARS = reference
            aggregate, label = density_aggregate, str(reference)
        per_band, accused, texts = [], 0, 0
        for band_texts in bands.values():
            n = sum(
                gauge(t, segmenter="sentence", aggregate=aggregate).document.label
                == "leans-machine"
                for t in band_texts
            )
            per_band.append(f"{n}/{len(band_texts)} ({n / len(band_texts):.0%})")
            accused += n
            texts += len(band_texts)
        hits = {k: machine_hits(v, aggregate) for k, v in fixtures.items()}
        print(
            f"| {label} | {' | '.join(per_band)} | "
            f"**{accused}/{texts} ({accused / texts:.1%})** | "
            f"{hits['llmtrace']} | {hits['roft']} |",
            flush=True,
        )
    score.REFERENCE_CHARS = original


def main() -> None:
    use_local = "--local" in sys.argv
    aggregate = length_blind_aggregate if "--blind" in sys.argv else density_aggregate
    scorer = "length-blind aggregate" if "--blind" in sys.argv else "density_aggregate"
    root = fetch_corpus()
    bands = {name: load_band(root, stem) for name, stem in BANDS.items()}

    if "--sweep" in sys.argv:
        sweep(bands)
        return

    # The model-based detectors are measured ALONE, not stacked on the deterministic
    # ones, so that a bias can be attributed to the mechanism that produced it. They
    # need a reference distribution within the document, so sentence granularity is
    # the only one that gives them anything to work with on texts this short.
    if "--pair-check" in sys.argv:
        # A stronger proxy pair may find more machine text AND accuse more humans.
        # Promoting one on recall alone would contradict this whole document, so the
        # candidate default is measured here before it is promoted.
        from functools import partial

        from ductus.curvature import binoculars

        sets = {
            "binoculars distilgpt2/gpt2 (current default)": [
                partial(binoculars, observer="distilgpt2", performer="gpt2")
            ],
            "binoculars gpt2/gpt2-large (candidate)": [
                partial(binoculars, observer="gpt2", performer="gpt2-large")
            ],
        }
        segmenters = ("sentence",)
    elif use_local:
        sets: dict[str, list[str] | None] = {
            "fast-detect-gpt alone": ["fast-detect-gpt"],
            "binoculars alone": ["binoculars"],
            "both model-based alone": ["fast-detect-gpt", "binoculars"],
        }
        segmenters = ("sentence",)
    else:
        sets = {"deterministic (default)": None}
        segmenters = ("paragraph", "sentence")

    for segmenter in segmenters:
        for name, detectors in sets.items():
            print(f"\n### {name} — segmenter {segmenter!r}, {scorer}\n", flush=True)
            print(
                "| band | texts | **false accusations** | called human | "
                "no evidence | segment-level |"
            )
            print("|---|---|---|---|---|---|")
            for band, texts in bands.items():
                rate = measure_band(
                    band, texts, detectors, segmenter=segmenter, aggregate=aggregate
                )
                print(rate.row(), flush=True)


if __name__ == "__main__":
    main()
