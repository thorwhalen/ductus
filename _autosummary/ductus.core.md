# ductus.core

The core: stream segments, or take the whole report. Everything else is a surface.

Two entry points, and the second is a facade over the first:

[`iter_segments()`](#ductus.core.iter_segments) yields one [`Segment`](ductus.base.md#ductus.base.Segment) at a time as it
scores them – the streaming surface, for long documents and for a UI that wants
to paint as results arrive.

[`gauge()`](#ductus.core.gauge) collects them into a [`Report`](ductus.base.md#ductus.base.Report).

The three seams are keyword arguments, each defaulting to something that
genuinely works rather than to a stub. The `aggregate=` default normalises evidence
by how much text produced it; the length-blind [`ductus.score.aggregate()`](ductus.score.md#ductus.score.aggregate) is still
there, and `misc/docs/phase-2-results.md` has the measurement that chose between
them – on human-written text the length-blind scorer’s false-accusation rate ran from
11% to 74% with document length alone.

| seam         | v1 default                                                                                                       | swap in                                                                                          |
|--------------|------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| `segmenter=` | `"paragraph"`                                                                                                    | `"sentence"`, a callable                                                                         |
| `detectors=` | all four deterministic detectors                                                                                 | a model-based detector                                                                           |
| `aggregate=` | [`ductus.score.density_aggregate()`](ductus.score.md#ductus.score.density_aggregate) | [`ductus.score.aggregate()`](ductus.score.md#ductus.score.aggregate) |

`extra_signals=` is not a seam but an input: evidence produced elsewhere –
by an agent reading the text, by a vendor API – attached to the segment that
contains it. It is how the shipped skills feed a model’s reading back in.

```pycon
>>> report = gauge("Great question! Let's delve into this robust tapestry.")
>>> report.document.label
'leans-machine'
>>> report = gauge("Sent the export Friday. Two sites, not five. Call if it breaks.")
>>> report.document.label
'no-evidence'
```

### Functions

| [`gauge`](#ductus.core.gauge)(text, \*[, segmenter, detectors, ...])   | Score `text` and roll the segments up into a report.   |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| [`iter_segments`](#ductus.core.iter_segments)(text, \*[, segmenter, ...])      | Yield one scored segment at a time.                    |

### ductus.core.gauge(text, \*, segmenter='paragraph', detectors=None, aggregate=<function density_aggregate>, extra_signals=())

Score `text` and roll the segments up into a report.

The document-level verdict is computed from the **segment verdicts**, by
[`ductus.score.roll_up()`](ductus.score.md#ductus.score.roll_up), not from the pooled signals. Pooling every signal in
the document and scoring the heap is what made a long human document more likely
to be accused for being long: with a ~3% per-segment false-flag rate, the chance
that something fires grows with the segment count. What is asked instead is what
*fraction* of the segments carry directional evidence and which way they point –
length-normalised by construction. `misc/docs/document-verdict-decision.md` has
the argument and what it cost.

The segments themselves are untouched by this, and remain the better evidence: a
flagged sentence says much more than a flagged document.

* **Return type:**
  [`Report`](ductus.base.md#ductus.base.Report)

```pycon
>>> r = gauge("It is important to note that this is a robust tapestry.")
>>> r.document.lean > 0 and r.n_chars == 55
True
>>> r.segmenter, len(r.detectors)
('paragraph', 4)
```

### ductus.core.iter_segments(text, \*, segmenter='paragraph', detectors=None, aggregate=<function density_aggregate>, extra_signals=())

Yield one scored segment at a time.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Segment`](ductus.base.md#ductus.base.Segment)]

```pycon
>>> segs = list(iter_segments("Let's delve in.\n\nSent it Friday."))
>>> len(segs), segs[0].label
(2, 'leans-machine')
```
