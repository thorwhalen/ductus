# Roadmap — from v1 to all surfaces

v1 is the core, the CLI and the agent skills. Every remaining piece is an **ADD at a seam that already exists**, and this document is the evidence for that claim: for each one, what changes, and whether the core has to change with it (the answer should always be no).

## The seam table

| # | Seam | v1 default (no new dependency) | Replacement, and where it already exists |
|---|---|---|---|
| 1 | `segmenter=` — how text is cut into scored units | `"paragraph"` (stdlib regex); `"sentence"` and `"document"` also ship | `imbed.fixed_step_chunker`, already in the local manifest |
| 2 | `detectors=` — what produces evidence | four deterministic detectors: `tells`, `forensic`, `rhetoric`, `rhythm` | Fast-DetectGPT and Binoculars (both open, both MIT/BSD, `[local]` extra); Sapling and Pangram APIs (`[api]` extra) — see `research/detection-methods.md` |
| 3 | `aggregate=` — evidence → lean, strength, label | `ductus.score.aggregate`, a transparent weighted sum | a scorer calibrated on the LLMTrace/RoFT fixtures — see `research/datasets-and-fixtures.md` |

**NOT seams**, written directly on purpose: the report templates, argument parsing, the `Span`/`Signal`/`Segment`/`Report` dataclasses, the colour ramp, the tier→weight mapping.

`extra_signals=` is an *input*, not a seam: evidence produced anywhere — by an agent reading the text, by a vendor API — anchored by quote and folded in beside the deterministic signals. The shipped skills are its first caller.

## What is built

- **Core** — `gauge()` / `iter_segments()`, the four detectors, the three renderers.
- **CLI** — `cw` over `ductus.tools._dispatch_funcs`. The one-command test is `ductus gauge <file>`, asserted in `tests/test_smoke.py`.
- **Agent skills** — `ductus`, `ductus-gauge`, and the `ductus-reader` subagent, shipped in `ductus/data/skills/` and installed with `ductus install-skills --write`.

## Surface questions, answered in v1

The question asked of each surface is only *"would this surface need the core to change?"* — not *"how would we build it"*.

| Surface | Would the core change? | Why not |
|---|---|---|
| **CLI** | built | — |
| **MCP** | no | `ductus.tools` functions take and return JSON-ready values and never print or exit. `py2mcp.mk_mcp_from_refs(['ductus.tools:gauge', 'ductus.tools:tells'])` uses **string refs**, so the core never imports MCP. |
| **Agent skills** | built | — |
| **HTTP** | no | `qh.mk_app(_dispatch_funcs)` over the same callables. No module-level mutable state exists; every verb is a pure function of its arguments. |
| **Frontend** | no | the report already round-trips as JSON (`--format json`), and `Span` already carries the redundant selectors a client needs to re-anchor highlights after an edit. |

If any of these turns out to need a core change, **the core was coupled to its first surface and the core is what gets fixed** — the adapter is not the place to paper over it.

## Tentative plan

### Phase 1 — model-based detectors (`[local]`) — **done, gate not cleared**

Built and shipped, **off by default**. The full measurement is in [`phase-1-results.md`](phase-1-results.md); the design decision it rests on is in [`curvature-as-evidence.md`](curvature-as-evidence.md).

- `ductus/curvature.py` holds `fast_detect_gpt(text, span, *, model=...)` and `binoculars(text, span, *, observer=..., performer=...)` — one function each of the existing `(text, span) -> Iterator[Signal]` shape, registered in `DETECTORS` so they can be named. (A flat module rather than the `ductus/detectors/` package sketched here, to match the shape the rest of the package already has.)
- Deferred imports: `import ductus` still loads no `torch`, and `tests/test_curvature.py` asserts it in a subprocess.
- Defaults are `gpt2` and the `distilgpt2`/`gpt2` pair, CPU-sized; `EleutherAI/gpt-neo-2.7B` and the Falcon-7B pair are the documented upgrade.
- **Gate: not cleared.** Machine-side recall moved from 1/40 to 3/40 decisive segments, but precision fell from 1/1 to 3/8, so the criterion — more recall *without* worse precision — failed. `DEFAULT_DETECTORS` is unchanged and is deliberately a different list from `DETECTORS`.
- The result worth carrying forward: the model detectors found **10 human-leaning segments where the deterministic set found 0, all 10 correct**. Human-leaning evidence is first-class here, so this is why they ship rather than being deleted.
- Re-running the gate after any change is `python misc/measure_detectors.py`.

### Phase 2 — calibration, and the fixture corpus — **done**

Results: [`phase-2-results.md`](phase-2-results.md). The decision that had to come first: [`what-calibration-means-here.md`](what-calibration-means-here.md).

