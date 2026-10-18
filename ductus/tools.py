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

Several readers' judgments go to the same ``judgments`` argument, one source each; what
enters the report is then the sentences at least ``k`` of them agree on, with the
per-reader counts beside it (:mod:`ductus.consensus`). :func:`baseline` takes the same
measure on reference texts, and ``gauge(baseline=...)`` sets the two side by side.
"""

from __future__ import annotations

import dataclasses
import json
import os
from collections.abc import Sequence
from typing import Any

from ductus.base import Signal, Span
from ductus.consensus import DEFAULT_K, anchor_judgment, consensus, consensus_signals
from ductus.consensus import pooled as _pooled
from ductus.core import gauge as _gauge
from ductus.detect import DETECTORS
from ductus.render import to_html, to_json, to_markdown
from ductus.segment import SEGMENTERS

__all__ = [
    "_dispatch_funcs",
    "baseline",
    "detectors",
    "gauge",
    "host_mutating",
    "host_paths",
    "install_skills",
    "segmenters",
    "tells",
]

FORMATS = ("markdown", "json", "html")


def host_mutating(fn):
    """Mark a verb that changes the machine it runs on, rather than only reading.

    Declared at the definition site so surfaces can filter on it without anyone
    writing a second list of verbs. A CLI user invoking one of these chose to; a
    remote MCP caller did not necessarily, so :mod:`ductus.mcp` leaves them out.

    >>> host_mutating(lambda: None).mutates_host
    True
    >>> getattr(segmenters, "mutates_host", False)
    False
    """
    fn.mutates_host = True
    return fn


def host_paths(**roles: str):
    """Declare which parameters of a verb address the machine's own filesystem.

    A sibling of :func:`host_mutating`, and the same idea: the fact is stated once,
    at the verb's own definition, and every surface reads it from there. A surface
    that never writes a second verb list also never writes a second list of which
    arguments are dangerous on it.

    ``role`` is ``"read"`` for a parameter the verb may read a file from, and
    ``"write"`` for one it may write a file to. Both are ordinary, correct behaviour
    at a CLI, where the caller and the filesystem belong to the same person. They are
    an arbitrary file read and an arbitrary file write on a surface where they do not
    -- so :mod:`ductus.http` refuses them, driven by this declaration rather than by
    knowing anything about ``gauge``.

    >>> sorted(gauge.host_paths.items())
    [('baseline', 'read'), ('judgments', 'read'), ('out', 'write'), ('source', 'read')]
    >>> getattr(segmenters, "host_paths", {})
    {}
    """
    unknown = set(roles.values()) - {"read", "write"}
    if unknown:
        raise ValueError(f"role must be 'read' or 'write', got {sorted(unknown)}")

    def decorate(fn):
        fn.host_paths = dict(roles)
        return fn

    return decorate


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


def _load_judgments(judgments: Any) -> list[dict[str, Any]]:
    """One reader's judgment records, from a path, JSON text, a wrapper dict or a list.

    >>> _load_judgments('{"judgments": [{"quote": "x", "direction": "human"}]}')
    [{'quote': 'x', 'direction': 'human'}]
    """
    if isinstance(judgments, str):
        judgments = json.loads(_read_source(judgments))
    if isinstance(judgments, dict):
        judgments = judgments.get("judgments", judgments.get("findings", []))
    return list(judgments or ())


def _readers(judgments: Any) -> list[tuple[str, list[dict[str, Any]]]]:
    """Split a ``judgments`` argument into named readers.

    A string, or a list of records, is **one** reader -- the original single-reader
    shape. A list of strings (paths, or JSON text) is one reader per string, named
    after its file.

    >>> [n for n, _ in _readers('[]')], [n for n, _ in _readers(['[]', '[]'])]
    (['reader 1'], ['reader 1', 'reader 2'])
    >>> len(_readers([{"quote": "x", "direction": "human"}]))
    1
    """
    if not judgments:
        return []
    if isinstance(judgments, (str, dict)) or isinstance(judgments[0], dict):
        judgments = [judgments]

    def name(i: int, source: Any) -> str:
        if isinstance(source, str) and len(source) < 4096 and os.path.isfile(source):
            return os.path.splitext(os.path.basename(source))[0]
        return f"reader {i + 1}"

    return [(name(i, src), _load_judgments(src)) for i, src in enumerate(judgments)]


def _signals_from_judgments(text: str, judgments: Any) -> list[Signal]:
    """Turn one reader's judgment records into signals anchored in ``text``.

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
    out: list[Signal] = []
    for j in _load_judgments(judgments):
        where = anchor_judgment(text, j)
        if where is None:
            continue  # the quote no longer occurs: drop it rather than mis-anchor
        start, end = where
        out.append(
            Signal(
                name=j.get("name", "judgment"),
                direction=j["direction"],
                weight=float(j.get("weight", 0.35)),
                detector=j.get("detector", "judge"),
                value=j.get("value"),
                note=j.get("note", ""),
                span=Span.of(text, start, end, level="token"),
            )
        )
    return out


