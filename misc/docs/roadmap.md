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

### Phase 2 — calibration, and the fixture corpus

- Vendor a second fixture set from RoFT (MIT, human prefix + machine continuation, an explicit `true_boundary_index`) alongside the LLMTrace slice already in `tests/fixtures/`. Different ground-truth shape — a single boundary rather than multiple spans — which is exactly why it is worth having both.
- Retest the Phase 1 detectors at the documented upgrade models before anything else — the cheapest untried thing, and the fixture's `fill_gaps` shape is close to their worst case.
- Fit `aggregate=` on them and report the honest operating characteristics: false-positive rate on the human-only subset first, and separately on non-native-English text if a suitable corpus can be licensed.
- **Even after calibration, no percentage.** A fitted scorer changes what `lean` is computed from; it does not change what is reported. See `why-no-percentage.md`.

### Phase 3 — MCP

- `ductus/mcp.py`: `mk_mcp_from_refs(['ductus.tools:gauge', 'ductus.tools:tells', 'ductus.tools:detectors'])`.
- Never author a second verb list. One registry, many emitters — a parity test between two surfaces means there are two implementations.
- The MCP surface is where the deployed-connector story starts: a hosted server whose LLM work runs on the caller's own subscription, with `middleware=` as the auth and metering seam.

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
