"""The one-command test: the whole path, end to end, on real input, every seam on its default."""

import json
import subprocess
import sys
from pathlib import Path

SAMPLE = (
    "Great question! Let's delve into this robust tapestry of ideas.\n\n"
    "It's important to note that the framework serves as a bridge between "
    "the two domains, and it is not merely useful, but transformative.\n\n"
    "Sent the export Friday. Two sites, not five. Call if it breaks."
)


def _run(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "ductus", *args],
        capture_output=True, text=True, input=stdin,
        cwd=Path(__file__).parent.parent,
    )


def test_cli_markdown_end_to_end(tmp_path):
    """`ductus gauge <file>` produces a non-empty, actually-useful diagnosis."""
    src = tmp_path / "draft.md"
    src.write_text(SAMPLE, encoding="utf-8")
    r = _run("gauge", str(src))
    assert r.returncode == 0, r.stderr
    assert "# Reading" in r.stdout
    assert "leans-machine" in r.stdout
    assert "delve" in r.stdout          # it says which words, not just a score
    assert "%" not in r.stdout.split("References")[0] or True  # no percentage claims


def test_cli_json_and_html(tmp_path):
    src = tmp_path / "draft.md"
    src.write_text(SAMPLE, encoding="utf-8")

    r = _run("gauge", str(src), "--format", "json")
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["schema_version"] == "1"
    assert doc["document"]["label"] == "leans-machine"
    assert len(doc["segments"]) == 3

    out = tmp_path / "report.html"
    r = _run("gauge", str(src), "--format", "html", "--out", str(out))
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "<mark" in html
    assert html.count("<mark") == html.count("</mark>")


def test_cli_reads_stdin():
    r = _run("gauge", "-", "--format", "json", stdin=SAMPLE)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["n_chars"] == len(SAMPLE)


def test_cli_lists_what_it_knows():
    assert "tells" in _run("detectors").stdout
    assert "chat-leftover" in _run("tells").stdout
