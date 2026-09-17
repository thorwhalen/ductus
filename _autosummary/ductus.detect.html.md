# ductus.detect

The detectors – the `detectors=` seam. Each one turns a span into evidence.

A detector is a plain function `(text, span) -> Iterator[Signal]`. That is the
entire interface; there is no base class and nothing to register. Four ship, all
deterministic and dependency-free:

`tells`
: Catalogue phrase matches (see [`ductus.tells`](ductus.tells.html.md#module-ductus.tells)). Finds vocabulary.

`forensic`
: Typographic and mechanical artifacts – em dashes, mixed apostrophes, a hard
  line break mid-sentence, trailing whitespace. The cheapest signal in the
  package and often the most decisive, because these are traces of *how* the
  text was produced rather than of how it reads.

`rhetoric`
: Sentence *shapes* a catalogue cannot see: the “not X but Y” antithesis, a
  colon introducing a three-part parallel enumeration, concession-then-pivot.

`rhythm`
: Burstiness – the variance of sentence length. Weak evidence, and reported
  as weak.

Two more ship behind the `[local]` extra – `fast-detect-gpt` and
`binoculars`, in [`ductus.curvature`](ductus.curvature.html.md#module-ductus.curvature). They are registered here so they can be
named, but whether they belong in [`DEFAULT_DETECTORS`](#ductus.detect.DEFAULT_DETECTORS) is settled by
measurement, not by being new – see `misc/docs/phase-1-results.md`.

Adding another one – a vendor API, a supervised classifier – means writing one more
function of this shape. Nothing else in the package changes.

```pycon
>>> from ductus.base import Span
>>> t = "The results were not merely good, but transformative."
>>> [s.name for s in rhetoric(t, Span.of(t, 0, len(t)))]
['not-x-but-y']
>>> t2 = "It matters — a lot — and always has."
>>> [s.name for s in forensic(t2, Span.of(t2, 0, len(t2)))]
['em-dash', 'em-dash']
```

### Module Attributes

| [`DETECTORS`](#ductus.detect.DETECTORS)         | The registry the `detectors=` seam resolves names against.                                                                      |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| [`DEFAULT_DETECTORS`](#ductus.detect.DEFAULT_DETECTORS) | a detector joins this tuple only after it has measurably beaten what is already here on `tests/fixtures/mixed_authorship.json`. |

### Functions

| [`binoculars`](#ductus.detect.binoculars)(text, span, \*[, observer, ...])   | Cross-perplexity of a paired observer and performer, as a standing in this text.   |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`detectors_from`](#ductus.detect.detectors_from)(names)                         | Resolve a detector spec into callables and their names.                            |
| [`fast_detect_gpt`](#ductus.detect.fast_detect_gpt)(text, span, \*[, model, ...]) | Conditional probability curvature, read as a standing within this document.        |
| [`forensic`](#ductus.detect.forensic)(text, span)                          | Typographic and mechanical artifacts of how the text was produced.                 |
| [`rhetoric`](#ductus.detect.rhetoric)(text, span)                          | Sentence shapes a phrase catalogue cannot see.                                     |
| [`rhythm`](#ductus.detect.rhythm)(text, span)                            | Burstiness: how much sentence length varies.                                       |
| [`tells`](#ductus.detect.tells)(text, span)                             | Catalogue phrase matches, as signals.                                              |

### ductus.detect.DEFAULT_DETECTORS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('tells', 'forensic', 'rhetoric', 'rhythm')*

a detector
joins this tuple only after it has measurably beaten what is already here on
`tests/fixtures/mixed_authorship.json`. See `misc/docs/phase-1-results.md`.

* **Type:**
  What `detectors=None` means. Deliberately *not* `list(DETECTORS)`

### ductus.detect.DETECTORS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Span](ductus.base.html.md#ductus.base.Span)], [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Signal](ductus.base.html.md#ductus.base.Signal)]]]* *= {'binoculars': <function binoculars>, 'fast-detect-gpt': <function fast_detect_gpt>, 'forensic': <function forensic>, 'rhetoric': <function rhetoric>, 'rhythm': <function rhythm>, 'tells': <function tells>}*

The registry the `detectors=` seam resolves names against. It holds more than
the default: the model-based detectors are nameable here so `--detectors
fast-detect-gpt` works, without being on by default. Registering is cheap –
[`ductus.curvature`](ductus.curvature.html.md#module-ductus.curvature) imports nothing heavier than [`ductus.base`](ductus.base.html.md#module-ductus.base) until one
of its detectors is actually called.

### ductus.detect.binoculars(text, span, , observer='distilgpt2', performer='gpt2', bands=((1.5, 0.3), (2.5, 0.45)), min_windows=6, min_tokens=16, device=None)

Cross-perplexity of a paired observer and performer, as a standing in this text.

Where [`fast_detect_gpt()`](#ductus.detect.fast_detect_gpt) asks how predictable a passage is, this asks whether
two closely related models are *unusually unsurprised in the same places* – which
generalises better to generators neither model has seen.

Needs the `[local]` extra, and observer and performer must share a tokenizer.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

### ductus.detect.detectors_from(names)

Resolve a detector spec into callables and their names.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Span`](ductus.base.html.md#ductus.base.Span)], [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]]], [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]]

```pycon
>>> fns, names = detectors_from(["forensic"])
>>> names
('forensic',)
>>> _, names = detectors_from(None)
>>> names
('tells', 'forensic', 'rhetoric', 'rhythm')
```

### ductus.detect.fast_detect_gpt(text, span, , model='gpt2', bands=((1.5, 0.3), (2.5, 0.45)), min_windows=6, min_tokens=16, device=None)

Conditional probability curvature, read as a standing within this document.

A passage a model finds unusually *predictable* compared to the rest of the
document leans machine; an unusually surprising one leans human. Neither claim
is absolute, and none of the paper’s benchmark thresholds are used.

Needs the `[local]` extra. The first call downloads and caches the proxy model;
later calls on the same text cost no model time at all.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

### ductus.detect.forensic(text, span)

Typographic and mechanical artifacts of how the text was produced.

Several of these argue for a *human*, which is the point: a detector that can
only ever accuse is not a measuring instrument.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

```pycon
>>> from ductus.base import Span
>>> t = "he said\nand then left"
>>> [s.name for s in forensic(t, Span.of(t, 0, len(t)))]
['mid-sentence-newline', 'no-terminal-punctuation']
```

### ductus.detect.rhetoric(text, span)

Sentence shapes a phrase catalogue cannot see.

These are the patterns that survive a model being told to avoid “AI words”,
which is why they matter more than vocabulary as models improve.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

```pycon
>>> from ductus.base import Span
>>> t = "This is a pattern: you plan it, you build it, and you ship it."
>>> [s.name for s in rhetoric(t, Span.of(t, 0, len(t)))]
['colon-tricolon']
```

### ductus.detect.rhythm(text, span)

Burstiness: how much sentence length varies.

Uniform lengths lean machine, uneven lengths lean human. This is the weakest
detector here and the thresholds come from the shared catalogue metrics, not
from a fitted model – treat it as a tiebreaker, never as a finding.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

```pycon
>>> from ductus.base import Span
>>> t = ("One two three four five six. " * 7)
>>> [s.name for s in rhythm(t, Span.of(t, 0, len(t)))]
['low-burstiness']
```

### ductus.detect.tells(text, span)

Catalogue phrase matches, as signals. Quoted text is skipped.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

```pycon
>>> from ductus.base import Span
>>> t = "Let's delve into it."
>>> [(s.name, s.direction) for s in tells(t, Span.of(t, 0, len(t)))]
[('ai-vocabulary', 'machine')]
>>> q = 'Models overuse "delve", so avoid it.'
>>> list(tells(q, Span.of(q, 0, len(q))))
[]
```
