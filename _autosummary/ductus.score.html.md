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
: One of [`ductus.base.LABELS`](ductus.base.html.md#ductus.base.LABELS), and never finer than the evidence.

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

| [`LEAN_THRESHOLD`](#ductus.score.LEAN_THRESHOLD)   | Beyond this, a segment is called as leaning one way.          |
|-------------------------------------------------------------------|---------------------------------------------------------------|
| [`STRENGTH_FLOOR`](#ductus.score.STRENGTH_FLOOR)   | Below this much total evidence, no label is claimed at all.   |
| [`EVIDENCE_FULL`](#ductus.score.EVIDENCE_FULL)    | The total signal weight at which `strength` saturates at 1.0. |

### Functions

| [`aggregate`](#ductus.score.aggregate)(signals)   | Reduce evidence to `(lean, strength, label)`.   |
|-----------------------------------------------------------------------|-------------------------------------------------|

### ductus.score.EVIDENCE_FULL *= 1.5*

The total signal weight at which `strength` saturates at 1.0. Not fitted –
it is “about three moderate signals”, chosen to be legible rather than exact.

### ductus.score.LEAN_THRESHOLD *= 0.45*

Beyond this, a segment is called as leaning one way.

### ductus.score.STRENGTH_FLOOR *= 0.2*

Below this much total evidence, no label is claimed at all.

### ductus.score.aggregate(signals)

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
