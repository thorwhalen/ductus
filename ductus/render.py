"""Turning a report into something a person reads: JSON, Markdown, or HTML.

Three renderers, all pure functions of a :class:`~ductus.base.Report`:

:func:`to_json`
    The full structure, for a frontend or another program.
:func:`to_markdown`
    A synopsis, then one section per flagged segment with its stats and the
    reason each signal fired.
:func:`to_html`
    A single self-contained file -- no build step, no CDN -- showing the text
    with the flagged spans shaded, the reason on hover, light and dark themes.

The HTML follows the two-channel rule for annotated text: **hue encodes score
only** (a perceptually-uniform ramp, lightness re-clamped per theme), while
overlap is shown structurally in a separate lane under each paragraph. Loading
both meanings into one colour is what makes overlapping highlights unreadable.

>>> from ductus.core import gauge
>>> r = gauge("Let's delve into this robust tapestry.")
>>> "delve" in to_markdown(r)
True
>>> to_html(r).startswith("<!doctype html>")
True
>>> import json; json.loads(to_json(r))["schema_version"]
'1'
"""

from __future__ import annotations

import html as _html
import json
from dataclasses import asdict
from typing import Any

from ductus.base import Report, Segment, Signal, Span

__all__ = ["to_html", "to_json", "to_markdown"]

#: Shown on every rendered report. The second sentence used to say that detectors
#: "over-flag non-native English" -- true of the field, and the opposite of what this
#: package was then measured to do. Phase 2 found the bias runs toward formal, fluent
#: prose, with the native-speaker control the most-accused group. The skills and the
#: MCP instructions were corrected at the time and this string was missed.
#:
#: The rate is given as a natural frequency rather than "6.0%" on purpose. This text
#: sits directly under a verdict about one specific document, and the footer is the
#: one place the no-percentage rule is load-bearing enough to have its own test.
_DISCLAIMER = (
    "Evidence, not a verdict. These are signals with weights, not a probability that "
    "anyone used a model. Heavily-edited human writing and model-assisted writing "
    "produce overlapping signatures. Measured on 350 human-written documents, about "
    "one in sixteen is called leans-machine by these defaults, and every one of those "
    "is wrong; the bias runs toward formal, fluent prose, not toward simple prose, so "
    "a careful essayist is the likeliest person to be wronged by this page. A flagged "
    "sentence is much better evidence than a flagged document. Do not use this to "
    "accuse someone."
)


def to_json(report: Report, *, indent: int | None = 2) -> str:
    """The whole report, serialized.

    >>> from ductus.core import gauge
    >>> d = __import__("json").loads(to_json(gauge("delve")))
    >>> d["segments"][0]["signals"][0]["detector"]
    'tells'
    """
    return json.dumps(asdict(report), indent=indent, ensure_ascii=False)


def _stats(seg: Segment) -> str:
    m = sum(s.weight for s in seg.signals if s.direction == "machine")
    h = sum(s.weight for s in seg.signals if s.direction == "human")
    return (
        f"lean **{seg.lean:+.2f}** &middot; strength {seg.strength:.2f} &middot; "
        f"{len(seg.signals)} signal(s), machine {m:.2f} / human {h:.2f}"
    )