- **Done** — `tests/fixtures/roft_boundary.json`, a RoFT slice (MIT): 18 documents, one human prefix then a machine continuation, two at each of the nine boundary positions. The different ground-truth shape earned its keep immediately — the model-based detectors clear the Phase 1 gate on it outright, having failed on LLMTrace's `fill_gaps` documents.
- **Done, partially** — the proxy-model ladder spans 124M to 1.5B (`misc/measure_model_ladder.py`). Falcon-7B is out of reach on CPU and is documented as such rather than skipped silently.
- **Done, and it is the headline** — false-positive rate on 350 human-written texts by CEFR band against a native control, from W&I+LOCNESS. Measured, not vendored: the corpus is non-redistributable, so the script downloads it and the numbers are committed. **20.6% of human documents are falsely accused by the shipped defaults**, down from 34.3%.
- **Done, and not what was expected** — most of the old rate was a *length* artefact, not a language one. `aggregate=` gained `n_chars` (the seam could not previously express a rate) and `density_aggregate` is the new default.
- **Not done, and deliberately** — per-detector weights were not fitted. Seven deterministic signals across twelve documents is not an evidence base, and fitting on it would have produced the shape of a result with none of the content.
- **The roadmap's own reassurance about calibration was wrong**, and is corrected in `what-calibration-means-here.md`: "a fitted scorer changes what `lean` is computed from, not what is reported" does *not* hold for the obvious implementation, because `lean = 2p − 1` is invertible. The rule that survives is *calibrate the instrument, not the verdict*, with a sufficiency test to tell them apart. **Still no percentage.**

### Phase 3 — MCP — **done**

- **Done** — `ductus/mcp.py`, `mk_mcp()` over `py2mcp.mk_mcp_from_refs`. The core did not change, as predicted.
- **Done, and better than "never author a second verb list"** — `TOOL_REFS` is *derived* from `tools._dispatch_funcs`, so there is no second list and therefore nothing for a parity test to catch. A verb that mutates the host says so at its own definition (`@host_mutating`) and surfaces filter on that property; `install_skills` is consequently not reachable over MCP, while a CLI user who types it chose to.
- **Done** — `middleware=` and `auth=` pass straight through, which is where a deployed connector attaches metering and authentication without the core learning either exists.
- **One thing the surface found.** Under `from __future__ import annotations` — used by every module here — the schema layer beneath `fastmcp` reads annotations as strings and drops **every keyword-only default**, so `gauge(source=...)` failed with five "missing required argument" errors. Since this package's convention is keyword-only from the second or third argument, that would have made every verb uncallable. `ductus.mcp._resolve_annotations` resolves them eagerly before the server is built. The defect is upstream, not in the core, so the core stayed as it was — but it is the first time a surface has told us anything, and it is the reason the surface is tested by *calling* it through a real client rather than by inspecting its schema.

### Phase 4 — HTTP

- `ductus/http.py`: `qh.mk_app(_dispatch_funcs)`, plus `qh.export_ts_client` for the frontend's typed client.
- Only worth building once there is a remote consumer. Note that remote MCP *is* HTTP — if the only remote consumer is an agent, Phase 3 may already be the whole job.

### Phase 5 — the frontend

The most expensive surface by an order of magnitude, and the one with the least settled design. The research is in `research/annotation-editing-ux.md`; the decisions it points to:

- **Policy: invalidate, never silently re-anchor.** The instant the text changes, affected spans are dimmed as unverified. Re-attaching an old *score* to new text is misleading, because that score was never computed for the text it now points at.
- **Technique: ProseMirror `Mapping` + `DecorationSet.map`** to keep *positions* exact while typing. Spans live in a side-car decoration set, never in the document schema. No CRDT stack — this is read-mostly, single-user editing.
- **Re-score** recomputes against the current text, so at that instant there is no anchoring problem at all; the redundant selectors are needed only at persistence and reload boundaries, where a diff-match-patch fuzzy match re-anchors and failures become an orphan list rather than a guess.
- **Rendering: two channels.** Hue encodes score only, on a perceptually-uniform ramp with lightness re-clamped per theme; overlap is shown structurally in a separate lane. Loading both meanings into one colour is what makes overlapping highlights unreadable. The shipped HTML report already implements this and is the reference.

### Not planned

- **Watermark detection** (SynthID, Kirchenbauer). It only works when you control or trust the generator's key, which is a different deployment model from everything here. It belongs as an explicitly-labelled verification mode if at all, never on the default path.
- **Anything that helps evade detection.** The read side describes text; the write side (`acquaint`'s `deslop`) exists to make writing *good*, not to launder it.

## Cross-package

`acquaint.deslop` reads this package's tells catalogue rather than carrying its own. The contract it depends on is pinned by `tests/test_tells_contract.py`: `load_rules()`, `iter_tell_matches()`, `metrics()`, `TIER_WEIGHT`. Recipient calibration — which tiers are enforced for which reader, and that reader's blocklist — stays in `acquaint`, because it needs a model of the reader that `ductus` deliberately does not have.
