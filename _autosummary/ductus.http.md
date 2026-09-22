# ductus.http

The HTTP surface: the same verbs the CLI dispatches, served over HTTP.

Like [`ductus.mcp`](ductus.mcp.md#module-ductus.mcp), there is **no second verb list here**. [`ROUTED_FUNCS`](#ductus.http.ROUTED_FUNCS)
is *derived* from `ductus.tools._dispatch_funcs` – the one list `cw` builds
the CLI from – so no two surfaces can drift apart and there is no parity test to
write. `qh.mk_app` turns those callables into a FastAPI app; `qh.export_ts_client`
turns the same app’s OpenAPI into the typed client the frontend imports. One registry,
three emitters.

The core did not change to make this work, which is the roadmap’s standing claim.
`ductus.tools` still imports nothing about HTTP, and `qh` lives in the `[http]`
extra, so `import ductus` is unaffected by installing it.

**What this surface found.** A verb list that is safe at a CLI is not automatically
safe when the caller is a stranger. `gauge(source=...)` reads a file when the string
names one, and `gauge(out=...)` writes one – exactly right when you typed the
command yourself, an arbitrary file read and an arbitrary file write when you did not.
Neither the CLI nor a local stdio MCP host can see that, because on those surfaces it
is not a bug. `_guard()` refuses both, driven by the `host_paths` declaration on
the verb itself rather than by this module knowing anything about `gauge`.

Run it:

```default
pip install 'ductus[http]'
ductus-http                     # http://127.0.0.1:8000, /docs for the OpenAPI UI
```

```pycon
>>> ROUTED_FUNCS[0].__name__
'gauge'
>>> "install_skills" in [f.__name__ for f in ROUTED_FUNCS]  # host-mutating, left out
False
```

### Module Attributes

| [`ROUTED_FUNCS`](#ductus.http.ROUTED_FUNCS)   | One callable per read-only verb, derived from the CLI's own list.   |
|-----------------------------------------------------------------|---------------------------------------------------------------------|
| [`DESCRIPTION`](#ductus.http.DESCRIPTION)    | The service description, carried into the OpenAPI document.         |

### Functions

| [`export_client`](#ductus.http.export_client)(\*[, class_name, base_url, app])   | The TypeScript client for this surface, generated from its own OpenAPI.   |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`main`](#ductus.http.main)()                                           | Serve on `127.0.0.1:8000`.                                                |
| [`mk_app`](#ductus.http.mk_app)(\*[, funcs, title, description, ...])     | Build a FastAPI app serving `funcs`, one POST endpoint per verb.          |

### ductus.http.DESCRIPTION *= 'Gauge which parts of a text read as machine-written, with every finding anchored to\\nthe exact characters that carry it.\\n\\nThis service never returns a percentage, a confidence, or a verdict about a person,\\nand a caller should not synthesise one from what it does return. It gives a lean in\\n[-1, +1], an evidence strength, a coarse label, and the signals behind them -- each\\nwith a quote that can be checked against the text.\\n\\nIts false-positive rate on human-written text is measured: with the default\\ndetectors, 6.0% of 350 human-written documents are called \`leans-machine\`. Every one\\nof those is wrong. A flagged \*sentence\* is much better evidence than a flagged\\n\*document\* -- the per-sentence rate is 0.4-2%.\\n\\nThe bias runs toward formal, fluent, essayistic prose, not toward simple prose. In\\nthe measured corpus the native-speaker control was the most-accused group.\\n\\n"No findings" is a weak result, not a clean bill.\\n'*

The service description, carried into the OpenAPI document. An HTTP client that
reads anything at all reads this, so the limits belong here and not only in a
README. The numbers are the measured ones – see
`misc/docs/reducing-false-accusations.md`.

### ductus.http.ROUTED_FUNCS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [Any](https://docs.python.org/3/library/typing.html#typing.Any)], ...]* *= (<function gauge>, <function detectors>, <function segmenters>, <function tells>)*

One callable per read-only verb, derived from the CLI’s own list. Never
hand-written. The filter reads `mutates_host`, declared at each verb’s own
definition – the same rule, and the same reason, as [`ductus.mcp`](ductus.mcp.md#module-ductus.mcp).

### ductus.http.export_client(, class_name='DuctusClient', base_url='', app=None)

The TypeScript client for this surface, generated from its own OpenAPI.

The frontend imports the result rather than hand-writing fetch calls, so a
changed Python signature becomes a TypeScript type error instead of a runtime
surprise. `base_url` defaults to empty, which makes every request relative –
correct when the app and the UI are served from the same origin, as
[`mk_app()`](#ductus.http.mk_app) arranges.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ductus.http.main()

Serve on `127.0.0.1:8000`. The `ductus-http` console script.

Host and port come from `DUCTUS_HTTP_HOST` / `DUCTUS_HTTP_PORT` so a
container can move them without a code change. The default binds to loopback:
a tool that can call a text machine-written should not appear on a network
because someone ran it to look at it.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ductus.http.mk_app(\*, funcs=(<function gauge>, <function detectors>, <function segmenters>, <function tells>), title='ductus', description='Gauge which parts of a text read as machine-written, with every finding anchored to\\\\nthe exact characters that carry it.\\\\n\\\\nThis service never returns a percentage, a confidence, or a verdict about a person,\\\\nand a caller should not synthesise one from what it does return. It gives a lean in\\\\n[-1, +1], an evidence strength, a coarse label, and the signals behind them -- each\\\\nwith a quote that can be checked against the text.\\\\n\\\\nIts false-positive rate on human-written text is measured: with the default\\\\ndetectors, 6.0% of 350 human-written documents are called \`leans-machine\`. Every one\\\\nof those is wrong. A flagged \*sentence\* is much better evidence than a flagged\\\\n\*document\* -- the per-sentence rate is 0.4-2%.\\\\n\\\\nThe bias runs toward formal, fluent, essayistic prose, not toward simple prose. In\\\\nthe measured corpus the native-speaker control was the most-accused group.\\\\n\\\\n"No findings" is a weak result, not a clean bill.\\\\n', guard_host_paths=True, ui=None, \*\*qh_kwargs)

Build a FastAPI app serving `funcs`, one POST endpoint per verb.

`guard_host_paths` is the seam for the one case that wants it off: a service
bound to loopback for your own use, where reading a local file by name is the
convenience it is at a CLI. It defaults to on, because the safe reading of an
ambiguous deployment is the one that does not hand out the filesystem.

`ui` is a directory of built frontend assets to serve at `/`. When it is
`None` the default location is used if it exists and is skipped if it does not,
so the API works with no frontend built and the two are served same-origin when
one is – which is also what lets a browser test drive it without CORS.

Extra keyword arguments pass straight through to `qh.mk_app`.

Raises [`ImportError`](https://docs.python.org/3/builtins/exceptions.html#ImportError) with an actionable message when the extra is missing.
