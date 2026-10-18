"""Several readers' judgments, the sentences they agree on, and a baseline to read it beside.

Every test runs on saved judgment files in ``tests/fixtures/readers/`` -- no network and
no model. The fixtures are small enough to count by hand, and the expected numbers below
were counted that way:

``draft.md`` (116 words) is read by three readers. Readers ``a`` and ``b`` both flag the
pattern-naming sentence and "The point is not speed but trust."; ``a`` and ``c`` both flag
"Time spent can't...". So three sentences reach k=2 and none reach k=3. Reader ``b``
also carries one quote that is not in the text, which must be dropped and counted.

``refs/old1.md`` (76 words) has one sentence both its readers flag; ``refs/old2.md``
(40 words) has none, and keeps its readers in a ``old2/`` subdirectory to exercise the
second naming convention.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ductus.consensus import consensus, pooled
from ductus.tools import _readers, baseline, gauge

FIX = Path(__file__).parent / "fixtures" / "readers"
DRAFT = FIX / "draft.md"
READERS = [str(FIX / f"draft.{r}.json") for r in "abc"]
REFS = [str(FIX / "refs" / "old1.md"), str(FIX / "refs" / "old2.md")]


def _consensus(**kw):
    readers = _readers(READERS)
    return consensus(
        DRAFT.read_text(encoding="utf-8"),
        [js for _, js in readers],
        names=[n for n, _ in readers],
        **kw,
    )


def test_per_reader_counts_are_reported_with_dropped_quotes():
    c = _consensus()
    assert [
        (r["name"], r["machine"], r["human"], r["dropped"]) for r in c["readers"]
    ] == [
        ("draft.a", 4, 1, 0),
        ("draft.b", 3, 1, 1),
        ("draft.c", 2, 1, 0),
    ]


def test_consensus_counts_only_sentences_k_readers_share():
    c = _consensus()
    assert c["n_words"] == 116
    assert c["machine"]["count"] == 3
    assert c["machine"]["per_1000_words"] == round(3000 / 116, 2)
    quotes = [u["quote"] for u in c["machine"]["units"]]
    assert quotes[0].startswith("This is a recurring pattern")
    assert quotes[1] == "Time spent can't by itself be a measure of care."
    assert quotes[2] == "The point is not speed but trust."
    assert c["machine"]["units"][1]["readers"] == ["draft.a", "draft.c"]
    # Human-leaning agreement is counted too: the instrument does not only accuse.
    assert [u["quote"] for u in c["human"]["units"]] == ["Marta found the bad checksum."]


def test_raising_k_only_ever_removes_sentences():
    assert _consensus(k=3)["machine"]["count"] == 0
    assert _consensus(k=1)["machine"]["count"] == 6  # the union


def test_k_larger_than_the_reader_count_is_refused():
    with pytest.raises(ValueError, match="needs at least 4 readers"):
        _consensus(k=4)


def test_every_consensus_unit_indexes_the_original_text():
    text = DRAFT.read_text(encoding="utf-8")
    c = _consensus(k=1)
    for d in ("machine", "human"):
        for u in c[d]["units"]:
            assert text[u["start"] : u["end"]] == u["quote"]


def test_gauge_with_several_readers_folds_in_only_the_consensus():
    report = json.loads(gauge(str(DRAFT), judgments=READERS, format="json"))
    judged = [
        s
        for seg in report["segments"]
        for s in seg["signals"]
        if s["detector"] in ("readers", "judge")
    ]
    assert {s["detector"] for s in judged} == {"readers"}
    assert sum(s["direction"] == "machine" for s in judged) == 3
    assert report["meta"]["readers"]["machine"]["count"] == 3


def test_a_single_reader_keeps_the_original_behaviour():
    one = json.loads(gauge(str(DRAFT), judgments=READERS[:1], format="json"))
    same = json.loads(gauge(str(DRAFT), judgments=READERS[0], format="json"))
    assert one == same
    assert one["meta"] == {}
    assert any(
        s["detector"] == "judge" for seg in one["segments"] for s in seg["signals"]
    )


def test_markdown_shows_readers_consensus_and_no_percentage():
    md = gauge(str(DRAFT), judgments=READERS)
    assert "## Readers" in md
    assert "| draft.b | 3 | 1 | 1 |" in md
    assert "3 machine-leaning, 25.9 per 1,000 words" in md
    assert "No baseline given" in md
    assert "%" not in md


def test_baseline_pools_reference_texts_by_words():
    b = json.loads(baseline(REFS))
    assert [t["source"] for t in b["texts"]] == ["old1.md", "old2.md"]
    assert [t["machine"]["count"] for t in b["texts"]] == [1, 0]
    assert b["n_words"] == 116
    assert b["machine"]["per_1000_words"] == round(1000 / 116, 2)
    assert b["machine"]["range"] == [0.0, round(1000 / 76, 2)]
    # Counts only: no sentence of a reference text leaves the function.
    assert "quote" not in json.dumps(b) and "boiler" not in json.dumps(b)


def test_baseline_needs_k_readers_per_text():
    with pytest.raises(ValueError, match="need at least k=3"):
        baseline(REFS, k=3)


def test_baseline_markdown_is_counts_and_words():
    md = baseline(REFS, format="markdown")
    assert md.startswith("# Baseline")
    assert "| old1.md | 76 | 2 | 13.2 |" in md
    assert "%" not in md


def test_gauge_sets_the_consensus_beside_the_baseline(tmp_path):
    ref = tmp_path / "baseline.json"
    baseline(REFS, out=str(ref))
    md = gauge(str(DRAFT), judgments=READERS, baseline=str(ref))
    assert "Next to the reference texts: 8.6 per 1,000 words" in md
    # Three readers here, two per reference text: said, not silently compared.
    assert "Not like-for-like" in md and "more readers agree more often" in md
    two = gauge(str(DRAFT), judgments=READERS[:2], baseline=str(ref))
    assert "Not like-for-like" not in two


def test_a_baseline_without_a_consensus_is_refused():
    with pytest.raises(ValueError, match="give judgments at least twice"):
        gauge(str(DRAFT), judgments=READERS[0], baseline="{}")


def test_pooling_refuses_mixed_k():
    a = {
        "k": 2,
        "n_readers": 2,
        "unit": "sentence",
        "n_words": 10,
        "machine": {"count": 1},
        "human": {"count": 0},
    }
    with pytest.raises(ValueError, match="different k"):
        pooled([a, {**a, "k": 3}])


def test_html_carries_the_readers_section():
    html = gauge(str(DRAFT), judgments=READERS, format="html")
    assert '<section class="rank readers">' in html
    assert "<b>Consensus, sentences flagged by at least 2 of 3 readers" in html


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "ductus", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )


def test_cli_accepts_repeated_judgments_and_a_baseline(tmp_path):
    ref = tmp_path / "baseline.json"
    r = _run("baseline", *REFS, "--out", str(ref))
    assert r.returncode == 0, r.stderr
    args = [a for path in READERS for a in ("--judgments", path)]
    r = _run("gauge", str(DRAFT), *args, "--baseline", str(ref))
    assert r.returncode == 0, r.stderr
    assert "| draft.a | 4 | 1 | 0 |" in r.stdout
    assert "| draft.c | 2 | 1 | 0 |" in r.stdout
    assert "Next to the reference texts" in r.stdout
    r = _run("gauge", str(DRAFT), *args, "-k", "3")
    assert "0 machine-leaning, 0.0 per 1,000 words" in r.stdout, r.stderr


# ------------------------------------------------- shapes that must not be guessed at


def test_a_file_beside_the_text_that_is_not_a_reader_is_an_error(tmp_path):
    """`baseline`'s own output written beside a text must not become a phantom reader."""
    import shutil

    for f in ("old1.md", "old1.a.json", "old1.b.json"):
        shutil.copy(FIX / "refs" / f, tmp_path / f)
    src = str(tmp_path / "old1.md")
    baseline([src], out=str(tmp_path / "old1.baseline.json"))
    with pytest.raises(ValueError, match="old1.baseline: not a reader's judgments"):
        baseline([src])


