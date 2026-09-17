"""Cutting a text into the units that get scored -- the ``segmenter=`` seam.

Two segmenters ship. ``paragraph`` is the default because it is the unit a
reader actually perceives as "a part of the text", and because scores over very
short spans are noise. ``sentence`` is there for finer localisation.

Both are pure generators over exact character offsets: a segmenter never copies
or normalises the text, so every offset it yields indexes the original.

>>> list(spans_of("One two.\\n\\nThree four.", "paragraph"))[1].quote
'Three four.'
>>> [s.quote for s in spans_of("A short one. And a second.", "sentence")]
['A short one.', 'And a second.']
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

from ductus.base import Span

__all__ = ["SEGMENTERS", "paragraph_spans", "sentence_spans", "spans_of"]

# A paragraph is a run of lines with no wholly blank line inside it.
_PARAGRAPH_RE = re.compile(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*")
# Deliberately simple: abbreviations will occasionally split wrong. A sentence
# splitter that is right 99% of the time costs a model; this one costs nothing,
# and a mis-split moves a boundary rather than losing text.
_SENTENCE_RE = re.compile(r"\s*(\S.*?(?:[.!?](?=\s|$)|$))", re.DOTALL)


def paragraph_spans(text: str) -> Iterator[Span]:
    """Yield one span per paragraph.

    >>> [ (s.start, s.end) for s in paragraph_spans("ab\\n\\ncd") ]
    [(0, 2), (4, 6)]
    """
    for m in _PARAGRAPH_RE.finditer(text):
        yield Span.of(text, m.start(), m.end(), level="paragraph")


def sentence_spans(text: str) -> Iterator[Span]:
    """Yield one span per sentence, never crossing a paragraph boundary.

    >>> [s.quote for s in sentence_spans("Hi there! Bye.")]
    ['Hi there!', 'Bye.']
    """
    for para in paragraph_spans(text):
        for m in _SENTENCE_RE.finditer(para.quote):
            start, end = para.start + m.start(1), para.start + m.end(1)
            if end > start:
                yield Span.of(text, start, end, level="sentence")


def document_spans(text: str) -> Iterator[Span]:
    """Yield the whole text as one span. Useful when only a roll-up is wanted.

    >>> len(list(document_spans("anything at all")))
    1
    """
    yield Span.of(text, 0, len(text), level="document")


#: The registry the ``segmenter=`` seam resolves names against.
SEGMENTERS: dict[str, Callable[[str], Iterator[Span]]] = {
    "paragraph": paragraph_spans,
    "sentence": sentence_spans,
    "document": document_spans,
}


def spans_of(
    text: str, segmenter: str | Callable[[str], Iterator[Span]]
) -> Iterator[Span]:
    """Resolve ``segmenter`` (a name or a callable) and run it over ``text``.

    >>> len(list(spans_of("a\\n\\nb", "paragraph")))
    2
    >>> len(list(spans_of("a b", lambda t: iter([Span.of(t, 0, 1)]))))
    1
    """
    fn = SEGMENTERS[segmenter] if isinstance(segmenter, str) else segmenter
    return fn(text)
