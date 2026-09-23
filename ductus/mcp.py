"""The MCP surface: the same verbs the CLI dispatches, emitted as MCP tools.

There is **no second verb list here**, and that is the whole design. :data:`TOOL_REFS`
is *derived* from :data:`ductus.tools._dispatch_funcs` -- the same list ``cw`` builds
the CLI from -- so the two surfaces cannot drift apart. The roadmap's rule is that a
parity test between two surfaces means there are two implementations; the fix is to
have one list, not two lists and a test that watches them.

The refs are **strings**, resolved by ``py2mcp`` at call time, so ``ductus.tools``
never imports MCP and neither does the core. ``py2mcp`` lives in the ``[mcp]`` extra
and is imported only when a server is actually built.

Verbs marked :func:`ductus.tools.host_mutating` are left out. ``install_skills``
symlinks into an agent host's skills directory: a person typing it at a CLI chose to,
a remote caller did not necessarily. That filter reads a property declared at the
function's own definition, so it is still one list.

``gauge(out=...)`` writes a file, and is *not* excluded -- writing the report you asked
for is the verb doing its job. A deployed server that should not write anywhere is what
``middleware=`` is for; it is passed straight through, along with ``auth=``.

Run it::

    pip install 'ductus[mcp]'
    ductus-mcp                      # stdio, for a local agent host

>>> TOOL_REFS[:2]
('ductus.tools:gauge', 'ductus.tools:detectors')
>>> all(ref.startswith("ductus.tools:") for ref in TOOL_REFS)
True
>>> "ductus.tools:install_skills" in TOOL_REFS  # host-mutating, left out
False
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ductus.tools import _dispatch_funcs

__all__ = ["INSTRUCTIONS", "TOOL_REFS", "main", "mk_mcp"]

#: One ref per read-only verb, derived from the CLI's own list. Never hand-written.
TOOL_REFS: tuple[str, ...] = tuple(
    f"ductus.tools:{fn.__name__}"
    for fn in _dispatch_funcs
    if not getattr(fn, "mutates_host", False)
)

#: What the server tells a model about itself. The limits are here rather than in a
#: README because this is the only description an MCP client ever reads.
INSTRUCTIONS = """\
Gauge which parts of a text read as machine-written, with every finding anchored to
the exact characters that carry it.

This server never returns a percentage, a confidence, or a verdict about a person, and
a caller should not synthesise one from what it does return. It gives a lean in
[-1, +1], an evidence strength, a coarse label, and the signals behind them -- each
with a quote that can be checked against the text.

Its false-positive rate on human-written text is measured: with the default detectors,
6.0% of 350 human-written documents are called leans-machine, and every one of those is
wrong. A flagged *sentence* is much better evidence than a flagged *document* -- the
per-sentence rate is 0.4-2%. The bias runs toward formal, fluent, essayistic prose
rather than toward simple prose; in the measured corpus the native-speaker control was
the most-accused group.

"No findings" is a weak result, not a clean bill.
"""


def mk_mcp(
    *,
    name: str = "ductus",
    refs: Sequence[str] = TOOL_REFS,
    instructions: str = INSTRUCTIONS,
    middleware: Any = None,
    auth: Any = None,
):
    """Build an MCP server exposing ``refs`` as tools.

    ``middleware=`` and ``auth=`` pass straight through to ``py2mcp``. They are where
    a deployed connector attaches metering and authentication without the core
    learning that either exists.

    Raises :class:`ImportError` with an actionable message when the extra is missing.
    """
    try:
        from py2mcp import mk_mcp_from_refs
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "the MCP surface needs the [mcp] extra:\n"
            "    pip install 'ductus[mcp]'\n"
            "which installs py2mcp. The library and the CLI need neither."
        ) from e

    return mk_mcp_from_refs(
        refs,
        name=name,
        instructions=instructions,
        middleware=middleware,
        auth=auth,
    )


def main() -> None:  # pragma: no cover - a blocking server loop
    """Serve on stdio. The ``ductus-mcp`` console script."""
    mk_mcp().run()


if __name__ == "__main__":  # pragma: no cover
    main()
