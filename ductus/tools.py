"""The verb SSOT: plain functions, JSON-ready in, JSON-ready out.

Deliberately surface-agnostic. Nothing here prints, exits, or knows what a CLI,
an MCP server or an HTTP request is -- ``__main__`` runs these through ``cw``,
``py2mcp.mk_mcp_from_refs(['ductus.tools:gauge', ...])`` would expose the same
functions as MCP tools, and ``qh.mk_app`` would serve them over HTTP, all from
this one list. Adding a surface never means writing a second implementation.

>>> out = gauge("Great question! Let's delve in.", format="json")
>>> import json; json.loads(out)["document"]["label"]
'leans-machine'
>>> [d["name"] for d in detectors()][:2]
['tells', 'forensic']
"""

from __future__ import annotations

import json
import os
from typing import Any, Sequence

from ductus.base import Signal, Span
from ductus.core import gauge as _gauge
from ductus.detect import DETECTORS
from ductus.render import to_html, to_json, to_markdown
from ductus.segment import SEGMENTERS

__all__ = ["gauge", "detectors", "tells", "segmenters", "install_skills", "_dispatch_funcs"]

FORMATS = ("markdown", "json", "html")


def _read_source(source: str) -> str:
    """``source`` is a path if one exists, otherwise the text itself. ``-`` is stdin.

    >>> _read_source("not a path, just words")
    'not a path, just words'
    """
    if source == "-":
        import sys
        return sys.stdin.read()
    if len(source) < 4096 and os.path.isfile(source):
        with open(source, encoding="utf-8") as f:
            return f.read()
    return source


def _signals_from_judgments(text: str, judgments: Any) -> list[Signal]:
    """Turn judgment records into signals anchored in ``text``.

    A judgment is a dict with ``direction`` and one of ``quote`` or
    ``start``/``end``, plus optional ``name``, ``weight`` and ``note``. This is
    how an agent's reading of the text gets folded in beside the deterministic
    detectors -- the shipped skills write this file.

    >>> t = "The cat sat on the mat."
    >>> s = _signals_from_judgments(t, [{"quote": "cat", "direction": "machine",
    ...                                  "note": "an example", "weight": 0.4}])
    >>> s[0].span.quote, s[0].detector
    ('cat', 'judge')
    """
    if isinstance(judgments, str):
        judgments = json.loads(_read_source(judgments))
    if isinstance(judgments, dict):
        judgments = judgments.get("judgments", judgments.get("findings", []))

    out: list[Signal] = []
    for j in judgments or ():
        if "quote" in j:
            start = text.find(j["quote"])
            if start < 0:
                continue  # the quote no longer occurs: drop it rather than mis-anchor
            end = start + len(j["quote"])
        else:
            start, end = int(j["start"]), int(j["end"])
        out.append(Signal(
            name=j.get("name", "judgment"),
            direction=j["direction"],
            weight=float(j.get("weight", 0.35)),
            detector=j.get("detector", "judge"),
            value=j.get("value"),
            note=j.get("note", ""),
            span=Span.of(text, start, end, level="token"),
        ))
    return out


def gauge(
    source: str,
    *,
    format: str = "markdown",
    segmenter: str = "paragraph",
    detectors: str | Sequence[str] | None = None,
    judgments: str | None = None,
    out: str | None = None,
    title: str = "Reading",
) -> str:
    """Gauge how machine-written a text reads, and render the result.

    ``source`` is a file path, a literal string, or ``-`` for stdin.
    ``format`` is one of markdown, json, html. ``detectors`` is a comma-separated
    subset of the available detectors. ``judgments`` is a path to a JSON file of
    an agent's own readings, folded in alongside the deterministic ones. With
    ``out``, the result is written there and a one-line summary is returned.

    >>> gauge("Sent it Friday. Two sites, not five.").splitlines()[0]
    '# Reading'
    """
    if format not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}, got {format!r}")
    if isinstance(detectors, str):
        detectors = [d.strip() for d in detectors.split(",") if d.strip()]

    text = _read_source(source)
    extra = _signals_from_judgments(text, judgments) if judgments else ()
    report = _gauge(text, segmenter=segmenter, detectors=detectors, extra_signals=extra)

    if format == "json":
        rendered = to_json(report)
    elif format == "html":
        rendered = to_html(report, text=text, subtitle=f"{report.n_chars} characters")
    else:
        rendered = to_markdown(report, text=text, title=title)

    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(rendered)
        return (f"wrote {out} ({len(rendered)} bytes) -- {report.document.label}, "
                f"lean {report.document.lean:+.2f}, {len(report.signals)} signal(s)")
    return rendered


def detectors() -> list[dict[str, str]]:
    """The available detectors and what each one looks at.

    >>> {d["name"] for d in detectors()} == set(DETECTORS)
    True
    """
    return [
        {"name": name, "summary": (fn.__doc__ or "").strip().splitlines()[0]}
        for name, fn in DETECTORS.items()
    ]


def segmenters() -> list[str]:
    """The available ways of cutting the text into scored units.

    >>> segmenters()
    ['paragraph', 'sentence', 'document']
    """
    return list(SEGMENTERS)


def tells(*, tier: str | None = None) -> list[dict[str, Any]]:
    """The tells catalogue, optionally filtered to one tier (E, W or S).

    >>> len(tells()) > 10
    True
    >>> {t["tier"] for t in tells(tier="E")}
    {'E'}
    """
    from ductus.tells import load_rules

    return [
        {"id": r.id, "tier": r.tier, "message": r.message, "weight": r.weight,
         "patterns": [p.pattern for p in r.patterns]}
        for r in load_rules()
        if tier is None or r.tier == tier
    ]


def install_skills(*, target: str | None = None, write: bool = False) -> dict[str, Any]:
    """Link this package's shipped skills into an agent host's skills directory.

    Defaults to ``~/.claude/skills``. Dry-run unless ``write`` is passed.

    >>> r = install_skills()
    >>> r["dry_run"], len(r["skills"]) > 0
    (True, True)
    """
    from importlib.resources import files
    from pathlib import Path

    src = Path(str(files("ductus.data") / "skills"))
    dst = Path(target).expanduser() if target else Path.home() / ".claude" / "skills"
    names = sorted(p.name for p in src.iterdir() if (p / "SKILL.md").is_file())

    actions = []
    for name in names:
        link = dst / name
        state = "exists" if link.exists() else "new"
        actions.append({"skill": name, "link": str(link), "state": state})
        if write and not link.exists():
            dst.mkdir(parents=True, exist_ok=True)
            link.symlink_to(src / name)
    return {"source": str(src), "target": str(dst), "dry_run": not write,
            "skills": actions}


#: The SSOT the CLI, an MCP server and an HTTP app would all dispatch from.
_dispatch_funcs = [gauge, detectors, segmenters, tells, install_skills]
