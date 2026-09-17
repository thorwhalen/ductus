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

### Phase 1 — model-based detectors (`[local]`)

The single biggest accuracy upgrade available, and it needs no API key.

- Add `ductus/detectors/curvature.py` with `fast_detect_gpt(text, span, *, model=...)` and `binoculars(text, span, *, observer=..., performer=...)`. Both are one function of the existing `(text, span) -> Iterator[Signal]` shape.
- Deferred imports; `torch`/`transformers` stay in the `[local]` extra and `import ductus` stays cheap.
- Default proxy model small enough to run on CPU (GPT-Neo-125M class), with the Falcon-7B pair as the documented upgrade.
- **Gate**: the `[local]` detectors must measurably beat the deterministic ones on `tests/fixtures/mixed_authorship.json` before they become part of any default. Recall is the weakness they exist to fix — the deterministic layer currently fires 8 times across 12 known-mixed documents.

### Phase 2 — calibration, and the fixture corpus

- Vendor a second fixture set from RoFT (MIT, human prefix + machine continuation, an explicit `true_boundary_index`) alongside the LLMTrace slice already in `tests/fixtures/`. Different ground-truth shape — a single boundary rather than multiple spans — which is exactly why it is worth having both.
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
