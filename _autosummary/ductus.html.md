# ductus

ductus – gauge which parts of a text read as machine-written, and why.

In palaeography the *ductus* is the characteristic manner and sequence of strokes
by which a scribe’s hand is recognised. This package looks for the equivalent in
prose: not a verdict about who wrote something, but evidence about how it reads,
attached to the exact characters that carry it.

```pycon
>>> from ductus import gauge
>>> report = gauge("Great question! Let's delve into this robust tapestry.")
>>> report.document.label
'leans-machine'
>>> report.segments[0].signals[0].name
'chat-leftover'
```

Every finding is a [`Signal`](#ductus.Signal) with a direction, a weight, the detector that
produced it, a reason, and a [`Span`](#ductus.Span) carrying both character offsets and
W3C-style quote/prefix/suffix selectors, so highlights survive an edit.

**There is no percentage anywhere in this package, and that is deliberate.** A
number like “87% AI” reads as a calibrated probability, is not one, and is how
people get falsely accused. What you get instead is a lean in [-1, +1], an
evidence strength, and a coarse label you can argue with. See
[`ductus.score`](ductus.score.html.md#module-ductus.score).

Three seams, each one keyword argument with a working default:
`segmenter=` (how the text is cut up), `detectors=` (what produces evidence),
`aggregate=` (how evidence becomes a lean).

### Functions

| [`aggregate`](#ductus.aggregate)(signals)                               | Reduce evidence to `(lean, strength, label)`.                    |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`gauge`](#ductus.gauge)(text, \*[, segmenter, detectors, ...])     | Score `text` and roll the segments up into a report.             |
| [`iter_segments`](#ductus.iter_segments)(text, \*[, segmenter, ...])        | Yield one scored segment at a time.                              |
| [`iter_tell_matches`](#ductus.iter_tell_matches)(text, \*[, rules, tiers, ...]) | Every catalogue hit in `text`, in document order.                |
| [`load_rules`](#ductus.load_rules)([path])                               | The catalogue's rules, compiled.                                 |
| [`to_html`](#ductus.to_html)(report, \*[, text, title, subtitle])     | A single self-contained HTML file.                               |
| [`to_json`](#ductus.to_json)(report, \*[, indent])                    | The whole report, serialized.                                    |
| [`to_markdown`](#ductus.to_markdown)(report, \*[, text, title])           | A readable diagnosis: synopsis first, then the flagged segments. |

### Classes

| [`Report`](#ductus.Report)(text_sha256, n_chars, document, ...)      | Everything a downstream consumer needs, and nothing it has to guess at.   |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`Segment`](#ductus.Segment)(span[, signals, lean, strength, label])  | A unit of text, the signals on it, and the lean they add up to.           |
| [`Signal`](#ductus.Signal)(name, direction, weight, detector[, ...]) | One piece of evidence about one span.                                     |
| [`Span`](#ductus.Span)(start, end, quote[, prefix, suffix, level]) | A character range, with redundant selectors so it survives an edit.       |
| [`TellMatch`](#ductus.TellMatch)(rule_id, tier, message, start, ...)    | Where a rule fired, and on what text.                                     |
| [`TellRule`](#ductus.TellRule)(id, tier, message, patterns)            | One named rule: a tier, a message, and the patterns that trigger it.      |

### *class* ductus.Report(text_sha256, n_chars, document, segments, detectors, segmenter, schema_version='1', calibration='uncalibrated', meta=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything a downstream consumer needs, and nothing it has to guess at.

#### *property* signals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Signal](ductus.base.html.md#ductus.base.Signal), ...]*

Every signal in the report, in document order.

### *class* ductus.Segment(span, signals=(), lean=0.0, strength=0.0, label='no-evidence')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A unit of text, the signals on it, and the lean they add up to.

`lean` runs from -1 (every signal argues human) to +1 (every signal argues
machine). `strength` is how much evidence there is at all – a lean of
+1.0 from a single weak signal is not the same claim as +1.0 from six.

### *class* ductus.Signal(name, direction, weight, detector, value=None, note='', span=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One piece of evidence about one span.

`weight` is how much this moves the needle, in `0..1`. It is a weight,
not a probability: two 0.5 signals pointing the same way are stronger than
one, and nothing here claims to be calibrated.

```pycon
>>> Signal("em-dash", "machine", 0.2, "forensic", value=3).name
'em-dash'
```

### *class* ductus.Span(start, end, quote, prefix='', suffix='', level='segment')

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
  [`Span`](ductus.base.html.md#ductus.base.Span)

```pycon
>>> Span.of("abcdef", 2, 4).suffix
'ef'
```

### *class* ductus.TellMatch(rule_id, tier, message, start, end, matched)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where a rule fired, and on what text.

### *class* ductus.TellRule(id, tier, message, patterns)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One named rule: a tier, a message, and the patterns that trigger it.

### ductus.aggregate(signals)

Reduce evidence to `(lean, strength, label)`.

Neutral signals count toward `strength` but never toward `lean` – they
are real evidence that the passage is unusual without being evidence about
who wrote it.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> from ductus.base import Signal
>>> aggregate([Signal("x", "human", 0.6, "d")])
(-1.0, 0.4, 'leans-human')
>>> aggregate([Signal("x", "neutral", 0.9, "d")])
(0.0, 0.6, 'uncertain')
```

### ductus.gauge(text, \*, segmenter='paragraph', detectors=None, aggregate=<function aggregate>, extra_signals=())

Score `text` and roll the segments up into a report.

The document-level lean is computed over *all* signals in the document, not
by averaging the segment leans – averaging would let two short, heavily
flagged paragraphs outvote a long clean one.

* **Return type:**
  [`Report`](ductus.base.html.md#ductus.base.Report)

```pycon
>>> r = gauge("It is important to note that this is a robust tapestry.")
>>> r.document.lean > 0 and r.n_chars == 55
True
>>> r.segmenter, len(r.detectors)
('paragraph', 4)
```

### ductus.iter_segments(text, \*, segmenter='paragraph', detectors=None, aggregate=<function aggregate>, extra_signals=())

Yield one scored segment at a time.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Segment`](ductus.base.html.md#ductus.base.Segment)]

```pycon
>>> segs = list(iter_segments("Let's delve in.\n\nSent it Friday."))
>>> len(segs), segs[0].label
(2, 'leans-machine')
```

### ductus.iter_tell_matches(text, , rules=None, tiers=None, offset=0)

Every catalogue hit in `text`, in document order.

`offset` is added to every position, so a caller scanning one segment of a
larger document gets offsets into the document.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`TellMatch`](ductus.tells.html.md#ductus.tells.TellMatch)]

```pycon
>>> [m.rule_id for m in iter_tell_matches("In conclusion, it's important to note this.")]
['summary-closer', 'throat-clearing']
>>> [m.start for m in iter_tell_matches("delve", offset=100)]
[100]
>>> [m.rule_id for m in iter_tell_matches("delve", tiers=["E"])]
[]
```

### ductus.load_rules(path=None)

The catalogue’s rules, compiled.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`TellRule`](ductus.tells.html.md#ductus.tells.TellRule), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]

```pycon
>>> rules = load_rules()
>>> len(rules) > 10 and all(r.patterns for r in rules)
True
>>> sorted({r.tier for r in rules})
['E', 'S', 'W']
```

### ductus.to_html(report, , text=None, title='Where this reads as machine-written', subtitle='')

A single self-contained HTML file. `text` defaults to the spans’ own quotes.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from ductus.core import gauge
>>> h = to_html(gauge("Let's delve in."))
>>> "<mark" in h and "prefers-color-scheme" in h
True
```

### ductus.to_json(report, , indent=2)

The whole report, serialized.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from ductus.core import gauge
>>> d = __import__("json").loads(to_json(gauge("delve")))
>>> d["segments"][0]["signals"][0]["detector"]
'tells'
```

### ductus.to_markdown(report, , text=None, title='Reading')

A readable diagnosis: synopsis first, then the flagged segments.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from ductus.core import gauge
>>> md = to_markdown(gauge("In conclusion, this is a robust tapestry."))
>>> md.splitlines()[0].startswith("# ")
True
```

### Modules

| [`base`](ductus.base.html.md#module-ductus.base)       | The data model: where a finding lives, what it claims, and how much it weighs.   |
|--------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`core`](ductus.core.html.md#module-ductus.core)       | The core: stream segments, or take the whole report.                             |
| [`data`](ductus.data.html.md#module-ductus.data)       |                                                                                  |
| [`detect`](ductus.detect.html.md#module-ductus.detect)   | The detectors -- the `detectors=` seam.                                          |
| [`render`](ductus.render.html.md#module-ductus.render)   | Turning a report into something a person reads: JSON, Markdown, or HTML.         |
| [`score`](ductus.score.html.md#module-ductus.score)     | Turning evidence into a lean -- the `aggregate=` seam.                           |
| [`segment`](ductus.segment.html.md#module-ductus.segment) | Cutting a text into the units that get scored -- the `segmenter=` seam.          |
| [`tells`](ductus.tells.html.md#module-ductus.tells)     | The tells catalogue: named regular-expression patterns, tiered by confidence.    |
| [`tools`](ductus.tools.html.md#module-ductus.tools)     | The verb SSOT: plain functions, JSON-ready in, JSON-ready out.                   |
