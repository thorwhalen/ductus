# ductus — dev notes for the agent working on this repo

`ductus` gauges which parts of a text read as machine-written, and says why, with every finding anchored to exact characters. The *ductus* is the palaeographer's term for the stroke-manner that identifies a scribe's hand.

## Seams, defaults, surfaces (read this before adding anything)

| Seam | Current default | Built surfaces |
|---|---|---|
| `segmenter=` | `"paragraph"` (also `"sentence"`, `"document"`, or any callable) | **CLI** (`cw` over `tools._dispatch_funcs`), **agent skills** (`ductus/data/skills/`) |
| `detectors=` | `tells`, `forensic`, `rhetoric`, `rhythm` — all deterministic, zero extra deps. `fast-detect-gpt` and `binoculars` ship in the `[local]` extra: registered, **opt-in**, off by default — see `misc/docs/phase-1-results.md` | MCP / HTTP / frontend: **questions answered, not built** — see `misc/docs/roadmap.md` |
| `aggregate=` | `score.aggregate`, a transparent weighted sum | |

**NOT seams**, on purpose: report templates, arg parsing, the four dataclasses, the colour ramp, the tier→weight map.

## Shape

```
base.py      Span / Signal / Segment / Report -- the contract every module speaks
segment.py   segmenters (the `segmenter=` seam); pure generators over exact offsets
tells.py     the catalogue: load_rules, iter_tell_matches, metrics  <- acquaint imports these
detect.py    the four deterministic detectors (the `detectors=` seam) + the registry
curvature.py Fast-DetectGPT and Binoculars ([local] extra, deferred torch import)
score.py     aggregate(): evidence -> (lean, strength, label). No percentage. Ever.
core.py      iter_segments() streams, gauge() batches over it
render.py    to_json / to_markdown / to_html (self-contained, no CDN, two-channel highlighting)
tools.py     the verb SSOT: JSON in, JSON out, never prints or exits
__main__.py  cw.dispatch over tools._dispatch_funcs -- one line, no adapter
data/        tells.yaml, skills/, agents/
```

## Invariants (each one is load-bearing)

- **No percentage, no verdict about a person.** `lean` + `strength` + a coarse label, and every number traceable to a quoted span. The full argument is `misc/docs/why-no-percentage.md`; do not weaken it without reading it.
- **Human-leaning signals are first-class.** A detector that can only accuse is not a measuring instrument. Mechanical artifacts (mid-sentence line breaks, mixed apostrophes, L2 slips) are often the most decisive evidence in a file.
- **An offset always finds the text it claims.** Every `Span` carries offsets *and* quote/prefix/suffix. `tests/test_ground_truth.py::test_every_signal_span_indexes_the_original_text` is the guard. A judgment whose quote is gone is **dropped, never re-anchored by offset** — mis-anchoring attaches a reason to text it was never about.
- **A detector is a function, not a class.** `(text, span) -> Iterator[Signal]`. If yours needs a base class or a registry, it is not a detector yet.
- **Nothing in `tools.py` prints or exits.** The CLI is `cw`; MCP would be `py2mcp` string refs to the same functions.
- **The core stays cheap to import.** `torch`/`transformers` live in the `[local]` extra behind deferred imports. `pyyaml` and `cw` are the only hard dependencies.
- **"No findings" is a weak result, not a clean bill**, and the renderers say so.
- **The deterministic layer has high precision and low recall** — 7 signals across the 12 known-mixed fixture documents at sentence granularity (11 at paragraph). `tests/test_ground_truth.py` asserts that floor rather than a flattering number. Do not raise the assertion to make a change look good.
- **A detector joins `DEFAULT_DETECTORS` by measurement, never by being new.** `DETECTORS` is the registry; `DEFAULT_DETECTORS` is what `detectors=None` means, and they are deliberately not the same list. The gate and its criterion are `misc/measure_detectors.py`; the standing result is `misc/docs/phase-1-results.md`. The model-based pair did not clear it and is off by default.

## Conventions

- Python ≥ 3.10, keyword-only from the 2nd or 3rd position, functional over OOP, dataclasses for data.
- Every module has a docstring with doctests that run (`pytest --doctest-modules ductus`).
- Tests in `tests/`; the ground-truth fixture is a vendored LLMTrace slice (Apache-2.0) and must not be edited to make a test pass.
- Conventional Commits, no AI attribution.

## Cross-package

`acquaint.deslop` imports this package's catalogue (`load_rules`, `iter_tell_matches`, `metrics`, `TIER_WEIGHT`) instead of carrying its own, and layers recipient calibration on top. `tests/test_tells_contract.py` pins that contract — breaking it breaks `acquaint`'s linter.