def to_markdown(
    report: Report, *, text: str | None = None, title: str = "Reading"
) -> str:
    """A readable diagnosis: synopsis first, then the flagged segments.

    >>> from ductus.core import gauge
    >>> md = to_markdown(gauge("In conclusion, this is a robust tapestry."))
    >>> md.splitlines()[0].startswith("# ")
    True
    """
    doc = report.document
    flagged = [s for s in report.segments if s.signals]
    by_dir: dict[str, float] = {}
    for s in report.signals:
        by_dir[s.direction] = by_dir.get(s.direction, 0.0) + s.weight

    out: list[str] = [f"# {title}", ""]
    out.append(
        f"**{doc.label}** &mdash; lean {doc.lean:+.2f}, evidence strength {doc.strength:.2f}, "
        f"over {len(report.segments)} {report.segmenter}(s) of {report.n_chars} characters."
    )
    out.append("")
    out.append(
        "Weight by direction: "
        + ", ".join(f"{k} {v:.2f}" for k, v in sorted(by_dir.items()))
        + f". Detectors: {', '.join(report.detectors)}. Calibration: {report.calibration}."
    )
    out.append("")

    if not flagged:
        out += [
            (
                "No signal fired anywhere in this text. That is a real result and a "
                "weak one: the deterministic detectors find phrases, artifacts and "
                "shapes, and a text can be wholly machine-written without any of them."
            ),
            "",
            f"> {_DISCLAIMER}",
            "",
        ]
        return "\n".join(out)

    out += ["## Segments with evidence", ""]
    out += ["| Offsets | Opening | Label | Lean | Signals |", "|---|---|---|---|---|"]
    for seg in flagged:
        opening = seg.span.quote[:44].replace("\n", " ").replace("|", "\\|")
        names = ", ".join(sorted({s.name for s in seg.signals}))
        out.append(
            f"| {seg.span.start}&ndash;{seg.span.end} | {opening}… | "
            f"{seg.label} | {seg.lean:+.2f} | {names} |"
        )
    out.append("")

    out += ["## Why", ""]
    for seg in flagged:
        opening = seg.span.quote[:60].replace("\n", " ")
        out += [
            f"### `{seg.span.start}`&ndash;`{seg.span.end}` — {seg.label}",
            "",
            f"> {opening}…",
            "",
            _stats(seg),
            "",
        ]
        for s in sorted(seg.signals, key=lambda s: -s.weight):
            where = (
                f" — `{s.span.quote[:40]}`" if s.span and s.span.level == "token" else ""
            )
            out.append(
                f"- **{s.name}** ({s.direction}, {s.weight:.2f}, via {s.detector}){where}  \n  {s.note}"
            )
        out.append("")

    out += ["---", "", f"> {_DISCLAIMER}", ""]
    return "\n".join(out)


# ------------------------------------------------------------------------- HTML

