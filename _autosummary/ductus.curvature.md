# ductus.curvature

Model-based detectors – the `[local]` extra. Two more functions of the same shape.

[`fast_detect_gpt()`](#ductus.curvature.fast_detect_gpt) and [`binoculars()`](#ductus.curvature.binoculars) are `(text, span) -> Iterator[Signal]`
like every other detector here. They differ in one way that matters: their evidence
is a number a reader cannot inspect, produced by a language model rather than quoted
from the text. The whole design of how that number becomes a [`Signal`](ductus.base.md#ductus.base.Signal)
is argued in `misc/docs/curvature-as-evidence.md`; the short version is:

* the statistic is the published one, evaluated over the span’s tokens;
* it is compared to **the same statistic over the rest of this document**, never to a
  threshold lifted from a paper’s benchmark – so no calibration is claimed anywhere;
* the standing is banded, not mapped continuously: a mid-range score emits *nothing*,
  because a mid-range score is this detector having nothing to say;
* both directions are emitted, because a detector that can only accuse is not a
  measuring instrument.

The consequence, accepted knowingly: these detectors cannot say whether a whole
document is machine-written. With no rest-of-the-document to compare against, they
return nothing.

`torch` and `transformers` are imported only when a detector actually runs, so
`import ductus` stays as cheap as it was.

```pycon
>>> band_of(0.9) is None, band_of(1.8), band_of(-3.0)
(True, 0.3, 0.45)
>>> round(robust_z(10.0, [1.0, 2.0, 3.0, 4.0, 5.0]), 2)
4.72
```

### Module Attributes

| [`FAST_DETECT_MODEL`](#ductus.curvature.FAST_DETECT_MODEL)   | Single model, used as both the scoring and the sampling model (the analytic same-model setting of Fast-DetectGPT).   |
|----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [`BINOCULARS_OBSERVER`](#ductus.curvature.BINOCULARS_OBSERVER) | Binoculars needs a *closely related* pair sharing one tokenizer, not an arbitrary strong/weak combination.           |
| [`BANDS`](#ductus.curvature.BANDS)               | `(|z| threshold, weight)`, lowest first.                                                                             |
| [`MIN_WINDOWS`](#ductus.curvature.MIN_WINDOWS)         | Fewer comparable windows than this and there is no reference distribution worth the name, so nothing is emitted.     |
| [`MIN_TOKENS`](#ductus.curvature.MIN_TOKENS)          | A span shorter than this is too few tokens for the statistic to mean anything -- roughly a sentence's worth.         |

### Functions

| [`band_of`](#ductus.curvature.band_of)(z[, bands])                           | The weight for a standing of `z`, or `None` when it says nothing.                |
|------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`binoculars`](#ductus.curvature.binoculars)(text, span, \*[, observer, ...])   | Cross-perplexity of a paired observer and performer, as a standing in this text. |
| [`fast_detect_gpt`](#ductus.curvature.fast_detect_gpt)(text, span, \*[, model, ...]) | Conditional probability curvature, read as a standing within this document.      |
| [`robust_z`](#ductus.curvature.robust_z)(value, reference)                    | How far `value` stands out from `reference`, in MADs.                            |

### ductus.curvature.BANDS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), [float](https://docs.python.org/3/builtins/functions.html#float)], ...]* *= ((1.5, 0.3), (2.5, 0.45))*

`(|z| threshold, weight)`, lowest first. Below the first threshold the detector
emits nothing at all – the dead zone is the point, not an oversight. Neither
weight exceeds the strongest deterministic signal: a statistic the reader cannot
inspect does not get to outvote one they can.

### ductus.curvature.BINOCULARS_OBSERVER *= 'distilgpt2'*

Binoculars needs a *closely related* pair sharing one tokenizer, not an
arbitrary strong/weak combination. `distilgpt2` is a distillation of `gpt2`.
The documented upgrade is the paper’s `tiiuae/falcon-7b` pair.

### ductus.curvature.FAST_DETECT_MODEL *= 'gpt2'*

Single model, used as both the scoring and the sampling model (the analytic
same-model setting of Fast-DetectGPT). Small enough for CPU; the documented
upgrade is `EleutherAI/gpt-neo-2.7B`.

### ductus.curvature.MIN_TOKENS *= 16*

A span shorter than this is too few tokens for the statistic to mean anything –
roughly a sentence’s worth.

### ductus.curvature.MIN_WINDOWS *= 6*

Fewer comparable windows than this and there is no reference distribution worth
the name, so nothing is emitted.

### ductus.curvature.band_of(z, bands=((1.5, 0.3), (2.5, 0.45)))

The weight for a standing of `z`, or `None` when it says nothing.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> band_of(1.49) is None
True
>>> band_of(1.5), band_of(2.49), band_of(2.5), band_of(-9.0)
(0.3, 0.3, 0.45, 0.45)
```

### ductus.curvature.binoculars(text, span, , observer='distilgpt2', performer='gpt2', bands=((1.5, 0.3), (2.5, 0.45)), min_windows=6, min_tokens=16, device=None)

Cross-perplexity of a paired observer and performer, as a standing in this text.

Where [`fast_detect_gpt()`](#ductus.curvature.fast_detect_gpt) asks how predictable a passage is, this asks whether
two closely related models are *unusually unsurprised in the same places* – which
generalises better to generators neither model has seen.

Needs the `[local]` extra, and observer and performer must share a tokenizer.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.md#ductus.base.Signal)]

### ductus.curvature.fast_detect_gpt(text, span, , model='gpt2', bands=((1.5, 0.3), (2.5, 0.45)), min_windows=6, min_tokens=16, device=None)

Conditional probability curvature, read as a standing within this document.

A passage a model finds unusually *predictable* compared to the rest of the
document leans machine; an unusually surprising one leans human. Neither claim
is absolute, and none of the paper’s benchmark thresholds are used.

Needs the `[local]` extra. The first call downloads and caches the proxy model;
later calls on the same text cost no model time at all.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.md#ductus.base.Signal)]

### ductus.curvature.robust_z(value, reference)

How far `value` stands out from `reference`, in MADs.

Median and MAD rather than mean and standard deviation: on a mixed document the
machine-written stretches are exactly the outliers that would drag a mean toward
themselves and hide the thing being looked for.

A degenerate reference (every value identical) yields `0.0`, which falls in the
dead zone and so emits nothing.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

```pycon
>>> robust_z(3.0, [1.0, 2.0, 3.0, 4.0, 5.0])
0.0
>>> robust_z(1.0, [1.0, 1.0, 1.0])
0.0
```
