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

Several readers’ judgments go to the same `judgments` argument, one source each; what
enters the report is then the sentences at least `k` of them agree on, with the
per-reader counts beside it ([`ductus.consensus`](ductus.consensus.html.md#module-ductus.consensus)). [`baseline()`](#ductus.tools.baseline) takes the same
measure on reference texts, and `gauge(baseline=...)` sets the two side by side.

### Functions

| [`baseline`](#ductus.tools.baseline)(sources, \*[, judgments_dir, k, ...])   | The multi-reader consensus density on reference texts, to read a new text beside.   |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`detectors`](#ductus.tools.detectors)()                                      | The available detectors and what each one looks at.                                 |
| [`gauge`](#ductus.tools.gauge)(source, \*[, format, segmenter, ...])      | Gauge how machine-written a text reads, and render the result.                      |
| [`host_mutating`](#ductus.tools.host_mutating)(fn)                                | Mark a verb that changes the machine it runs on, rather than only reading.          |
| [`host_paths`](#ductus.tools.host_paths)(\*\*roles)                            | Declare which parameters of a verb address the machine's own filesystem.            |
| [`install_skills`](#ductus.tools.install_skills)(\*[, target, write])              | Link this package's shipped skills into an agent host's skills directory.           |
| [`segmenters`](#ductus.tools.segmenters)()                                     | The available ways of cutting the text into scored units.                           |
| [`tells`](#ductus.tools.tells)(\*[, tier])                                | The tells catalogue, optionally filtered to one tier (E, W or S).                   |

### ductus.tools.baseline(sources, , judgments_dir=None, k=2, format='json', out=None)

The multi-reader consensus density on reference texts, to read a new text beside.

`sources` are files – typically the author’s own writing from before the
question arose. Each one’s readers are found by name: `<stem>.*.json` in
`judgments_dir` (default: beside the file), or `<stem>/*.json` under it. Every
text needs at least `k` readers.

The result pools the texts by words and keeps the per-text spread; pass the JSON to
`gauge(baseline=...)` so a report can say *next to this author’s own writing*
instead of giving a bare number. `format` is json or markdown. Quotes from the
reference texts are not included – only counts.

It works on files only, so over HTTP (which refuses server paths) it always
refuses; it is for the CLI, a local MCP host, and the library.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ductus.tools.detectors()

The available detectors and what each one looks at.

```pycon
>>> {d["name"] for d in detectors()} == set(DETECTORS)
True
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]

### ductus.tools.gauge(source, , format='markdown', segmenter='paragraph', detectors=None, judgments=None, k=2, baseline=None, out=None, title=None)

Gauge how machine-written a text reads, and render the result.

`source` is a file path, a literal string, or `-` for stdin.
`format` is one of markdown, json, html. `detectors` is a comma-separated
subset of the available detectors. `title` overrides the heading of the
markdown and html renderings (each has its own default). `judgments` is a path to a JSON file of
an agent’s own readings, folded in alongside the deterministic ones. With
`out`, the result is written there and a one-line summary is returned.

Give `judgments` several times – one file per independent reader – and what is
folded in is no longer each reader’s flags but the sentences at least `k` readers
flag; the report shows each reader’s count and that consensus per 1,000 words.
`baseline` is the output of [`baseline()`](#ductus.tools.baseline) on reference texts (a path, the
JSON text, or the parsed dict), shown beside the consensus; a previous reading’s
`meta["readers"]` works too, as a one-text baseline.

```pycon
>>> gauge("Sent it Friday. Two sites, not five.").splitlines()[0]
'# Reading'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

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

### ductus.tools.host_paths(\*\*roles)

Declare which parameters of a verb address the machine’s own filesystem.

A sibling of [`host_mutating()`](#ductus.tools.host_mutating), and the same idea: the fact is stated once,
at the verb’s own definition, and every surface reads it from there. A surface
that never writes a second verb list also never writes a second list of which
arguments are dangerous on it.

`role` is `"read"` for a parameter the verb may read a file from, and
`"write"` for one it may write a file to. Both are ordinary, correct behaviour
at a CLI, where the caller and the filesystem belong to the same person. They are
an arbitrary file read and an arbitrary file write on a surface where they do not
– so [`ductus.http`](ductus.http.html.md#module-ductus.http) refuses them, driven by this declaration rather than by
knowing anything about `gauge`.

```pycon
>>> sorted(gauge.host_paths.items())
[('baseline', 'read'), ('judgments', 'read'), ('out', 'write'), ('source', 'read')]
>>> getattr(segmenters, "host_paths", {})
{}
```

### ductus.tools.install_skills(, target=None, write=False)

Link this package’s shipped skills into an agent host’s skills directory.

Defaults to `~/.claude/skills`. Dry-run unless `write` is passed.

```pycon
>>> r = install_skills()
>>> r["dry_run"], len(r["skills"]) > 0
(True, True)
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### ductus.tools.segmenters()

The available ways of cutting the text into scored units.

```pycon
>>> segmenters()
['paragraph', 'sentence', 'document']
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ductus.tools.tells(, tier=None)

The tells catalogue, optionally filtered to one tier (E, W or S).

```pycon
>>> len(tells()) > 10
True
>>> {t["tier"] for t in tells(tier="E")}
{'E'}
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]
