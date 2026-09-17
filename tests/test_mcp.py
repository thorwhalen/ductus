"""The MCP surface. One verb list, and a server that actually answers.

The part that needs no extra installed is the part worth pinning hardest: that
:data:`ductus.mcp.TOOL_REFS` is *derived* from the CLI's own list rather than written
out again, and that importing ``ductus`` still costs no MCP dependency.

The rest builds a real server and calls tools through a real client, because a surface
that is only tested by inspecting its schema is a surface nobody has run. It skips
when the ``[mcp]`` extra is absent, which is how CI sees it.

No ``pytest-asyncio``: the async probes are driven with :func:`asyncio.run`.
"""

import asyncio
import json
import subprocess
import sys

import pytest

from ductus.mcp import TOOL_REFS, _resolve_annotations
from ductus.tools import _dispatch_funcs, host_mutating, install_skills


# ------------------------------------------------------------ always, no extras


def test_importing_ductus_does_not_import_mcp():
    """Installing the extra must not change what `import ductus` costs."""
    probe = (
        "import sys, ductus; "
        "assert 'py2mcp' not in sys.modules, 'ductus imported py2mcp'; "
        "assert 'fastmcp' not in sys.modules, 'ductus imported fastmcp'; "
        "print('ok')"
    )
    r = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=120
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_the_refs_are_derived_from_the_one_verb_list():
    """No second verb list. A parity test would mean there were two implementations.

    This is not a parity check between two hand-written lists -- it asserts that the
    refs *are* the dispatch list, so there is nothing that could drift.
    """
    expected = tuple(
        f"ductus.tools:{fn.__name__}"
        for fn in _dispatch_funcs
        if not getattr(fn, "mutates_host", False)
    )
    assert TOOL_REFS == expected
    assert TOOL_REFS  # and it is not accidentally empty


def test_host_mutating_verbs_are_left_out():
    """A CLI user typing `install-skills` chose to; a remote caller did not."""
    assert install_skills.mutates_host is True
    assert "ductus.tools:install_skills" not in TOOL_REFS
    for fn in _dispatch_funcs:
        if getattr(fn, "mutates_host", False):
            assert f"ductus.tools:{fn.__name__}" not in TOOL_REFS
        else:
            assert f"ductus.tools:{fn.__name__}" in TOOL_REFS


def test_host_mutating_is_declared_at_the_definition_site():
    """The marker is a property of the verb, not an entry in a list kept elsewhere."""

    @host_mutating
    def writes_something():
        pass

    assert writes_something.mutates_host is True

    def reads_something():
        pass

    assert getattr(reads_something, "mutates_host", False) is False


def test_resolving_annotations_recovers_keyword_only_defaults():
    """The upstream workaround, pinned so its removal is a deliberate act.

    Under `from __future__ import annotations` the schema layer under fastmcp reads
    annotations as strings and drops every keyword-only default, which would make
    every verb in this package uncallable over MCP. See `ductus.mcp._resolve_annotations`.
    """

    def verb(a: "int", *, b: "str" = "bee") -> "str":
        return f"{a}{b}"

    assert verb.__annotations__["b"] == "str"
    _resolve_annotations(verb)
    assert verb.__annotations__["b"] is str
    assert verb.__annotations__["a"] is int
    assert verb(1) == "1bee"  # behaviour is untouched


def test_the_instructions_carry_the_limits():
    """An MCP client reads this and nothing else. The caveats have to be in it."""
    from ductus.mcp import INSTRUCTIONS

    lowered = INSTRUCTIONS.lower()
    assert "never returns a percentage" in lowered
    assert "false-positive rate" in lowered
    assert "one document in five" in lowered
    assert "sentence" in lowered and "document" in lowered
    assert "not a clean bill" in lowered


# --------------------------------------------------------------- needs the extra


@pytest.fixture(scope="module")
def server():
    """A real server, or a skip. Never a failure for a missing optional dependency."""
    pytest.importorskip("py2mcp", reason="the [mcp] extra is not installed")
    pytest.importorskip("fastmcp", reason="the [mcp] extra is not installed")
    from ductus.mcp import mk_mcp

    return mk_mcp()


def _call(server, tool, args):
    """Call one tool through a real client and return its parsed payload."""
    from fastmcp import Client

    async def go():
        async with Client(server) as client:
            result = await client.call_tool(tool, args)
            return result.content[0].text

    return asyncio.run(go())


def test_the_server_exposes_exactly_the_derived_refs(server):
    from fastmcp import Client

    async def go():
        async with Client(server) as client:
            return sorted(t.name for t in await client.list_tools())

    assert asyncio.run(go()) == sorted(r.split(":")[1] for r in TOOL_REFS)


def test_gauge_answers_over_mcp(server):
    """The one-command test for this surface, end to end through a client."""
    payload = _call(
        server,
        "gauge",
        {
            "source": "Great question! Let's delve into this robust tapestry of ideas.",
            "format": "json",
        },
    )
    report = json.loads(payload)
    assert report["document"]["label"] == "leans-machine"
    assert report["schema_version"] == "1"
    assert "uncalibrated" in report["calibration"]
    assert report["segments"][0]["signals"], "no evidence came back with the verdict"


def test_the_optional_arguments_really_are_optional(server):
    """The upstream defect this surface tripped over, asserted at the surface.

    Every one of `gauge`'s keyword arguments has a default; a caller supplying only
    `source` must get a report, not a validation error naming five missing arguments.
    """
    payload = _call(server, "gauge", {"source": "Sent the export Friday."})
    assert payload.startswith("# Reading")


def test_the_read_only_verbs_answer(server):
    assert json.loads(_call(server, "segmenters", {})) == [
        "paragraph",
        "sentence",
        "document",
    ]
    assert len(json.loads(_call(server, "detectors", {}))) >= 4
    assert {t["tier"] for t in json.loads(_call(server, "tells", {"tier": "E"}))} == {"E"}


def test_install_skills_is_not_reachable(server):
    """The host-mutating verb must not be callable over this surface."""
    from fastmcp import Client

    async def go():
        async with Client(server) as client:
            return [t.name for t in await client.list_tools()]

    assert "install_skills" not in asyncio.run(go())