def test_a_sibling_texts_readers_are_not_borrowed(tmp_path):
    import shutil

    for f in ("old1.md", "old1.a.json", "old1.b.json"):
        shutil.copy(FIX / "refs" / f, tmp_path / f)
    (tmp_path / "old1.v2.md").write_text("Another text.", encoding="utf-8")
    (tmp_path / "old1.v2.x.json").write_text("[]", encoding="utf-8")
    b = json.loads(baseline([str(tmp_path / "old1.md")]))
    assert b["texts"][0]["readers"] == ["old1.a", "old1.b"]


def test_readers_can_be_wrapper_dicts_or_one_json_list_of_readers():
    wrapped = [json.loads((FIX / "draft.b.json").read_text())] * 2
    assert len(_readers(wrapped)) == 2
    many = json.dumps([json.loads(Path(r).read_text()) for r in READERS])
    assert [n for n, _ in _readers(many)] == ["reader 1", "reader 2", "reader 3"]


def test_mixing_records_and_readers_is_refused():
    record = {"quote": "Marta", "direction": "human"}
    with pytest.raises(ValueError, match="mixes single records with whole readers"):
        _readers([READERS[0], record])


def test_baseline_accepts_a_dict_and_a_previous_reading():
    b = json.loads(baseline(REFS))
    md = gauge(str(DRAFT), judgments=READERS[:2], baseline=b)
    assert "Next to the reference texts: 8.6" in md
    assert "Not like-for-like" not in md
    # Comparing a rewrite with the version before it: the earlier reading's meta.
    before = json.loads(gauge(str(DRAFT), judgments=READERS[:2], format="json"))
    md = gauge(str(DRAFT), judgments=READERS[:2], baseline=before["meta"]["readers"])
    assert "Next to the reference texts: 17.2 per 1,000 words" in md


def test_a_markdown_baseline_gets_a_clear_error():
    with pytest.raises(ValueError, match="must be the JSON from `ductus baseline`"):
        gauge(str(DRAFT), judgments=READERS, baseline=baseline(REFS, format="markdown"))


def test_k_below_one_is_refused_even_for_one_reader():
    with pytest.raises(ValueError, match="k must be at least 1"):
        gauge(str(DRAFT), judgments=READERS[0], k=0)
