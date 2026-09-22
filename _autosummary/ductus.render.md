# ductus.render

Turning a report into something a person reads: JSON, Markdown, or HTML.

Three renderers, all pure functions of a [`Report`](ductus.base.md#ductus.base.Report):

[`to_json()`](#ductus.render.to_json)
: The full structure, for a frontend or another program.

[`to_markdown()`](#ductus.render.to_markdown)
: A synopsis, then one section per flagged segment with its stats and the
  reason each signal fired.

[`to_html()`](#ductus.render.to_html)
: A single self-contained file – no build step, no CDN – showing the text
  with the flagged spans shaded, the reason on hover, light and dark themes.

The HTML follows the two-channel rule for annotated text: \*\*hue encodes score
only\*\* (a perceptually-uniform ramp, lightness re-clamped per theme), while
overlap is shown structurally in a separate lane under each paragraph. Loading
both meanings into one colour is what makes overlapping highlights unreadable.

```pycon
>>> from ductus.core import gauge
>>> r = gauge("Let's delve into this robust tapestry.")
>>> "delve" in to_markdown(r)
True
>>> to_html(r).startswith("<!doctype html>")
True
>>> import json; json.loads(to_json(r))["schema_version"]
'1'
```

### Functions

| [`to_html`](#ductus.render.to_html)(report, \*[, text, title, subtitle])   | A single self-contained HTML file.                               |
|-------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`to_json`](#ductus.render.to_json)(report, \*[, indent])                  | The whole report, serialized.                                    |
| [`to_markdown`](#ductus.render.to_markdown)(report, \*[, text, title])         | A readable diagnosis: synopsis first, then the flagged segments. |

### ductus.render.to_html(report, , text=None, title='Where this reads as machine-written', subtitle='')

A single self-contained HTML file. `text` defaults to the spans’ own quotes.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from ductus.core import gauge
>>> h = to_html(gauge("Let's delve in."))
>>> "<mark" in h and "prefers-color-scheme" in h
True
```

### ductus.render.to_json(report, , indent=2)

The whole report, serialized.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from ductus.core import gauge
>>> d = __import__("json").loads(to_json(gauge("delve")))
>>> d["segments"][0]["signals"][0]["detector"]
'tells'
```

### ductus.render.to_markdown(report, , text=None, title='Reading')

A readable diagnosis: synopsis first, then the flagged segments.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from ductus.core import gauge
>>> md = to_markdown(gauge("In conclusion, this is a robust tapestry."))
>>> md.splitlines()[0].startswith("# ")
True
```
