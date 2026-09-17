# ductus.base

The data model: where a finding lives, what it claims, and how much it weighs.

Four types, and they are the whole contract every other module speaks in.

A [`Span`](#ductus.base.Span) says *where*. It carries character offsets **and** the W3C Web
Annotation redundant selectors (quote, prefix, suffix) so a finding can be
re-anchored after the text is edited, which plain offsets cannot survive.

A [`Signal`](#ductus.base.Signal) is one piece of evidence: a direction, a weight, who produced
it, and a human-readable reason. Signals are never merged or averaged away –
the reason a passage scored the way it did is always recoverable.

A [`Segment`](#ductus.base.Segment) is a unit of text plus the signals that landed on it and the
lean derived from them. A [`Report`](#ductus.base.Report) is the document-level roll-up.

```pycon
>>> text = "The cat sat. It was a fine evening."
>>> span = Span.of(text, 4, 7)
>>> span.quote, span.prefix
('cat', 'The ')
>>> Signal("test", "machine", 0.5, "demo", note="an example").direction
'machine'
```

### Module Attributes

| [`SCHEMA_VERSION`](#ductus.base.SCHEMA_VERSION)   | Bumped when the serialized shape of a Report changes incompatibly.   |
|-------------------------------------------------------------------|----------------------------------------------------------------------|
| [`DIRECTIONS`](#ductus.base.DIRECTIONS)       | What a signal can argue for.                                         |
| [`LABELS`](#ductus.base.LABELS)           | The coarse vocabulary a segment is labelled with.                    |

### Classes

| [`Report`](#ductus.base.Report)(text_sha256, n_chars, document, ...)      | Everything a downstream consumer needs, and nothing it has to guess at.   |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`Segment`](#ductus.base.Segment)(span[, signals, lean, strength, label])  | A unit of text, the signals on it, and the lean they add up to.           |
| [`Signal`](#ductus.base.Signal)(name, direction, weight, detector[, ...]) | One piece of evidence about one span.                                     |
| [`Span`](#ductus.base.Span)(start, end, quote[, prefix, suffix, level]) | A character range, with redundant selectors so it survives an edit.       |

### ductus.base.DIRECTIONS *= ('machine', 'human', 'neutral')*

What a signal can argue for. `neutral` records evidence that is real but
does not discriminate – it is kept because hiding it would be dishonest.

### ductus.base.LABELS *= ('leans-machine', 'leans-human', 'mixed-signals', 'uncertain', 'no-evidence')*

The coarse vocabulary a segment is labelled with. Deliberately not a
percentage: see `docs/why-no-percentage.md`.

### *class* ductus.base.Report(text_sha256, n_chars, document, segments, detectors, segmenter, schema_version='1', calibration='uncalibrated', meta=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything a downstream consumer needs, and nothing it has to guess at.

#### *property* signals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Signal](#ductus.base.Signal), ...]*

Every signal in the report, in document order.

### ductus.base.SCHEMA_VERSION *= '1'*

Bumped when the serialized shape of a Report changes incompatibly.

### *class* ductus.base.Segment(span, signals=(), lean=0.0, strength=0.0, label='no-evidence')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A unit of text, the signals on it, and the lean they add up to.

`lean` runs from -1 (every signal argues human) to +1 (every signal argues
machine). `strength` is how much evidence there is at all – a lean of
+1.0 from a single weak signal is not the same claim as +1.0 from six.

### *class* ductus.base.Signal(name, direction, weight, detector, value=None, note='', span=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One piece of evidence about one span.

`weight` is how much this moves the needle, in `0..1`. It is a weight,
not a probability: two 0.5 signals pointing the same way are stronger than
one, and nothing here claims to be calibrated.

```pycon
>>> Signal("em-dash", "machine", 0.2, "forensic", value=3).name
'em-dash'
```

### *class* ductus.base.Span(start, end, quote, prefix='', suffix='', level='segment')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A character range, with redundant selectors so it survives an edit.

`start`/`end` are a `TextPositionSelector`; `quote` with `prefix`
and `suffix` is a `TextQuoteSelector`. Keeping both is what lets a
viewer re-find a finding after the text around it changed.

```pycon
>>> s = Span.of("one two three", 4, 7, level="sentence")
>>> (s.start, s.end, s.quote, s.level)
(4, 7, 'two', 'sentence')
>>> s.length
3
```

#### contains(other)

Whether `other` falls entirely inside this span.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

```pycon
>>> a, b = Span.of("abcdef", 0, 6), Span.of("abcdef", 2, 4)
>>> a.contains(b), b.contains(a)
(True, False)
```

#### *classmethod* of(text, start, end, , level='segment')

Build a span over `text`, capturing its re-anchoring context.

* **Return type:**
  [`Span`](#ductus.base.Span)

```pycon
>>> Span.of("abcdef", 2, 4).suffix
'ef'
```
