"""The detectors -- the ``detectors=`` seam. Each one turns a span into evidence.

A detector is a plain function ``(text, span) -> Iterator[Signal]``. That is the
entire interface; there is no base class and nothing to register. Four ship, all
deterministic and dependency-free:

``tells``
    Catalogue phrase matches (see :mod:`ductus.tells`). Finds vocabulary.
``forensic``
    Typographic and mechanical artifacts -- em dashes, mixed apostrophes, a hard
    line break mid-sentence, trailing whitespace. The cheapest signal in the
    package and often the most decisive, because these are traces of *how* the
    text was produced rather than of how it reads.
``rhetoric``
    Sentence *shapes* a catalogue cannot see: the "not X but Y" antithesis, a
    colon introducing a three-part parallel enumeration, concession-then-pivot.
``rhythm``
    Burstiness -- the variance of sentence length. Weak evidence, and reported
    as weak.

Adding a model-based detector (Fast-DetectGPT, Binoculars, a vendor API) means
writing one more function of this shape. Nothing else in the package changes.

>>> from ductus.base import Span
>>> t = "The results were not merely good, but transformative."
>>> [s.name for s in rhetoric(t, Span.of(t, 0, len(t)))]
['not-x-but-y']
>>> t2 = "It matters — a lot — and always has."
>>> [s.name for s in forensic(t2, Span.of(t2, 0, len(t2)))]
['em-dash', 'em-dash']
"""

from __future__ import annotations

import re
import statistics
from typing import Callable, Iterator, Sequence

from ductus.base import Signal, Span
from ductus.tells import iter_tell_matches, metrics

__all__ = ["DETECTORS", "tells", "forensic", "rhetoric", "rhythm", "detectors_from"]

_WORD_RE = re.compile(r"[A-Za-z0-9’']+")
_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?")

_DISCOURSE_OPENERS = (
    "however", "moreover", "furthermore", "additionally", "that said",
    "at the same time", "in addition", "importantly", "ultimately",
    "crucially", "notably", "overall",
)


def _sub(text: str, span: Span, start: int, end: int) -> Span:
    """A token-level span at document coordinates, given offsets inside ``span``."""
    return Span.of(text, span.start + start, span.start + end, level="token")


# Headings, list items, table rows, fenced code, quotes, link-only lines. These are
# markup, not prose: judging them for terminal punctuation or stray line breaks
# reports the document's *format* as evidence about its author, which is noise.
_MARKUP_RE = re.compile(
    r"""^\s*(?:\#{1,6}\s        # heading
            |[-*+]\s              # bullet
            |\d+[.)]\s           # numbered item
            |\|                   # table row
            |>\s                  # block quote
            |```|~~~               # code fence
            |\[[^\]]+\]:        # link reference
            |[-=]{3,}\s*$         # rule / setext underline
        )""",
    re.VERBOSE,
)


def _is_markup(s: str) -> bool:
    """Whether a segment is document structure rather than prose.

    >>> _is_markup("## A heading"), _is_markup("| a | b |"), _is_markup("- an item")
    (True, True, True)
    >>> _is_markup("An ordinary sentence.")
    False
    """
    return bool(_MARKUP_RE.match(s)) or "```" in s


# --------------------------------------------------------------------------- tells

_QUOTED_RE = re.compile(r"`[^`\n]+`|\"[^\"\n]{0,200}\"|[“][^”\n]{0,200}[”]")


def _quoted_ranges(s: str) -> list[tuple[int, int]]:
    """Character ranges inside inline code or quotation marks.

    A tell inside quotation marks was written by whoever is being quoted, not by
    the author of the text. Scoring it is how a document *about* machine writing
    scores as machine-written -- this package's own README does exactly that.

    >>> _quoted_ranges('he said "delve" and `robust` too')
    [(8, 15), (20, 28)]
    >>> _quoted_ranges("nothing quoted here")
    []
    """
    return [(m.start(), m.end()) for m in _QUOTED_RE.finditer(s)]


