# ductus.tells

The tells catalogue: named regular-expression patterns, tiered by confidence.

This is the cheap floor of detection – it finds *phrases* a model overuses, and
by construction it cannot find *shapes* (see [`ductus.detect`](ductus.detect.html.md#module-ductus.detect) for those). It
is fast, it needs nothing installed, and every hit points at the exact characters
that matched, which is what makes it useful for highlighting rather than scoring.

The catalogue is data (`ductus/data/tells.yaml`) and a keyword argument, so a
list derived from one author’s own writing can replace it without code changes.

`acquaint` consumes [`iter_tell_matches()`](#ductus.tells.iter_tell_matches) directly for the deterministic
half of its `deslop` check, and layers recipient calibration on top.

```pycon
>>> ms = list(iter_tell_matches("Great question! Let's delve into this tapestry."))
>>> sorted({m.rule_id for m in ms})
['ai-vocabulary', 'chat-leftover', 'exclamation']
>>> m = next(m for m in ms if m.rule_id == 'chat-leftover')
>>> m.tier, m.matched.lower()
('E', 'great question')
>>> list(iter_tell_matches("Sending the export on Friday. Two sites, not five."))
[]
```

### Module Attributes

| [`TIER_WEIGHT`](#ductus.tells.TIER_WEIGHT)   | How much each tier is worth as evidence, on the 0..1 Signal scale.   |
|----------------------------------------------------------------|----------------------------------------------------------------------|

### Functions

| [`iter_tell_matches`](#ductus.tells.iter_tell_matches)(text, \*[, rules, tiers, ...])   | Every catalogue hit in `text`, in document order.   |
|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| [`load_catalogue`](#ductus.tells.load_catalogue)([path])                             | Read the catalogue file.                            |
| [`load_rules`](#ductus.tells.load_rules)([path])                                 | The catalogue's rules, compiled.                    |
| [`metrics`](#ductus.tells.metrics)([path])                                    | The catalogue's shared numeric thresholds.          |

### Classes

| [`TellMatch`](#ductus.tells.TellMatch)(rule_id, tier, message, start, ...)   | Where a rule fired, and on what text.                                |
|--------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`TellRule`](#ductus.tells.TellRule)(id, tier, message, patterns[, ...])    | One named rule: a tier, a message, and the patterns that trigger it. |

### ductus.tells.TIER_WEIGHT *= {'E': 0.5, 'S': 0.15, 'W': 0.3}*

How much each tier is worth as evidence, on the 0..1 Signal scale.
E is near-certain but still not 1.0 – a quoted model output is not a
model-written document, and nothing in this package claims certainty.

### *class* ductus.tells.TellMatch(rule_id, tier, message, start, end, matched, weight=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where a rule fired, and on what text.

#### weight *: [float](https://docs.python.org/3/builtins/functions.html#float)* *= 0.0*

The rule’s evidential weight – its per-rule override when it has one, else its
tier’s. Carried here so a consumer never has to re-derive it from `tier`, which
would silently discard the override. Defaulted so existing constructions still
work; [`iter_tell_matches()`](#ductus.tells.iter_tell_matches) always fills it in.

### *class* ductus.tells.TellRule(id, tier, message, patterns, weight_override=None)

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

### ductus.tells.iter_tell_matches(text, , rules=None, tiers=None, offset=0)

Every catalogue hit in `text`, in document order.

`offset` is added to every position, so a caller scanning one segment of a
larger document gets offsets into the document.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`TellMatch`](#ductus.tells.TellMatch)]

```pycon
>>> [m.rule_id for m in iter_tell_matches("In conclusion, it's important to note this.")]
['summary-closer', 'throat-clearing']
>>> [m.start for m in iter_tell_matches("delve", offset=100)]
[100]
>>> [m.rule_id for m in iter_tell_matches("delve", tiers=["E"])]
[]
```

### ductus.tells.load_catalogue(path=None)

Read the catalogue file. Cached; pass a path to use a different one.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> sorted(load_catalogue())
['metrics', 'rules']
```

### ductus.tells.load_rules(path=None)

The catalogue’s rules, compiled.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`TellRule`](#ductus.tells.TellRule), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]

```pycon
>>> rules = load_rules()
>>> len(rules) > 10 and all(r.patterns for r in rules)
True
>>> sorted({r.tier for r in rules})
['E', 'S', 'W']
```

### ductus.tells.metrics(path=None)

The catalogue’s shared numeric thresholds.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> metrics()["min_sentences_for_rhythm"] > 0
True
```
