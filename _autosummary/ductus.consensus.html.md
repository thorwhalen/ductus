# ductus.consensus

Several close readers, and the sentences at least `k` of them agree on.

One reader’s judgments are noisy in a way that hides the thing being measured. Fresh,
strict readers given the same instructions each flag dozens of shapes in a long essay,
mostly on text the previous reader passed, so a raw count does not move when a rewrite
helps and does not move when it does not. What does move is the set of \*\*sentences
that independent readers both flag\*\*. That is what this module counts.

Two numbers come out, and both are descriptions of how a text reads, never of who
wrote it:

- **per-reader counts** – how many sentences each reader flagged, each direction. Large
  and unequal is normal; it is the reader variance this module exists to see past.
- **consensus density** – sentences flagged by at least `k` readers, per 1,000 words.
  A density on its own is a bare number. [`pooled()`](#ductus.consensus.pooled) takes the same measure over
  reference texts – the author’s own earlier writing – so a report can put the two
  side by side instead.

The unit is the sentence, from the same segmenter `gauge(segmenter="sentence")` uses,
so a judgment and a sentence are anchored by the same rule as everywhere else: a quote
that no longer occurs in the text is **dropped and counted**, never re-anchored.

Pure functions over judgment records (dicts); nothing here reads a file.

```pycon
>>> text = "It is a pattern. You decide, invest, regret. Sent it Friday."
>>> a = [{"quote": "You decide, invest, regret", "direction": "machine"}]
>>> b = [{"quote": "invest, regret.", "direction": "machine"},
...      {"quote": "It is a pattern", "direction": "machine"}]
>>> c = consensus(text, [a, b], names=["a", "b"])
>>> [(r["name"], r["machine"]) for r in c["readers"]]
[('a', 1), ('b', 2)]
>>> c["machine"]["count"], [u["quote"] for u in c["machine"]["units"]]
(1, ['You decide, invest, regret.'])
```

### Module Attributes

| [`DEFAULT_K`](#ductus.consensus.DEFAULT_K)   | How many readers must flag a sentence for it to count.   |
|--------------------------------------------------------------|----------------------------------------------------------|

### Functions

| [`anchor_judgment`](#ductus.consensus.anchor_judgment)(text, judgment)               | Where a judgment lands in `text`, or `None` when its quote is gone.             |
|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`consensus`](#ductus.consensus.consensus)(text, readers, \*[, k, names, ...]) | Per-reader counts and the sentences at least `k` readers flag, each direction.  |
| [`consensus_signals`](#ductus.consensus.consensus_signals)(text, result)               | One signal per consensus unit, anchored to the unit's own characters.           |
| [`pooled`](#ductus.consensus.pooled)(results)                               | The same measure over several texts, pooled by words, with the per-text spread. |

### ductus.consensus.DEFAULT_K *= 2*

How many readers must flag a sentence for it to count. Two is the smallest number
that is agreement rather than one reader’s taste.

### ductus.consensus.anchor_judgment(text, judgment)

Where a judgment lands in `text`, or `None` when its quote is gone.

A judgment carries a `quote` (anchored at its first occurrence) or explicit
`start`/`end` offsets. A quote that does not occur is dropped by every caller –
mis-anchoring would attach a reason to text it was never about.

```pycon
>>> anchor_judgment("one two three", {"quote": "two"})
(4, 7)
>>> anchor_judgment("one two three", {"quote": "four"}) is None
True
>>> anchor_judgment("one two three", {"start": 0, "end": 3})
(0, 3)
```

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ductus.consensus.consensus(text, readers, , k=2, names=None, segmenter='sentence')

Per-reader counts and the sentences at least `k` readers flag, each direction.

`readers` is one list of judgment records per reader. `names` labels them in the
result (default `reader 1`, `reader 2`, …). `segmenter` is the unit readers
must agree on – a sentence by default, any of [`ductus.segment.SEGMENTERS`](ductus.segment.html.md#ductus.segment.SEGMENTERS) or
a callable.

Everything returned is JSON-ready: counts, densities per 1,000 words, and each
consensus unit with its offsets, its quote, the readers that flagged it and the
shapes they named.

```pycon
>>> t = "One. Two. Three."
>>> r = [[{"quote": "Two.", "direction": "human"}]] * 3
>>> c = consensus(t, r, k=3)
>>> c["human"]["count"], c["machine"]["count"], c["n_words"]
(1, 0, 3)
>>> consensus(t, r, k=4)
Traceback (most recent call last):
    ...
ValueError: k=4 needs at least 4 readers; got 3
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### ductus.consensus.consensus_signals(text, result)

One signal per consensus unit, anchored to the unit’s own characters.

This is what a multi-reader reading contributes to a report: not every reader’s
every flag – most of which the next reader would not have made – but the units
they agree on, weighted by the mean of the agreeing readers’ weights.

```pycon
>>> t = "One. Two. Three."
>>> c = consensus(t, [[{"quote": "Two", "direction": "machine", "name": "x"}]] * 2)
>>> s = consensus_signals(t, c)[0]
>>> s.name, s.detector, s.span.quote, s.note
('reader-consensus', 'readers', 'Two.', 'flagged by 2 of 2 readers (reader 1, reader 2): x')
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Signal`](ductus.base.html.md#ductus.base.Signal)]

### ductus.consensus.pooled(results)

The same measure over several texts, pooled by words, with the per-text spread.

Pooled means total consensus units over total words – a long reference text counts
for more than a short one, as it should. The per-text range is reported beside it,
because two reference essays at 2.4 and 9.3 per 1,000 words say something a single
pooled 5.0 hides.

```pycon
>>> a = {"k": 2, "n_readers": 2, "unit": "sentence", "n_words": 1000,
...      "machine": {"count": 2}, "human": {"count": 1}}
>>> b = {**a, "n_words": 500, "machine": {"count": 5}, "human": {"count": 0}}
>>> p = pooled([a, b])
>>> p["machine"]
{'count': 7, 'per_1000_words': 4.67, 'range': [2.0, 10.0]}
>>> p["n_texts"], p["n_words"]
(2, 1500)
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