_CSS = """
:root{--bg:#fdfdfc;--fg:#1a1a18;--muted:#6b6b63;--line:#e4e4de;--card:#fff;--panel:#f6f6f3;
 --h0:oklch(0.95 0.04 235);--h1:oklch(0.80 0.11 235);
 --m0:oklch(0.95 0.05 65);--m1:oklch(0.78 0.15 55);--n1:oklch(0.75 0.03 280)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#14140f;--fg:#ececdf;--muted:#95958a;--line:#2e2e26;--card:#1c1c16;--panel:#1f1f18;
 --h0:oklch(0.30 0.04 235);--h1:oklch(0.54 0.11 235);
 --m0:oklch(0.32 0.05 65);--m1:oklch(0.56 0.14 55);--n1:oklch(0.45 0.03 280)}}
:root[data-theme="dark"]{--bg:#14140f;--fg:#ececdf;--muted:#95958a;--line:#2e2e26;--card:#1c1c16;
 --panel:#1f1f18;--h0:oklch(0.30 0.04 235);--h1:oklch(0.54 0.11 235);
 --m0:oklch(0.32 0.05 65);--m1:oklch(0.56 0.14 55);--n1:oklch(0.45 0.03 280)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 ui-serif,Georgia,serif}
header,main,footer{max-width:820px;margin:0 auto;padding:0 16px}
header{padding-top:32px;border-bottom:1px solid var(--line);padding-bottom:14px}
h1{font:600 22px/1.3 ui-sans-serif,system-ui,sans-serif;margin:0 0 4px}
.sub{font:13px/1.5 ui-sans-serif,system-ui,sans-serif;color:var(--muted);margin:0}
.legend{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:14px 0 0;
 font:12px/1 ui-sans-serif,system-ui,sans-serif;color:var(--muted)}
.chip{display:inline-flex;align-items:center;gap:6px}
.sw{width:34px;height:12px;border-radius:2px;display:inline-block}
.sw.m{background:linear-gradient(90deg,var(--m0),var(--m1))}
.sw.h{background:linear-gradient(90deg,var(--h0),var(--h1))}
main{padding-top:22px;padding-bottom:36px}
.para{position:relative;margin:0;padding:10px 12px 10px 14px;border-radius:4px;
 border-left:3px solid transparent;white-space:pre-wrap;transition:background .12s}
.para:hover{background:var(--panel)}
.para[data-lean="m"]{border-left-color:var(--m1)}
.para[data-lean="h"]{border-left-color:var(--h1)}
mark{background:var(--hl);color:inherit;padding:.06em 0;border-radius:2px;
 box-shadow:0 1.5px 0 0 var(--ul);cursor:help}
mark:focus{outline:2px solid var(--ul);outline-offset:1px}
.badge{position:absolute;right:10px;top:8px;font:10px/1 ui-sans-serif,system-ui,sans-serif;
 letter-spacing:.04em;text-transform:uppercase;color:var(--muted);opacity:0;transition:opacity .12s}
.para:hover .badge{opacity:1}
.lane{display:flex;gap:3px;margin:3px 0 12px 14px;height:4px}
.lane i{height:4px;border-radius:2px;display:block}
aside{position:fixed;right:16px;bottom:16px;width:min(340px,calc(100vw - 32px));
 background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px 14px;
 font:12px/1.55 ui-sans-serif,system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.16);
 display:none;z-index:9}
aside.on{display:block}
/* Anchored beside the highlight it explains: the reason should be where the eye already
   is, not in a corner the reader has to look away to find. JS sets left/top. */
aside.at{right:auto;bottom:auto}
aside .dir{font-weight:600}
aside .dir.machine{color:var(--m1)}aside .dir.human{color:var(--h1)}
aside .why{margin-top:7px;padding-top:7px;border-top:1px solid var(--line)}
footer{border-top:1px solid var(--line);padding-top:16px;padding-bottom:48px;
 font:12px/1.6 ui-sans-serif,system-ui,sans-serif;color:var(--muted)}
/* Too narrow to sit beside anything: fall back to a bottom sheet. */
@media(max-width:640px){aside,aside.at{left:16px;right:16px;top:auto;bottom:16px;width:auto}}
"""

_JS = """
const D=JSON.parse(document.getElementById('ductus-data').textContent);
const box=document.getElementById('tip');
const ANCHOR_MIN_WIDTH=641, GAP=10, EDGE=12;
function place(el){
 if(innerWidth<ANCHOR_MIN_WIDTH){box.classList.remove('at');box.style.left=box.style.top='';return;}
 box.classList.add('at');
 const r=el.getBoundingClientRect(),w=box.offsetWidth,h=box.offsetHeight;
 let y=r.bottom+GAP; if(y+h>innerHeight-EDGE) y=Math.max(EDGE,r.top-h-GAP);
 const x=Math.min(Math.max(EDGE,r.left),innerWidth-w-EDGE);
 box.style.left=x+'px';box.style.top=y+'px';}
function show(e){const el=e.currentTarget,s=D[el.dataset.k];if(!s)return;
 box.innerHTML='<b>'+s.n+'</b> &middot; <span class="dir '+s.d+'">'+s.d+'</span> &middot; weight '+
 s.w.toFixed(2)+' &middot; '+s.t+'<div class="why">'+s.r+'</div>';
 box.classList.add('on');place(el);}
function hide(){box.classList.remove('on');}
for(const m of document.querySelectorAll('mark')){m.tabIndex=0;
 m.addEventListener('mouseenter',show);m.addEventListener('mouseleave',hide);
 m.addEventListener('focus',show);m.addEventListener('blur',hide);}
"""


def _shade(direction: str, weight: float) -> tuple[str, str]:
    """Background and underline colour for a signal, on the per-theme ramp."""
    t = min(max(weight, 0.10), 0.60) / 0.60
    if direction == "neutral":
        return "transparent", "var(--n1)"
    a, b = ("m0", "m1") if direction == "machine" else ("h0", "h1")
    return f"color-mix(in oklab, var(--{b}) {t * 100:.0f}%, var(--{a}))", f"var(--{b})"


