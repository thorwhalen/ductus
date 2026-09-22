# The example frontend: score a text, edit it, score it again

A single-page app over the `ductus` HTTP surface. Paste a text, read it, edit it, read it again — with every finding anchored to the exact characters that carry it, and with a finding that no longer describes the text saying so rather than quietly pretending otherwise.

This is an *example of consuming the package*, shipped beside it. It is not a product, and the decisions that follow from that — no framework, no persistence, no state library — are written down in [`../misc/docs/frontend-stack-decision.md`](../misc/docs/frontend-stack-decision.md) with their costs named.

## Running it

```bash
pip install 'ductus[http]'
ductus-http                       # the API on http://127.0.0.1:8000
```

```bash
cd frontend
npm install
npm run dev                       # the UI on http://127.0.0.1:5173, proxying to the API
```

Or build it once and let the Python server serve both from one origin:

```bash
npm run build                     # writes frontend/dist/
ductus-http                       # now serves the UI at / as well as the API
```

That last one works **from a git checkout**, where `frontend/dist` sits beside the package. The frontend is deliberately not carried in the wheel — committing a minified bundle into a Python package to make one demo self-installing is a trade this package has not made — so a pip-installed `ductus` serves the API and no UI unless you point it at one:

```bash
DUCTUS_UI_DIR=/path/to/dist ductus-http
```

```bash
npm test                          # the invalidation policy, in vitest
npm run typecheck                 # tsc --noEmit
```

## What is where

| File | What it is |
|---|---|
| `src/editor.ts` | ProseMirror. The schema that preserves every character, and the position mapping that keeps findings attached while you type. |
| `src/state.ts` | The one store, and **the invalidation policy** — the correctness rule of the whole app. |
| `src/decorations.ts` | Findings → highlights, on two channels: hue for score, a separate lane for overlap. |
| `src/panels.ts` | The verdict, the findings list, and the limits. Where the honesty requirement is met or quietly dropped. |
| `src/main.ts` | The wiring. Read it top to bottom and you have the app. |
| `src/generated/` | **Generated from Python. Do not edit.** |

## Three things worth knowing before changing anything

**1. The editor must not tidy the text.** A normal rich-text editor turns `'` into `’`, trims trailing spaces and collapses lone newlines. `ductus` reads all three as evidence — `mixed-apostrophes` and `trailing-whitespace` are *human*-leaning signals, among the strongest the package has. A tidying editor would silently delete the evidence that exonerates people. Hence the whitespace-preserving one-block schema, which also makes a plain offset `o` exactly ProseMirror position `o + 1`.

**2. An edit never re-scores and never re-anchors a score.** Positions are kept exact (ProseMirror's `Mapping`); *validity* is not inherited. A finding whose text has changed goes hatched and says "unverified" until you read again. Re-attaching an old score to new text is not a stale cache, it is a false claim — that number was never computed for the characters it now points at.

What counts as affected is two-level, and the second half is easy to miss: a finding is invalidated when the edit touched *its own characters* **or anywhere in its segment**, because the segment's lean and strength come from `density_aggregate`, which divides evidence by how much text produced it. Adding a sentence to a paragraph changes what every finding in that paragraph is worth without touching any of them. The document verdict is invalidated by any edit at all.

**3. `src/generated/` is generated from the Python.** `client.ts` comes from the service's own OpenAPI, `report.ts` from the dataclasses in `ductus/base.py`. After changing a verb signature or a dataclass:

```bash
python misc/generate_frontend_sources.py
```

`tests/test_generated_sources.py` fails if what is committed disagrees with what the Python now produces — so a renamed field is a failing `pytest` run, not an `undefined` someone finds in a browser three weeks later.

## Not built

Persistence and reload (and therefore the fuzzy re-anchoring and orphan list that go with it), file upload, and a compare-with-last-scored view. The reasons, and which of them are deliberate rather than merely unfinished, are in the decision doc.