def _compared(reading: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """The reference measure, plus whatever makes it not like-for-like with ``reading``.

    More readers at the same ``k`` agree more often by chance, and a different ``k`` is
    a different measure, so either is said out loud rather than silently compared.
    """
    caveats = []
    if reference.get("k") != reading["k"]:
        caveats.append(
            f"the reference texts were read at k={reference.get('k')}, this one at "
            f"k={reading['k']}: different measures"
        )
    if reference.get("n_readers") != [reading["n_readers"]]:
        caveats.append(
            f"the reference texts had {reference.get('n_readers')} readers each, this "
            f"one {reading['n_readers']}: more readers agree more often by chance"
        )
    return {**reference, "caveats": caveats}


@host_paths(source="read", judgments="read", baseline="read", out="write")
def gauge(
    source: str,
    *,
    format: str = "markdown",
    segmenter: str = "paragraph",
    detectors: str | Sequence[str] | None = None,
    judgments: str | Sequence[str] | None = None,
    k: int = DEFAULT_K,
    baseline: str | None = None,
    out: str | None = None,
    title: str | None = None,
) -> str:
    """Gauge how machine-written a text reads, and render the result.

    ``source`` is a file path, a literal string, or ``-`` for stdin.
    ``format`` is one of markdown, json, html. ``detectors`` is a comma-separated
    subset of the available detectors. ``title`` overrides the heading of the
    markdown and html renderings (each has its own default). ``judgments`` is a path to a JSON file of
    an agent's own readings, folded in alongside the deterministic ones. With
    ``out``, the result is written there and a one-line summary is returned.

    Give ``judgments`` several times -- one file per independent reader -- and what is
    folded in is no longer each reader's flags but the sentences at least ``k`` readers
    flag; the report shows each reader's count and that consensus per 1,000 words.
    ``baseline`` is the output of :func:`baseline` on reference texts (a path or the
    JSON itself), shown beside the consensus.

    >>> gauge("Sent it Friday. Two sites, not five.").splitlines()[0]
    '# Reading'
    """
    if format not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}, got {format!r}")
    if isinstance(detectors, str):
        detectors = [d.strip() for d in detectors.split(",") if d.strip()]

    text = _read_source(source)
    readers = _readers(judgments)
    reading = None
    if len(readers) > 1:
        reading = consensus(
            text, [js for _, js in readers], k=k, names=[n for n, _ in readers]
        )
        extra = consensus_signals(text, reading)
    elif readers:
        extra = _signals_from_judgments(text, readers[0][1])
    else:
        extra = ()
    if baseline is not None and reading is None:
        raise ValueError(
            "baseline compares a multi-reader consensus; give judgments at least twice"
        )
    report = _gauge(text, segmenter=segmenter, detectors=detectors, extra_signals=extra)
    if reading is not None:
        meta = {"readers": reading}
        if baseline is not None:
            meta["baseline"] = _compared(reading, json.loads(_read_source(baseline)))
        report = dataclasses.replace(report, meta=meta)
    # Only override when asked: each renderer owns its own default title.
    titled = {} if title is None else {"title": title}

    if format == "json":
        rendered = to_json(report)
    elif format == "html":
        rendered = to_html(
            report, text=text, subtitle=f"{report.n_chars} characters", **titled
        )
    else:
        rendered = to_markdown(report, text=text, **titled)

    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(rendered)
        return (
            f"wrote {out} ({len(rendered)} bytes) -- {report.document.label}, "
            f"lean {report.document.lean:+.2f}, {len(report.signals)} signal(s)"
        )
    return rendered


# Several readers means `--judgments a.json --judgments b.json`, so the flag appends.
# A plain attribute (cw's declared contract), so this module still never imports cw.
gauge._cw = {"params": {"judgments": {"action": "append"}}}


def _readers_beside(source: str, judgments_dir: str | None) -> list[str]:
    """The judgment files for ``source``, by convention.

    ``<stem>.*.json`` in ``judgments_dir`` (default: the source's own directory), and
    every ``*.json`` in a ``<stem>/`` subdirectory of it. So ``essay.md`` is read by
    ``essay.a.json`` and ``essay.b.json`` beside it, or by ``essay/*.json``.
    """
    import glob

    stem = os.path.splitext(os.path.basename(source))[0]
    where = judgments_dir or os.path.dirname(os.path.abspath(source))
    esc = glob.escape
    found = glob.glob(os.path.join(esc(where), esc(stem) + ".*.json"))
    found += glob.glob(os.path.join(esc(where), esc(stem), "*.json"))
    return sorted(set(found))