def _placed(seg: Segment) -> list[tuple[Signal, Span]]:
    """Token-level signals, greedily de-overlapped -- the rest go to the lane.

    Pairs each signal with its span so the caller never has to re-check that the
    span is there.
    """
    candidates = sorted(
        ((s, s.span) for s in seg.signals if s.span and s.span.level == "token"),
        key=lambda pair: (pair[1].start, -pair[0].weight),
    )
    out: list[tuple[Signal, Span]] = []
    last = seg.span.start
    for signal, span in candidates:
        if span.start >= last:
            out.append((signal, span))
            last = span.end
    return out


def to_html(
    report: Report,
    *,
    text: str | None = None,
    title: str = "Where this reads as machine-written",
    subtitle: str = "",
) -> str:
    """A single self-contained HTML file. ``text`` defaults to the spans' own quotes.

    >>> from ductus.core import gauge
    >>> h = to_html(gauge("Let's delve in."))
    >>> "<mark" in h and "prefers-color-scheme" in h
    True
    """
    tips: dict[str, dict[str, Any]] = {}
    body: list[str] = []

    for i, seg in enumerate(report.segments):
        base = seg.span.start
        raw = text[seg.span.start : seg.span.end] if text is not None else seg.span.quote
        out, cursor = [], 0
        for j, (s, s_span) in enumerate(_placed(seg)):
            key = f"{i}_{j}"
            tips[key] = {
                "n": s.name,
                "d": s.direction,
                "w": s.weight,
                "t": s.detector,
                "r": _html.escape(s.note),
            }
            hl, ul = _shade(s.direction, s.weight)
            a, b = s_span.start - base, s_span.end - base
            out.append(_html.escape(raw[cursor:a]))
            out.append(
                f'<mark data-k="{key}" style="--hl:{hl};--ul:{ul}">'
                f"{_html.escape(raw[a:b])}</mark>"
            )
            cursor = b
        out.append(_html.escape(raw[cursor:]))

        lean = "m" if seg.lean > 0.15 else ("h" if seg.lean < -0.15 else "n")
        badge = f"{seg.label} &middot; {seg.lean:+.2f}" if seg.signals else ""
        body.append(
            f'<p class="para" data-lean="{lean}">'
            f'<span class="badge">{badge}</span>{"".join(out)}</p>'
        )
        if seg.signals:
            bars = "".join(
                f'<i style="width:{max(12, s.weight * 80):.0f}px;'
                f'background:{_shade(s.direction, s.weight)[1]}" '
                f'title="{_html.escape(s.name)}"></i>'
                for s in seg.signals
            )
            body.append(f'<div class="lane">{bars}</div>')

    doc = report.document
    sub = subtitle or (
        f"{report.n_chars} characters &middot; {len(report.segments)} "
        f"{report.segmenter}(s) &middot; schema {report.schema_version}"
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_html.escape(title)}</title><style>{_CSS}</style></head><body>"
        f'<header><h1>{_html.escape(title)}</h1><p class="sub">{sub}</p>'
        '<div class="legend">'
        '<span class="chip"><span class="sw m"></span> machine-leaning</span>'
        '<span class="chip"><span class="sw h"></span> human-leaning</span>'
        f'<span class="chip">document: <b>&nbsp;{doc.label}</b> '
        f"({doc.lean:+.2f}, strength {doc.strength:.2f})</span></div></header>"
        f'<main>{"".join(body)}</main><aside id="tip"></aside>'
        f"<footer><p><b>{_DISCLAIMER}</b></p>"
        f"<p>sha256 {report.text_sha256[:16]} &middot; detectors: "
        f"{', '.join(report.detectors)} &middot; calibration: {report.calibration}</p></footer>"
        f'<script type="application/json" id="ductus-data">{json.dumps(tips)}</script>'
        f"<script>{_JS}</script></body></html>"
    )
