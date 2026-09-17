# ductus.tools

The verb SSOT: plain functions, JSON-ready in, JSON-ready out.

Deliberately surface-agnostic. Nothing here prints, exits, or knows what a CLI,
an MCP server or an HTTP request is – `__main__` runs these through `cw`,
`py2mcp.mk_mcp_from_refs(['ductus.tools:gauge', ...])` would expose the same
functions as MCP tools, and `qh.mk_app` would serve them over HTTP, all from
this one list. Adding a surface never means writing a second implementation.

```pycon
>>> out = gauge("Great question! Let's delve in.", format="json")
>>> import json; json.loads(out)["document"]["label"]
'leans-machine'
>>> [d["name"] for d in detectors()][:2]
['tells', 'forensic']
```

### Functions

| [`detectors`](#ductus.tools.detectors)()                                 | The available detectors and what each one looks at.                        |
|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`gauge`](#ductus.tools.gauge)(source, \*[, format, segmenter, ...]) | Gauge how machine-written a text reads, and render the result.             |
| [`host_mutating`](#ductus.tools.host_mutating)(fn)                           | Mark a verb that changes the machine it runs on, rather than only reading. |
| [`install_skills`](#ductus.tools.install_skills)(\*[, target, write])         | Link this package's shipped skills into an agent host's skills directory.  |
| [`segmenters`](#ductus.tools.segmenters)()                                | The available ways of cutting the text into scored units.                  |
| [`tells`](#ductus.tools.tells)(\*[, tier])                           | The tells catalogue, optionally filtered to one tier (E, W or S).          |

### ductus.tools.detectors()

The available detectors and what each one looks at.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

```pycon
>>> {d["name"] for d in detectors()} == set(DETECTORS)
True
```

### ductus.tools.gauge(source, , format='markdown', segmenter='paragraph', detectors=None, judgments=None, out=None, title='Reading')

Gauge how machine-written a text reads, and render the result.

`source` is a file path, a literal string, or `-` for stdin.
`format` is one of markdown, json, html. `detectors` is a comma-separated
subset of the available detectors. `judgments` is a path to a JSON file of
an agent’s own readings, folded in alongside the deterministic ones. With
`out`, the result is written there and a one-line summary is returned.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> gauge("Sent it Friday. Two sites, not five.").splitlines()[0]
'# Reading'
```

### ductus.tools.host_mutating(fn)

Mark a verb that changes the machine it runs on, rather than only reading.

Declared at the definition site so surfaces can filter on it without anyone
writing a second list of verbs. A CLI user invoking one of these chose to; a
remote MCP caller did not necessarily, so [`ductus.mcp`](ductus.mcp.html.md#module-ductus.mcp) leaves them out.

```pycon
>>> host_mutating(lambda: None).mutates_host
True
>>> getattr(segmenters, "mutates_host", False)
False
```

### ductus.tools.install_skills(, target=None, write=False)

Link this package’s shipped skills into an agent host’s skills directory.

Defaults to `~/.claude/skills`. Dry-run unless `write` is passed.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> r = install_skills()
>>> r["dry_run"], len(r["skills"]) > 0
(True, True)
```

### ductus.tools.segmenters()

The available ways of cutting the text into scored units.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> segmenters()
['paragraph', 'sentence', 'document']
```

### ductus.tools.tells(, tier=None)

The tells catalogue, optionally filtered to one tier (E, W or S).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]

```pycon
>>> len(tells()) > 10
True
>>> {t["tier"] for t in tells(tier="E")}
{'E'}
```
