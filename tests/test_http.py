"""The HTTP surface, tested by driving a real client rather than reading a schema.

Phase 3 learned this the hard way: under ``from __future__ import annotations`` the
schema layer beneath ``fastmcp`` dropped every keyword-only default, so every verb was
uncallable while the tool list and the JSON schema both looked perfect. A test that
inspected the schema would have passed. So every test here sends an actual request.

``qh`` turned out not to have that defect -- the first test below is the one that
establishes it, and it is worth keeping precisely because a future ``qh`` could
acquire it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ductus import tools
from ductus.http import ROUTED_FUNCS, mk_app

qh = pytest.importorskip("qh", reason="the HTTP surface needs the [http] extra")

from qh.testing import test_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with test_app(mk_app()) as c:
        yield c


# --------------------------------------------------------------------------- shape


def test_the_verb_list_is_derived_not_written():
    """The surface must not be able to drift from the CLI's list.

    Not a parity test between two lists -- there is only one list, and this asserts
    that fact. A parity test would mean there were two implementations.
    """
    expected = [f for f in tools._dispatch_funcs if not getattr(f, "mutates_host", False)]
    assert list(ROUTED_FUNCS) == expected
    assert tools.install_skills not in ROUTED_FUNCS


def test_the_core_does_not_import_http():
    """``import ductus`` must not pull in FastAPI, or the extra is not optional."""
    import subprocess
    import sys

    code = (
        "import sys, ductus, ductus.tools;"
        "assert 'fastapi' not in sys.modules, sorted(sys.modules)[:0] or 'fastapi';"
        "assert 'qh' not in sys.modules"
    )
    assert (
        subprocess.run([sys.executable, "-c", code], capture_output=True).returncode == 0
    )


# ------------------------------------------------------------------- driving it


def test_every_verb_is_callable_with_only_its_required_arguments(client):
    """The Phase 3 defect, checked for directly.

    ``gauge`` is keyword-only from its second parameter with six defaults. If the
    schema layer drops those defaults, this call fails with "missing required
    argument" while ``/openapi.json`` still looks correct.
    """
    assert client.post("/gauge", json={"source": "hello there"}).status_code == 200
    assert client.post("/detectors", json={}).status_code == 200
    assert client.post("/segmenters", json={}).status_code == 200
    assert client.post("/tells", json={}).status_code == 200


def test_gauge_json_round_trips(client):
    r = client.post(
        "/gauge", json={"source": "Great question! Let's delve in.", "format": "json"}
    )
    assert r.status_code == 200
    report = json.loads(r.json())
    assert report["schema_version"] == "1"
    assert report["document"]["label"] == "leans-machine"
    assert report["segments"][0]["signals"]


def test_the_optional_arguments_actually_arrive(client):
    """A default that is silently used instead of the value sent is the same bug."""
    r = client.post(
        "/gauge",
        json={"source": "One. Two. Three.", "format": "json", "segmenter": "sentence"},
    )
    assert json.loads(r.json())["segmenter"] == "sentence"

    r = client.post(
        "/gauge", json={"source": "x", "format": "json", "detectors": "tells"}
    )
    assert json.loads(r.json())["detectors"] == ["tells"]

    # The same parameter in its sequence spelling, since the annotation allows both.
    r = client.post(
        "/gauge",
        json={"source": "x", "format": "json", "detectors": ["tells", "forensic"]},
    )
    assert json.loads(r.json())["detectors"] == ["tells", "forensic"]


def test_tier_filter_arrives(client):
    r = client.post("/tells", json={"tier": "E"})
    assert {t["tier"] for t in r.json()} == {"E"}


def test_html_and_markdown_formats(client):
    html = client.post(
        "/gauge", json={"source": "Let's delve in.", "format": "html"}
    ).json()
    assert html.startswith("<!doctype html>")
    md = client.post("/gauge", json={"source": "Let's delve in."}).json()
    assert md.startswith("# Reading")


def test_a_bad_format_is_an_error_not_a_silent_default(client):
    assert client.post("/gauge", json={"source": "x", "format": "pdf"}).status_code >= 400


# ------------------------------------------------------- the filesystem is not ours


def test_a_remote_caller_cannot_read_a_file_from_the_server(client, tmp_path):
    """``source`` names a file at a CLI. Over HTTP that is an arbitrary file read."""
    local = tmp_path / "private.txt"
    local.write_text("content that belongs to whoever runs the server", encoding="utf-8")

    r = client.post("/gauge", json={"source": str(local), "format": "json"})
    assert r.status_code >= 400, "the server read its own filesystem for a stranger"
    assert "not available over HTTP" in r.text

    # And the guard is exact, not a guess at path-shaped strings: a string that
    # merely looks like a path, but names nothing, is ordinary text to be scored.
    r = client.post(
        "/gauge", json={"source": str(tmp_path / "no-such-file.txt"), "format": "json"}
    )
    assert r.status_code == 200


def test_a_remote_caller_cannot_write_a_file_on_the_server(client, tmp_path):
    target = tmp_path / "written_by_a_stranger.txt"
    r = client.post("/gauge", json={"source": "hello", "out": str(target)})
    assert r.status_code >= 400
    assert not target.exists()


def test_stdin_is_refused(client):
    """``-`` means stdin, which on a server is meaningless or a hang."""
    assert client.post("/gauge", json={"source": "-"}).status_code >= 400


def test_judgments_is_guarded_too(client, tmp_path):
    """It is a second path parameter, and the guard is driven by the declaration."""
    local = tmp_path / "judgments.json"
    local.write_text("[]", encoding="utf-8")
    r = client.post("/gauge", json={"source": "hello", "judgments": str(local)})
    assert r.status_code >= 400


def test_the_guard_is_generic_not_a_list_of_verbs():
    """A new verb declaring a path parameter is guarded with no edit to the surface."""
    from ductus.http import _guard
    from ductus.tools import host_paths

    @host_paths(where="write")
    def invented(text: str, *, where: str | None = None) -> str:
        Path(where).write_text(text) if where else None
        return text

    guarded = _guard(invented)
    assert guarded("fine") == "fine"
    with pytest.raises(ValueError, match="not available over HTTP"):
        guarded("bad", where="/anywhere")


def test_the_guard_can_be_turned_off_for_a_local_service(tmp_path):
    """The seam exists, because a loopback service for yourself is a real case."""
    local = tmp_path / "mine.txt"
    local.write_text("Sent it Friday. Two sites, not five.", encoding="utf-8")
    with test_app(mk_app(guard_host_paths=False)) as c:
        r = c.post("/gauge", json={"source": str(local), "format": "json"})
        assert r.status_code == 200
        assert json.loads(r.json())["n_chars"] == len(local.read_text())


# ---------------------------------------------------------------- what it tells you


def test_the_limits_travel_with_the_openapi_document(client):
    """An HTTP client reads the description and nothing else, so it must carry them."""
    described = client.get("/openapi.json").json()["info"]["description"]
    assert "6.0%" in described
    assert "formal, fluent" in described
    assert "weak result, not a clean bill" in described
    assert "%" not in described.replace("6.0%", "").replace("0.4-2%", "")


def test_no_percentage_anywhere_in_a_response(client):
    """The package's central invariant, checked on the wire."""
    report = json.loads(
        client.post(
            "/gauge", json={"source": "Let's delve into this tapestry.", "format": "json"}
        ).json()
    )
    assert "probability" not in json.dumps(report).lower()
    assert -1.0 <= report["document"]["lean"] <= 1.0
    assert report["calibration"].startswith("uncalibrated")


# ------------------------------------------------------------------- the ts client


def test_the_typed_client_is_generated_from_this_app():
    from ductus.http import export_client

    ts = export_client()
    assert "export class DuctusClient" in ts
    # Every routed verb, and nothing that is not routed.
    for fn in ROUTED_FUNCS:
        assert f"async {fn.__name__}(" in ts
    assert "async install_skills(" not in ts
    # The keyword-only defaults must be optional on the client too, or the frontend
    # has to pass all seven arguments to score a string.
    line = next(ln for ln in ts.splitlines() if "async gauge(" in ln)
    assert "source: string" in line and "format?: string" in line
