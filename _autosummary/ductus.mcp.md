# ductus.mcp

The MCP surface: the same verbs the CLI dispatches, emitted as MCP tools.

There is **no second verb list here**, and that is the whole design. [`TOOL_REFS`](#ductus.mcp.TOOL_REFS)
is *derived* from `ductus.tools._dispatch_funcs` – the same list `cw` builds
the CLI from – so the two surfaces cannot drift apart. The roadmap’s rule is that a
parity test between two surfaces means there are two implementations; the fix is to
have one list, not two lists and a test that watches them.

The refs are **strings**, resolved by `py2mcp` at call time, so `ductus.tools`
never imports MCP and neither does the core. `py2mcp` lives in the `[mcp]` extra
and is imported only when a server is actually built.

Verbs marked [`ductus.tools.host_mutating()`](ductus.tools.md#ductus.tools.host_mutating) are left out. `install_skills`
symlinks into an agent host’s skills directory: a person typing it at a CLI chose to,
a remote caller did not necessarily. That filter reads a property declared at the
function’s own definition, so it is still one list.

`gauge(out=...)` writes a file, and is *not* excluded – writing the report you asked
for is the verb doing its job. A deployed server that should not write anywhere is what
`middleware=` is for; it is passed straight through, along with `auth=`.

Run it:

```default
pip install 'ductus[mcp]'
ductus-mcp                      # stdio, for a local agent host
```

```pycon
>>> TOOL_REFS[:2]
('ductus.tools:gauge', 'ductus.tools:detectors')
>>> all(ref.startswith("ductus.tools:") for ref in TOOL_REFS)
True
>>> "ductus.tools:install_skills" in TOOL_REFS  # host-mutating, left out
False
```

### Module Attributes

| [`TOOL_REFS`](#ductus.mcp.TOOL_REFS)    | One ref per read-only verb, derived from the CLI's own list.   |
|---------------------------------------------------------------|----------------------------------------------------------------|
| [`INSTRUCTIONS`](#ductus.mcp.INSTRUCTIONS) | What the server tells a model about itself.                    |

### Functions

| [`main`](#ductus.mcp.main)()                                      | Serve on stdio.                               |
|----------------------------------------------------------------------------------------------|-----------------------------------------------|
| [`mk_mcp`](#ductus.mcp.mk_mcp)(\*[, name, refs, instructions, ...]) | Build an MCP server exposing `refs` as tools. |

### ductus.mcp.INSTRUCTIONS *= 'Gauge which parts of a text read as machine-written, with every finding anchored to\\nthe exact characters that carry it.\\n\\nThis server never returns a percentage, a confidence, or a verdict about a person, and\\na caller should not synthesise one from what it does return. It gives a lean in\\n[-1, +1], an evidence strength, a coarse label, and the signals behind them -- each\\nwith a quote that can be checked against the text.\\n\\nIts false-positive rate on human-written text is measured: with the default detectors,\\n6.0% of 350 human-written documents are called leans-machine, and every one of those is\\nwrong. A flagged \*sentence\* is much better evidence than a flagged \*document\* -- the\\nper-sentence rate is 0.4-2%. The bias runs toward formal, fluent, essayistic prose\\nrather than toward simple prose; in the measured corpus the native-speaker control was\\nthe most-accused group.\\n\\n"No findings" is a weak result, not a clean bill.\\n'*

What the server tells a model about itself. The limits are here rather than in a
README because this is the only description an MCP client ever reads.

### ductus.mcp.TOOL_REFS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]* *= ('ductus.tools:gauge', 'ductus.tools:detectors', 'ductus.tools:segmenters', 'ductus.tools:tells')*

One ref per read-only verb, derived from the CLI’s own list. Never hand-written.

### ductus.mcp.main()

Serve on stdio. The `ductus-mcp` console script.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ductus.mcp.mk_mcp(, name='ductus', refs=('ductus.tools:gauge', 'ductus.tools:detectors', 'ductus.tools:segmenters', 'ductus.tools:tells'), instructions='Gauge which parts of a text read as machine-written, with every finding anchored to\\\\nthe exact characters that carry it.\\\\n\\\\nThis server never returns a percentage, a confidence, or a verdict about a person, and\\\\na caller should not synthesise one from what it does return. It gives a lean in\\\\n[-1, +1], an evidence strength, a coarse label, and the signals behind them -- each\\\\nwith a quote that can be checked against the text.\\\\n\\\\nIts false-positive rate on human-written text is measured: with the default detectors,\\\\n6.0% of 350 human-written documents are called leans-machine, and every one of those is\\\\nwrong. A flagged \*sentence\* is much better evidence than a flagged \*document\* -- the\\\\nper-sentence rate is 0.4-2%. The bias runs toward formal, fluent, essayistic prose\\\\nrather than toward simple prose; in the measured corpus the native-speaker control was\\\\nthe most-accused group.\\\\n\\\\n"No findings" is a weak result, not a clean bill.\\\\n', middleware=None, auth=None)

Build an MCP server exposing `refs` as tools.

`middleware=` and `auth=` pass straight through to `py2mcp`. They are where
a deployed connector attaches metering and authentication without the core
learning that either exists.

Raises [`ImportError`](https://docs.python.org/3/builtins/exceptions.html#ImportError) with an actionable message when the extra is missing.