def tells(text: str, span: Span) -> Iterator[Signal]:
    """Catalogue phrase matches, as signals. Quoted text is skipped.

    >>> from ductus.base import Span
    >>> t = "Let's delve into it."
    >>> [(s.name, s.direction) for s in tells(t, Span.of(t, 0, len(t)))]
    [('ai-vocabulary', 'machine')]
    >>> q = 'Models overuse "delve", so avoid it.'
    >>> list(tells(q, Span.of(q, 0, len(q))))
    []
    """
    from ductus.tells import TIER_WEIGHT

    quoted = _quoted_ranges(span.quote)

    for m in iter_tell_matches(span.quote, offset=span.start):
        rel_start = m.start - span.start
        if any(a <= rel_start < b for a, b in quoted):
            continue  # inside a quotation: not this author's words
        yield Signal(
            name=m.rule_id,
            direction="machine",
            weight=TIER_WEIGHT.get(m.tier, 0.15),
            detector="tells",
            value=m.matched,
            note=f"tier {m.tier}: {m.message}",
            span=Span.of(text, m.start, m.end, level="token"),
        )


# ------------------------------------------------------------------------ forensic

def forensic(text: str, span: Span) -> Iterator[Signal]:
    """Typographic and mechanical artifacts of how the text was produced.

    Several of these argue for a *human*, which is the point: a detector that can
    only ever accuse is not a measuring instrument.

    >>> from ductus.base import Span
    >>> t = "he said\\nand then left"
    >>> [s.name for s in forensic(t, Span.of(t, 0, len(t)))]
    ['mid-sentence-newline', 'no-terminal-punctuation']
    """
    s = span.quote

    for m in re.finditer(r"—", s):
        yield Signal("em-dash", "machine", 0.12, "forensic", "—",
                     "em dash; heavy use is a default-model habit, and absence "
                     "across a long text is a meaningful human signal",
                     _sub(text, span, m.start(), m.end()))

    straight, curly = s.count("'"), s.count("’")
    if straight and curly:
        yield Signal("mixed-apostrophes", "human", 0.35, "forensic", (straight, curly),
                     f"{straight} straight and {curly} curly apostrophes mixed -- "
                     "the trace of hand-editing pasted text")

    for m in re.finditer(r"[ \t]+$", s, re.M):
        yield Signal("trailing-whitespace", "human", 0.25, "forensic", True,
                     "trailing whitespace: a typing artifact, not something a model emits",
                     _sub(text, span, m.start(), m.end()))

    prose = not _is_markup(s)

    if prose:
        for m in re.finditer(r"[a-z,;]\n[a-z]", s):
            yield Signal("mid-sentence-newline", "human", 0.45, "forensic", True,
                         "a hard line break inside a sentence -- a paste or typing artifact",
                         _sub(text, span, m.start(), m.end()))

    if (prose and len(_WORD_RE.findall(s)) >= 4
            and not re.search(r"[.!?:;)\]\"'’”]\s*$", s.strip())):
        yield Signal("no-terminal-punctuation", "human", 0.30, "forensic", True,
                     "ends without terminal punctuation; models close their sentences")

    for m in re.finditer(r"[  →✓✅❌]", s):
        yield Signal("unicode-artifact", "machine", 0.15, "forensic",
                     f"U+{ord(m.group()):04X}",
                     f"U+{ord(m.group()):04X} is rarely typed by hand",
                     _sub(text, span, m.start(), m.end()))


# ------------------------------------------------------------------------ rhetoric