def _baseline_markdown(result: dict[str, Any]) -> str:
    def rate(d: dict[str, Any]) -> str:
        r = d.get("per_1000_words")
        return "n/a" if r is None else f"{r:.1f}"

    m, h = result["machine"], result["human"]
    lo, hi = m["range"] or (None, None)
    spread = "" if lo is None else f", {lo:.1f}&ndash;{hi:.1f} across texts"
    out = [
        "# Baseline",
        "",
        (
            f"{result['n_texts']} reference text(s), {result['n_words']:,} words, "
            f"{result['unit']}s flagged by at least k={result['k']} readers "
            f"(readers per text: {', '.join(map(str, result['n_readers']))})."
        ),
        "",
        (
            f"**Machine-leaning consensus: {rate(m)} per 1,000 words** pooled{spread}. "
            f"Human-leaning: {rate(h)} per 1,000 words."
        ),
        "",
        "| Text | Words | Readers | Machine-leaning / 1,000 words | Human-leaning / 1,000 words |",
        "|---|---|---|---|---|",
    ]
    for t in result["texts"]:
        out.append(
            f"| {t['source']} | {t['n_words']:,} | {t['n_readers']} | "
            f"{rate(t['machine'])} | {rate(t['human'])} |"
        )
    out += [
        "",
        (
            "A description of how these texts read to these readers, so another text "
            "can be set beside it. Not a threshold, and not a statement about who wrote "
            "anything."
        ),
        "",
    ]
    return "\n".join(out)


@host_paths(sources="read", judgments_dir="read", out="write")
def baseline(
    sources: Sequence[str],
    *,
    judgments_dir: str | None = None,
    k: int = DEFAULT_K,
    format: str = "json",
    out: str | None = None,
) -> str:
    """The multi-reader consensus density on reference texts, to read a new text beside.

    ``sources`` are files -- typically the author's own writing from before the
    question arose. Each one's readers are found by name: ``<stem>.*.json`` in
    ``judgments_dir`` (default: beside the file), or ``<stem>/*.json`` under it. Every
    text needs at least ``k`` readers.

    The result pools the texts by words and keeps the per-text spread; pass the JSON to
    ``gauge(baseline=...)`` so a report can say *next to this author's own writing*
    instead of giving a bare number. ``format`` is json or markdown. Quotes from the
    reference texts are not included -- only counts.
    """
    if format not in ("json", "markdown"):
        raise ValueError(f"format must be json or markdown, got {format!r}")
    if isinstance(sources, str):
        sources = [sources]
    if not sources:
        raise ValueError("baseline needs at least one reference text")
    texts = []
    for src in sources:
        if not os.path.isfile(src):
            raise ValueError(f"{src!r} is not a file; baseline finds readers by filename")
        files = _readers_beside(src, judgments_dir)
        if len(files) < k:
            raise ValueError(
                f"{os.path.basename(src)}: found {len(files)} reader file(s), need at "
                f"least k={k} ({os.path.splitext(os.path.basename(src))[0]}.*.json)"
            )
        names, readers = zip(*_readers(files))
        result = consensus(_read_source(src), readers, k=k, names=names)
        texts.append(
            {
                "source": os.path.basename(src),
                "readers": list(names),
                "k": result["k"],
                "unit": result["unit"],
                "n_readers": result["n_readers"],
                "n_words": result["n_words"],
                # Counts only: the reference texts' own sentences stay out of the output.
                **{
                    d: {f: result[d][f] for f in ("count", "per_1000_words")}
                    for d in ("machine", "human")
                },
            }
        )
    result = {**_pooled(texts), "texts": texts}
    rendered = (
        json.dumps(result, indent=2, ensure_ascii=False)
        if format == "json"
        else _baseline_markdown(result)
    )
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(rendered)
        m = result["machine"]
        return (
            f"wrote {out} -- {result['n_texts']} text(s), machine-leaning consensus "
            f"{m['per_1000_words']} per 1,000 words pooled"
        )
    return rendered


# Several reference texts, one positional each (`ductus baseline a.md b.md`).
baseline._cw = {"params": {"sources": {"nargs": "+"}}}


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
        {
            "id": r.id,
            "tier": r.tier,
            "message": r.message,
            "weight": r.weight,
            "patterns": [p.pattern for p in r.patterns],
        }
        for r in load_rules()
        if tier is None or r.tier == tier
    ]


@host_mutating
@host_paths(target="write")
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
    return {
        "source": str(src),
        "target": str(dst),
        "dry_run": not write,
        "skills": actions,
    }


#: The SSOT the CLI, an MCP server and an HTTP app would all dispatch from.
_dispatch_funcs = [gauge, baseline, detectors, segmenters, tells, install_skills]
