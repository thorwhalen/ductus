"""The frontend's TypeScript is generated from this package's Python, and stays that way.

`frontend/src/generated/` is committed so `npm install && npm run dev` needs no Python
toolchain. That convenience is only safe if the committed files cannot quietly fall
behind the Python they were generated from — which is what this module is for.

The claim being defended is the one the whole surface design rests on: **there is one
source of truth and the rest is emitted from it.** A hand-written TypeScript `Report`
interface would be a second description of the same thing, in a second language, free to
drift. So there isn't one, and a renamed dataclass field is a failing test here rather
than an `undefined` someone finds in a browser three weeks later.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("qh", reason="generating the frontend sources needs the [http] extra")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "misc"))

from generate_frontend_sources import generated_sources  # noqa: E402


def test_the_committed_sources_match_what_the_python_produces():
    """The guard. Run `python misc/generate_frontend_sources.py` if this fails."""
    stale = []
    for path, expected in generated_sources().items():
        assert path.exists(), (
            f"{path} is missing -- run misc/generate_frontend_sources.py"
        )
        if path.read_text(encoding="utf-8") != expected:
            stale.append(path.relative_to(REPO))
    assert not stale, (
        "these generated files no longer match the Python they come from: "
        f"{', '.join(str(p) for p in stale)}. "
        "Run `python misc/generate_frontend_sources.py` and commit the result."
    )


def test_every_dataclass_field_reaches_typescript():
    """A field the generator cannot express must fail loudly, never become `any`."""
    import dataclasses

    from ductus import base
    from ductus.http import _REPORT_TYPES, export_types

    ts = export_types()
    for name in _REPORT_TYPES:
        for field in dataclasses.fields(getattr(base, name)):
            assert f"  {field.name}:" in ts, f"{name}.{field.name} is missing"
    assert ": any" not in ts, "a field fell through to `any`"


def test_an_unknown_annotation_raises_rather_than_guessing():
    from ductus.http import _ts_type

    with pytest.raises(ValueError, match="no TypeScript type"):
        _ts_type("SomeTypeNobodyTaughtItAbout")


def test_the_closed_vocabularies_are_read_from_the_module():
    """Adding a label must reach the frontend without anyone editing the generator."""
    from ductus.base import DIRECTIONS, LABELS
    from ductus.http import export_types

    ts = export_types()
    for label in LABELS:
        assert f"'{label}'" in ts
    for direction in DIRECTIONS:
        assert f"'{direction}'" in ts


def test_the_client_covers_every_routed_verb():
    from ductus.http import ROUTED_FUNCS, export_client

    ts = export_client()
    for fn in ROUTED_FUNCS:
        assert f"async {fn.__name__}(" in ts
    assert "install_skills" not in ts


def test_the_ui_mount_is_optional():
    """A wheel with no built frontend still serves every verb."""
    from qh.testing import test_app

    from ductus.http import mk_app

    with test_app(mk_app(ui=None)) as client:
        assert client.post("/segmenters", json={}).status_code == 200


def test_a_named_ui_directory_that_is_not_there_is_an_error(tmp_path):
    """Silence is right for the default; a path someone typed must not be ignored."""
    from ductus.http import mk_app

    with pytest.raises(FileNotFoundError):
        mk_app(ui=str(tmp_path / "nope"))


def test_a_built_ui_is_served_at_the_root(tmp_path):
    from qh.testing import test_app

    from ductus.http import mk_app

    (tmp_path / "index.html").write_text("<!doctype html><p>hi", encoding="utf-8")
    with test_app(mk_app(ui=str(tmp_path))) as client:
        assert client.get("/").status_code == 200
        assert "hi" in client.get("/").text
        # ...and the API is still reachable underneath it.
        assert client.post("/segmenters", json={}).status_code == 200


def test_the_ui_directory_can_come_from_the_environment(tmp_path, monkeypatch):
    """The seam for a deployment that built the assets somewhere else."""
    from qh.testing import test_app

    from ductus.http import mk_app

    (tmp_path / "index.html").write_text("<!doctype html><p>from env", encoding="utf-8")
    monkeypatch.setenv("DUCTUS_UI_DIR", str(tmp_path))
    with test_app(mk_app()) as client:
        assert "from env" in client.get("/").text
