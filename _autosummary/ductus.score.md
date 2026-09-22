# ductus.score

Turning evidence into a lean – the `aggregate=` seam.

The deliberate design choice of this package lives here: \*\*there is no
percentage\*\*. Every commercial detector emits a number like “87% AI”, and that
number is how people get falsely accused, because it reads as a calibrated
probability and is nothing of the kind.

What comes out instead is three things a reader can argue with:

`lean`
: -1 (all evidence argues human) to +1 (all evidence argues machine). It is a
  ratio of the weights present, not a probability of anything.

`strength`
: 0 to 1: how much evidence there was at all. A lean of +1.0 from one weak
  signal is a different claim from +1.0 from six, and collapsing those into
  one number is exactly the lie this module refuses to tell.

`label`
: One of [`ductus.base.LABELS`](ductus.base.md#ductus.base.LABELS), and never finer than the evidence.

Replacing this with a scorer calibrated on labelled data is one keyword
argument; see `misc/docs/roadmap.md`.

```pycon
>>> from ductus.base import Signal
>>> aggregate([Signal("a", "machine", 0.5, "d"), Signal("b", "machine", 0.4, "d")])
(1.0, 0.6, 'leans-machine')
>>> aggregate([Signal("a", "machine", 0.5, "d"), Signal("b", "human", 0.5, "d")])
(0.0, 0.667, 'mixed-signals')
>>> aggregate([])
(0.0, 0.0, 'no-evidence')
```

### Module Attributes

| [`LEAN_THRESHOLD`](#ductus.score.LEAN_THRESHOLD)    | Beyond this, a segment is called as leaning one way.                                                                                                                               |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`STRENGTH_FLOOR`](#ductus.score.STRENGTH_FLOOR)    | Below this much total evidence, no label is claimed at all.                                                                                                                        |
| [`EVIDENCE_FULL`](#ductus.score.EVIDENCE_FULL)     | The total signal weight at which `strength` saturates at 1.0.                                                                                                                      |
| [`REFERENCE_CHARS`](#ductus.score.REFERENCE_CHARS)   | How much text [`density_aggregate()`](#ductus.score.density_aggregate) treats as one "unit" of reading.                                                                |
| [`SEGMENT_RATE_FULL`](#ductus.score.SEGMENT_RATE_FULL) | The fraction of a document's segments that must carry directional evidence before [`roll_up()`](#ductus.score.roll_up) calls the document's `strength` full. |

### Functions

| [`aggregate`](#ductus.score.aggregate)(signals, \*[, n_chars])         | Reduce evidence to `(lean, strength, label)`.                                                                         |
|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| [`density_aggregate`](#ductus.score.density_aggregate)(signals, \*[, n_chars]) | Like [`aggregate()`](#ductus.score.aggregate), but `strength` is an evidence *rate*, not a total. |
| [`roll_up`](#ductus.score.roll_up)(segments, \*[, n_chars])          | A document verdict computed from the **segment verdicts**, not the signal pool.                                       |

### ductus.score.EVIDENCE_FULL *= 1.5*

The total signal weight at which `strength` saturates at 1.0. Not fitted –
it is “about three moderate signals”, chosen to be legible rather than exact.

### ductus.score.LEAN_THRESHOLD *= 0.45*

Beyond this, a segment is called as leaning one way.

### ductus.score.REFERENCE_CHARS *= 1000*

How much text [`density_aggregate()`](#ductus.score.density_aggregate) treats as one “unit” of reading. Above this
length a passage must produce proportionally more evidence to reach the same
`strength`. Selected on human-written text; see `misc/docs/phase-2-results.md`.

### ductus.score.SEGMENT_RATE_FULL *= 0.35*

The fraction of a document’s segments that must carry directional evidence before
[`roll_up()`](#ductus.score.roll_up) calls the document’s `strength` full. A *rate*, not a count, which
is what makes the roll-up length-normalised by construction.

### ductus.score.STRENGTH_FLOOR *= 0.2*

Below this much total evidence, no label is claimed at all.

### ductus.score.aggregate(signals, , n_chars=None)

Reduce evidence to `(lean, strength, label)`. Length-blind, by construction.

Neutral signals count toward `strength` but never toward `lean` – they
are real evidence that the passage is unusual without being evidence about
who wrote it.

`n_chars` is accepted and **deliberately ignored**. The seam passes it so a
scorer *can* reason about how much text produced the evidence; this one does not,
which is a choice with a measured cost: on human-written text the chance of a
false accusation rises from 11% to 74% with document length alone, because two
stray signals weigh the same in 600 characters as in 3000. See
[`density_aggregate()`](#ductus.score.density_aggregate) and `misc/docs/phase-2-results.md`.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> from ductus.base import Signal
>>> aggregate([Signal("x", "human", 0.6, "d")])
(-1.0, 0.4, 'leans-human')
>>> aggregate([Signal("x", "neutral", 0.9, "d")])
(0.0, 0.6, 'uncertain')
```

### ductus.score.density_aggregate(signals, , n_chars=None)

Like [`aggregate()`](#ductus.score.aggregate), but `strength` is an evidence *rate*, not a total.

Two signals in 600 characters is a different claim from two in 3000, and the
length-blind scorer cannot tell them apart. This one divides the evidence by how
much text produced it, above a reference length of [`REFERENCE_CHARS`](#ductus.score.REFERENCE_CHARS).

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

### ductus.score.roll_up(segments, , n_chars=None)

A document verdict computed from the **segment verdicts**, not the signal pool.

Pooling every signal in a document and scoring the heap is why length hurt: with a
per-segment false-flag rate of about 3%, the chance that *something* fires grows
with the number of segments, and by thirty segments it is a coin toss. Pooling
treats accumulation as though it were corroboration.

This asks a different question – \*what fraction of this document’s segments carry
directional evidence, and which way do they point\* – and it is length-normalised
by construction rather than by a fitted constant. One flagged segment in twenty is
the same claim whether the document has twenty segments or two hundred.

The two axes keep exactly the meanings they have one level down, which is what
stops “what proportion of segments lean machine” from becoming “what percentage is
AI”:

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

`lean`
: unchanged: the *direction ratio* over the document’s signal weights, exactly as
  [`aggregate()`](#ductus.score.aggregate) computes it. Counting segment *labels* instead was tried and
  reverted – it silently discards evidence in segments that did not reach a
  label, and that evidence is disproportionately human-leaning, which this
  package treats as first-class. It still reaches ±1.0 off a single signal.

`strength`
: how much evidence there is, judged **two ways, and believed at its weakest**:
  the *rate* of directional segments relative to [`SEGMENT_RATE_FULL`](#ductus.score.SEGMENT_RATE_FULL), and
  the evidence *density* per unit text that [`density_aggregate()`](#ductus.score.density_aggregate) uses. Each
  guards a failure the other misses – the rate view catches a long document with
  many segments and one stray flag, the density view catches a long document cut
  into two paragraphs where one stray flag is half of them. A document has to
  satisfy both to be called, which is the conservative direction and the one this
  package’s asymmetry asks for.

Neither axis alone, nor the pair, can be inverted into “how much of this is
machine-written”. See `misc/docs/document-verdict-decision.md`.

```pycon
>>> from ductus.base import Segment, Signal, Span
>>> def seg(label, lean):
...     found = () if label == "no-evidence" else (Signal("t", "machine", 0.5, "d"),)
...     return Segment(span=Span(0, 1, "x"), signals=found, lean=lean,
...                    strength=1.0, label=label)
>>> many = [seg("no-evidence", 0.0)] * 19 + [seg("leans-machine", 1.0)]
>>> roll_up(many)              # one flagged sentence in twenty: a rate of 5%
(1.0, 0.143, 'no-evidence')
>>> few = [seg("leans-machine", 1.0)] * 8 + [seg("no-evidence", 0.0)] * 12
>>> roll_up(few)               # eight in twenty, all pointing the same way
(1.0, 1.0, 'leans-machine')
>>> roll_up([])
(0.0, 0.0, 'no-evidence')
```

One flagged paragraph out of two is a rate of 50% – but not if those two
paragraphs are four thousand characters of text carrying one weak signal:

```pycon
>>> pair = [seg("leans-machine", 1.0), seg("no-evidence", 0.0)]
>>> roll_up(pair)[2]
'leans-machine'
>>> roll_up(pair, n_chars=4000)[2]
'no-evidence'
```
