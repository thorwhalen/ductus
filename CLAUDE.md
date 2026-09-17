# ductus — dev notes for the agent working on this repo

`ductus` gauges which parts of a text read as machine-written, and says why, with every finding anchored to exact characters. The *ductus* is the palaeographer's term for the stroke-manner that identifies a scribe's hand.

## Seams, defaults, surfaces (read this before adding anything)

| Seam | Current default | Built surfaces |
|---|---|---|
| `segmenter=` | `"paragraph"` (also `"sentence"`, `"document"`, or any callable) | **CLI** (`cw` over `tools._dispatch_funcs`), **agent skills** (`ductus/data/skills/`), **MCP** (`py2mcp` over the same list) |
| `detectors=` | `tells`, `forensic`, `rhetoric`, `rhythm` — all deterministic, zero extra deps. `fast-detect-gpt` and `binoculars` ship in the `[local]` extra: registered, **opt-in**, off by default — see `misc/docs/phase-1-results.md` | MCP / HTTP / frontend: **questions answered, not built** — see `misc/docs/roadmap.md` |
| `aggregate=` | `score.density_aggregate` — the same weighted sum, divided by how much text produced it. `score.aggregate` is the length-blind original, still exported | |

**NOT seams**, on purpose: report templates, arg parsing, the four dataclasses, the colour ramp, the tier→weight map.

## Shape

```
base.py      Span / Signal / Segment / Report -- the contract every module speaks
segment.py   segmenters (the `segmenter=` seam); pure generators over exact offsets
tells.py     the catalogue: load_rules, iter_tell_matches, metrics  <- acquaint imports these
detect.py    the four deterministic detectors (the `detectors=` seam) + the registry
curvature.py Fast-DetectGPT and Binoculars ([local] extra, deferred torch import)
score.py     (density_)aggregate(): evidence -> (lean, strength, label). No percentage. Ever.
core.py      iter_segments() streams, gauge() batches over it
render.py    to_json / to_markdown / to_html (self-contained, no CDN, two-channel highlighting)
tools.py     the verb SSOT: JSON in, JSON out, never prints or exits
mcp.py       the MCP surface ([mcp] extra); TOOL_REFS is DERIVED from _dispatch_funcs
__main__.py  cw.dispatch over tools._dispatch_funcs -- one line, no adapter
data/        tells.yaml, skills/, agents/
```

## Invariants (each one is load-bearing)

- **No percentage, no verdict about a person.** `lean` + `strength` + a coarse label, and every number traceable to a quoted span. The full argument is `misc/docs/why-no-percentage.md`; do not weaken it without reading it.
- **Human-leaning signals are first-class.** A detector that can only accuse is not a measuring instrument. Mechanical artifacts (mid-sentence line breaks, mixed apostrophes, L2 slips) are often the most decisive evidence in a file.
- **An offset always finds the text it claims.** Every `Span` carries offsets *and* quote/prefix/suffix. `tests/test_ground_truth.py::test_every_signal_span_indexes_the_original_text` is the guard. A judgment whose quote is gone is **dropped, never re-anchored by offset** — mis-anchoring attaches a reason to text it was never about.
- **A detector is a function, not a class.** `(text, span) -> Iterator[Signal]`. If yours needs a base class or a registry, it is not a detector yet.
- **Nothing in `tools.py` prints or exits.** The CLI is `cw`; MCP is `py2mcp` string refs to the same functions.
- **A surface never gets its own verb list.** `ductus/mcp.py` *derives* `TOOL_REFS` from `tools._dispatch_funcs`, so there is nothing to keep in sync and no parity test to write — a parity test between two surfaces means there are two implementations. A verb that changes the host declares it at its own definition with `@host_mutating`, and surfaces filter on that property rather than on a second list.
- **The core stays cheap to import.** `torch`/`transformers` live in the `[local]` extra behind deferred imports. `pyyaml` and `cw` are the only hard dependencies.
- **"No findings" is a weak result, not a clean bill**, and the renderers say so.
- **The deterministic layer has high precision and low recall** — 7 signals across the 12 known-mixed fixture documents at sentence granularity (11 at paragraph). `tests/test_ground_truth.py` asserts that floor rather than a flattering number. Do not raise the assertion to make a change look good.
- **Calibrate the instrument, not the verdict.** Fitting may tune how much each *kind* of evidence weighs, or how evidence is normalised — properties of the tool, publishable as a table. It may never produce a per-document estimate of P(machine), however renamed. The operational test: if a reader who knows the procedure can invert the reported output back into a probability, the package is emitting one. `lean` must stay a ratio that reaches ±1.0 on a single weak signal; that jaggedness is the guardrail, not a defect. Full argument: `misc/docs/what-calibration-means-here.md`.
- **This package's own false-positive rate is measured, and it is not small** — 20.6% of 350 human-written documents are called `leans-machine` by the shipped defaults (`misc/docs/phase-2-results.md`). The bias runs toward *formal, fluent* writing, not simple writing, which is the opposite of the direction the literature warns about and is explained by what the deterministic detectors look for. Re-measure with `python misc/measure_false_positives.py` after any change to rules, weights or thresholds.
- **A detector joins `DEFAULT_DETECTORS` by measurement, never by being new.** `DETECTORS` is the registry; `DEFAULT_DETECTORS` is what `detectors=None` means, and they are deliberately not the same list. The gate and its criterion are `misc/measure_detectors.py`; the standing result is `misc/docs/phase-1-results.md`. The model-based pair did not clear it and is off by default.

## Conventions

- Python ≥ 3.10, keyword-only from the 2nd or 3rd position, functional over OOP, dataclasses for data.
- Every module has a docstring with doctests that run (`pytest --doctest-modules ductus`).
- Tests in `tests/`; two vendored ground-truth fixtures — `mixed_authorship.json` (LLMTrace, Apache-2.0, interleaved machine spans) and `roft_boundary.json` (RoFT, MIT, one human prefix then a machine continuation). Neither may be edited to make a test pass. Their shapes differ on purpose: a detector that only works on one of them has a result about the fixture.
- Corpora that cannot be redistributed are **measured, not vendored**: `misc/measure_false_positives.py` downloads W&I+LOCNESS to `~/.local/share/ductus/corpora/` and the numbers are committed instead of the data. Never add a non-redistributable corpus to the repo.
- Conventional Commits, no AI attribution.

## Cross-package

`acquaint.deslop` imports this package's catalogue (`load_rules`, `iter_tell_matches`, `metrics`, `TIER_WEIGHT`) instead of carrying its own, and layers recipient calibration on top. `tests/test_tells_contract.py` pins that contract — breaking it breaks `acquaint`'s linter.
