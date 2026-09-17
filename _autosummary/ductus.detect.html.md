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

Adding a model-based detector (Fast-DetectGPT, Binoculars, a vendor API) means
writing one more function of this shape. Nothing else in the package changes.

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

| [`DETECTORS`](#ductus.detect.DETECTORS)   | The registry the `detectors=` seam resolves names against.   |
|--------------------------------------------------------------|--------------------------------------------------------------|

### Functions

| [`detectors_from`](#ductus.detect.detectors_from)(names)   | Resolve a detector spec into callables and their names.            |
|--------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`forensic`](#ductus.detect.forensic)(text, span)    | Typographic and mechanical artifacts of how the text was produced. |
| [`rhetoric`](#ductus.detect.rhetoric)(text, span)    | Sentence shapes a phrase catalogue cannot see.                     |
| [`rhythm`](#ductus.detect.rhythm)(text, span)      | Burstiness: how much sentence length varies.                       |
| [`tells`](#ductus.detect.tells)(text, span)       | Catalogue phrase matches, as signals.                              |

### ductus.detect.DETECTORS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Span](ductus.base.html.md#ductus.base.Span)], [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Signal](ductus.base.html.md#ductus.base.Signal)]]]* *= {'forensic': <function forensic>, 'rhetoric': <function rhetoric>, 'rhythm': <function rhythm>, 'tells': <function tells>}*

The registry the `detectors=` seam resolves names against.

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
