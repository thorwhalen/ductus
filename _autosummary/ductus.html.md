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

**This package’s own false-positive rate is measured, and it is not small**: 20.6% of
350 human-written documents are called `leans-machine` by the shipped defaults, and a
flagged *sentence* is much better evidence than a flagged *document*. See
`misc/docs/phase-2-results.md` before reporting anything from this.

### Functions

| [`aggregate`](#ductus.aggregate)(signals, \*[, n_chars])                | Reduce evidence to `(lean, strength, label)`.                                                                         |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| [`density_aggregate`](#ductus.density_aggregate)(signals, \*[, n_chars])        | Like [`aggregate()`](#ductus.aggregate), but `strength` is an evidence *rate*, not a total. |
| [`gauge`](#ductus.gauge)(text, \*[, segmenter, detectors, ...])     | Score `text` and roll the segments up into a report.                                                                  |
| [`iter_segments`](#ductus.iter_segments)(text, \*[, segmenter, ...])        | Yield one scored segment at a time.                                                                                   |
| [`iter_tell_matches`](#ductus.iter_tell_matches)(text, \*[, rules, tiers, ...]) | Every catalogue hit in `text`, in document order.                                                                     |
| [`load_rules`](#ductus.load_rules)([path])                               | The catalogue's rules, compiled.                                                                                      |
| [`to_html`](#ductus.to_html)(report, \*[, text, title, subtitle])     | A single self-contained HTML file.                                                                                    |
| [`to_json`](#ductus.to_json)(report, \*[, indent])                    | The whole report, serialized.                                                                                         |
| [`to_markdown`](#ductus.to_markdown)(report, \*[, text, title])           | A readable diagnosis: synopsis first, then the flagged segments.                                                      |

### Classes

| [`Report`](#ductus.Report)(text_sha256, n_chars, document, ...)      | Everything a downstream consumer needs, and nothing it has to guess at.   |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`Segment`](#ductus.Segment)(span[, signals, lean, strength, label])  | A unit of text, the signals on it, and the lean they add up to.           |
| [`Signal`](#ductus.Signal)(name, direction, weight, detector[, ...]) | One piece of evidence about one span.                                     |
| [`Span`](#ductus.Span)(start, end, quote[, prefix, suffix, level]) | A character range, with redundant selectors so it survives an edit.       |
| [`TellMatch`](#ductus.TellMatch)(rule_id, tier, message, start, ...)    | Where a rule fired, and on what text.                                     |
| [`TellRule`](#ductus.TellRule)(id, tier, message, patterns[, ...])     | One named rule: a tier, a message, and the patterns that trigger it.      |

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

### *class* ductus.TellMatch(rule_id, tier, message, start, end, matched, weight=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where a rule fired, and on what text.

#### weight *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.0*

The rule’s evidential weight – its per-rule override when it has one, else its
tier’s. Carried here so a consumer never has to re-derive it from `tier`, which
would silently discard the override. Defaulted so existing constructions still
work; [`iter_tell_matches()`](#ductus.iter_tell_matches) always fills it in.

### *class* ductus.TellRule(id, tier, message, patterns, weight_override=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One named rule: a tier, a message, and the patterns that trigger it.

#### *property* weight *: [float](https://docs.python.org/3/builtins/functions.html#float)*

the per-rule override when set, else the tier’s.

```pycon
>>> TellRule("x", "E", "m", (), weight_override=0.15).weight
0.15
>>> TellRule("x", "E", "m", ()).weight
0.5
```

* **Type:**
  Evidential weight

#### weight_override *: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None)* *= None*

An optional per-rule override of the tier’s weight, read from `weight:` in
the catalogue. It exists because a rule’s **tier** and its \*\*evidential
weight\*\* answer different questions, and a rule can be right about one and
wrong about the other: `summary-closer` catches “In conclusion,” which is
reasonable style advice (`acquaint` enforces tiers) and almost worthless as
evidence about *who wrote the text* (`ductus` uses weights). Overriding the
weight changes this package only – `acquaint` reads `tier` and never
`weight`. Changing a tier is a two-package decision; see
`misc/docs/document-verdict-decision.md`.

### ductus.aggregate(signals, , n_chars=None)

Reduce evidence to `(lean, strength, label)`. Length-blind, by construction.

Neutral signals count toward `strength` but never toward `lean` – they
are real evidence that the passage is unusual without being evidence about
who wrote it.

`n_chars` is accepted and **deliberately ignored**. The seam passes it so a
scorer *can* reason about how much text produced the evidence; this one does not,
which is a choice with a measured cost: on human-written text the chance of a
false accusation rises from 11% to 74% with document length alone, because two
stray signals weigh the same in 600 characters as in 3000. See
[`density_aggregate()`](#ductus.density_aggregate) and `misc/docs/phase-2-results.md`.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> from ductus.base import Signal
>>> aggregate([Signal("x", "human", 0.6, "d")])
(-1.0, 0.4, 'leans-human')
>>> aggregate([Signal("x", "neutral", 0.9, "d")])
(0.0, 0.6, 'uncertain')
```

### ductus.density_aggregate(signals, , n_chars=None)

Like [`aggregate()`](#ductus.aggregate), but `strength` is an evidence *rate*, not a total.

Two signals in 600 characters is a different claim from two in 3000, and the
length-blind scorer cannot tell them apart. This one divides the evidence by how
much text produced it, above a reference length of `REFERENCE_CHARS`.

`lean` is untouched. It still reads ±1.0 off a single weak signal, and that
jaggedness is deliberate – smoothing it is how `lean` would quietly become a
quantity-integrating score, which is to say a probability. See
`misc/docs/what-calibration-means-here.md`.

The scaling only ever *divides*, never multiplies, so this scorer can only remove
accusations, never add one. Short passages behave exactly as before.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> from ductus.base import Signal
>>> evidence = [Signal("x", "machine", 0.4, "d")]
>>> density_aggregate(evidence, n_chars=500)        # short: unchanged
(1.0, 0.267, 'leans-machine')
>>> density_aggregate(evidence, n_chars=4000)       # the same evidence, spread thin
(1.0, 0.067, 'no-evidence')
>>> density_aggregate(evidence) == aggregate(evidence)  # no length, no opinion
True
```

### ductus.gauge(text, \*, segmenter='paragraph', detectors=None, aggregate=<function density_aggregate>, extra_signals=())

Score `text` and roll the segments up into a report.

The document-level verdict is computed from the **segment verdicts**, by
[`ductus.score.roll_up()`](ductus.score.html.md#ductus.score.roll_up), not from the pooled signals. Pooling every signal in
the document and scoring the heap is what made a long human document more likely
to be accused for being long: with a ~3% per-segment false-flag rate, the chance
that something fires grows with the segment count. What is asked instead is what
*fraction* of the segments carry directional evidence and which way they point –
length-normalised by construction. `misc/docs/document-verdict-decision.md` has
the argument and what it cost.

The segments themselves are untouched by this, and remain the better evidence: a
flagged sentence says much more than a flagged document.

* **Return type:**
  [`Report`](ductus.base.html.md#ductus.base.Report)

```pycon
>>> r = gauge("It is important to note that this is a robust tapestry.")
>>> r.document.lean > 0 and r.n_chars == 55
True
>>> r.segmenter, len(r.detectors)
('paragraph', 4)
```

### ductus.iter_segments(text, \*, segmenter='paragraph', detectors=None, aggregate=<function density_aggregate>, extra_signals=())

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

| [`base`](ductus.base.html.md#module-ductus.base)           | The data model: where a finding lives, what it claims, and how much it weighs.   |
|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`core`](ductus.core.html.md#module-ductus.core)           | The core: stream segments, or take the whole report.                             |
| [`curvature`](ductus.curvature.html.md#module-ductus.curvature) | Model-based detectors -- the `[local]` extra.                                    |
| [`data`](ductus.data.html.md#module-ductus.data)           |                                                                                  |
| [`detect`](ductus.detect.html.md#module-ductus.detect)       | The detectors -- the `detectors=` seam.                                          |
| [`http`](ductus.http.html.md#module-ductus.http)           | The HTTP surface: the same verbs the CLI dispatches, served over HTTP.           |
| [`mcp`](ductus.mcp.html.md#module-ductus.mcp)             | The MCP surface: the same verbs the CLI dispatches, emitted as MCP tools.        |
| [`render`](ductus.render.html.md#module-ductus.render)       | Turning a report into something a person reads: JSON, Markdown, or HTML.         |
| [`score`](ductus.score.html.md#module-ductus.score)         | Turning evidence into a lean -- the `aggregate=` seam.                           |
| [`segment`](ductus.segment.html.md#module-ductus.segment)     | Cutting a text into the units that get scored -- the `segmenter=` seam.          |
| [`tells`](ductus.tells.html.md#module-ductus.tells)         | The tells catalogue: named regular-expression patterns, tiered by confidence.    |
| [`tools`](ductus.tools.html.md#module-ductus.tools)         | The verb SSOT: plain functions, JSON-ready in, JSON-ready out.                   |