def rhetoric(text: str, span: Span) -> Iterator[Signal]:
    """Sentence shapes a phrase catalogue cannot see.

    These are the patterns that survive a model being told to avoid "AI words",
    which is why they matter more than vocabulary as models improve.

    >>> from ductus.base import Span
    >>> t = "This is a pattern: you plan it, you build it, and you ship it."
    >>> [s.name for s in rhetoric(t, Span.of(t, 0, len(t)))]
    ['colon-tricolon']
    """
    s = span.quote
    low = s.lower()

    for m in re.finditer(r"\bnot (?:just |only |merely |simply )?[^,.;:]{2,45},? but\b", s, re.I):
        yield Signal("not-x-but-y", "machine", 0.30, "rhetoric", m.group().strip(),
                     "the 'not X but Y' antithesis -- one of the strongest model habits",
                     _sub(text, span, m.start(), m.end()))

    for m in re.finditer(r":\s*[^,.:;]{4,90},\s*[^,.:;]{4,90},\s*and\s+[^.]{4,90}[.!?]", s):
        yield Signal("colon-tricolon", "machine", 0.45, "rhetoric", m.group()[:70],
                     "a colon introducing a three-part parallel enumeration -- "
                     "a textbook assistant construction",
                     _sub(text, span, m.start(), m.end()))

    for opener in _DISCOURSE_OPENERS:
        if low.startswith(opener):
            yield Signal("discourse-opener", "machine", 0.20, "rhetoric", opener,
                         f"opens with '{opener}', a connective models reach for",
                         _sub(text, span, 0, len(opener)))
            break

    for m in re.finditer(
        r"\bi (?:do |really do |genuinely )?(?:value|appreciate|respect|understand)\b[^.]{0,80}\.\s*"
        r"(?:at the same time|that said|however|but)\b", low):
        yield Signal("concede-pivot", "machine", 0.35, "rhetoric", m.group()[:70],
                     "concession immediately followed by a pivot -- the diplomatic-feedback move",
                     _sub(text, span, m.start(), m.end()))


# -------------------------------------------------------------------------- rhythm

def rhythm(text: str, span: Span) -> Iterator[Signal]:
    """Burstiness: how much sentence length varies.

    Uniform lengths lean machine, uneven lengths lean human. This is the weakest
    detector here and the thresholds come from the shared catalogue metrics, not
    from a fitted model -- treat it as a tiebreaker, never as a finding.

    >>> from ductus.base import Span
    >>> t = ("One two three four five six. " * 7)
    >>> [s.name for s in rhythm(t, Span.of(t, 0, len(t)))]
    ['low-burstiness']
    """
    cfg = metrics()
    lengths = [len(_WORD_RE.findall(x)) for x in _SENTENCE_RE.findall(span.quote)]
    lengths = [n for n in lengths if n >= 3]
    if len(lengths) < cfg["min_sentences_for_rhythm"]:
        return
    mean = statistics.mean(lengths)
    sd = statistics.pstdev(lengths)
    cv = sd / mean if mean else 0.0
    floor = cfg["sentence_len_cv_min"]
    if cv < floor:
        yield Signal("low-burstiness", "machine", 0.25, "rhythm", round(cv, 3),
                     f"uniform sentence lengths (mean {mean:.0f} words, sd {sd:.1f}); "
                     "metronomic rhythm")
    elif cv > floor * 2:
        yield Signal("high-burstiness", "human", 0.25, "rhythm", round(cv, 3),
                     f"uneven sentence lengths (mean {mean:.0f} words, sd {sd:.1f})")


#: The registry the ``detectors=`` seam resolves names against.
DETECTORS: dict[str, Callable[[str, Span], Iterator[Signal]]] = {
    "tells": tells,
    "forensic": forensic,
    "rhetoric": rhetoric,
    "rhythm": rhythm,
}


def detectors_from(
    names: Sequence[str] | Sequence[Callable[[str, Span], Iterator[Signal]]] | None,
) -> tuple[list[Callable[[str, Span], Iterator[Signal]]], tuple[str, ...]]:
    """Resolve a detector spec into callables and their names.

    >>> fns, names = detectors_from(["forensic"])
    >>> names
    ('forensic',)
    >>> _, names = detectors_from(None)
    >>> names
    ('tells', 'forensic', 'rhetoric', 'rhythm')
    """
    if names is None:
        names = list(DETECTORS)
    fns, labels = [], []
    for n in names:
        if isinstance(n, str):
            if n not in DETECTORS:
                raise KeyError(f"unknown detector {n!r}; known: {sorted(DETECTORS)}")
            fns.append(DETECTORS[n])
            labels.append(n)
        else:
            fns.append(n)
            labels.append(getattr(n, "__name__", "custom"))
    return fns, tuple(labels)
