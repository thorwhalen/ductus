# ductus.segment

Cutting a text into the units that get scored – the `segmenter=` seam.

Two segmenters ship. `paragraph` is the default because it is the unit a
reader actually perceives as “a part of the text”, and because scores over very
short spans are noise. `sentence` is there for finer localisation.

Both are pure generators over exact character offsets: a segmenter never copies
or normalises the text, so every offset it yields indexes the original.

```pycon
>>> list(spans_of("One two.\n\nThree four.", "paragraph"))[1].quote
'Three four.'
>>> [s.quote for s in spans_of("A short one. And a second.", "sentence")]
['A short one.', 'And a second.']
```

### Module Attributes

| [`SEGMENTERS`](#ductus.segment.SEGMENTERS)   | The registry the `segmenter=` seam resolves names against.   |
|---------------------------------------------------------------|--------------------------------------------------------------|

### Functions

| [`paragraph_spans`](#ductus.segment.paragraph_spans)(text)     | Yield one span per paragraph.                                      |
|----------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`sentence_spans`](#ductus.segment.sentence_spans)(text)      | Yield one span per sentence, never crossing a paragraph boundary.  |
| [`spans_of`](#ductus.segment.spans_of)(text, segmenter) | Resolve `segmenter` (a name or a callable) and run it over `text`. |

### ductus.segment.SEGMENTERS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/builtins/stdtypes.html#str)], [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Span](ductus.base.html.md#ductus.base.Span)]]]* *= {'document': <function document_spans>, 'paragraph': <function paragraph_spans>, 'sentence': <function sentence_spans>}*

The registry the `segmenter=` seam resolves names against.

### ductus.segment.paragraph_spans(text)

Yield one span per paragraph.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Span`](ductus.base.html.md#ductus.base.Span)]

```pycon
>>> [ (s.start, s.end) for s in paragraph_spans("ab\n\ncd") ]
[(0, 2), (4, 6)]
```

### ductus.segment.sentence_spans(text)

Yield one span per sentence, never crossing a paragraph boundary.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Span`](ductus.base.html.md#ductus.base.Span)]

```pycon
>>> [s.quote for s in sentence_spans("Hi there! Bye.")]
['Hi there!', 'Bye.']
```

### ductus.segment.spans_of(text, segmenter)

Resolve `segmenter` (a name or a callable) and run it over `text`.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Span`](ductus.base.html.md#ductus.base.Span)]

```pycon
>>> len(list(spans_of("a\n\nb", "paragraph")))
2
>>> len(list(spans_of("a b", lambda t: iter([Span.of(t, 0, 1)]))))
1
```
