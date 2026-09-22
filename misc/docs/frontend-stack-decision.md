# What the frontend is built with, where it lives, and what that costs

Written before the frontend, in the same spirit as [`curvature-as-evidence.md`](curvature-as-evidence.md) and [`document-verdict-decision.md`](document-verdict-decision.md): decide in the open, then measure against the decision rather than rationalising whatever got built.

The *interaction* design was settled earlier, by [`research/annotation-editing-ux.md`](research/annotation-editing-ux.md), and is not reopened here. This document answers the two questions that research left: **which stack**, and **which repository**.

## The short version

An example frontend for a Python package, in `frontend/` in this repository, built with Vite + TypeScript + ProseMirror and no framework. It is deliberately *not* built on the house app stack (Zod-schema SSOT, generated UI, zustand/immer, a zodal store, acture commands). The reasons are below, one invariant at a time, because departing from them is a decision and not a detail.

## Where it lives: this repo, not `tt/`

The rule is that frontend work goes in a `tt/` repository. That rule is about **repositories**, and the question here is what kind of thing this is.

This is an example of consuming `ductus`, shipped beside `ductus`, whose whole purpose is to demonstrate the HTTP surface that `ductus` emits. It is `misc/demo/` with a build step. The argument for `tt/` is that it is JavaScript; the argument against is everything else:

- **The typed client is generated from this package's own OpenAPI.** Splitting the repositories puts a network and a release cadence between a Python signature and the TypeScript that calls it. In one repository, a changed signature is a failing test in the same `pytest` run — and it is, see below. Across two, it is a bug someone finds later.
- **The version skew becomes real.** `ductus` 0.1 and `ductus-ui` 0.4 are two things a user has to match up. One repository has one version.
- **Same-origin comes free.** `mk_app(ui=...)` serves the built assets from the same process as the API, so there is no CORS configuration, no second port in development, and a browser test can drive the whole thing by starting one server.

**The cost, named.** If this ever becomes a product rather than an example — accounts, saved documents, history, a deploy — it wants its own repository, its own release cadence and the house stack, and moving it then is a migration. The trigger to watch for is the first feature that is about *the app* rather than about *demonstrating the package*.

## The stack, against each house invariant

### 1. "A Zod schema is the single source of truth" — honoured in substance, not in letter

The source of truth for this system is `ductus.tools._dispatch_funcs` and the dataclasses in `ductus/base.py`. It is in Python, and it already has three emitters (CLI, MCP, HTTP). Writing a Zod schema for `Report` would create a **second** source of truth, in a second language, hand-maintained, free to drift from the dataclasses it mirrors. That is exactly the failure the "one registry, many emitters" design exists to prevent, and adding it here to satisfy the letter of the invariant would violate its purpose.

So the invariant is kept by moving the generation boundary rather than by abandoning it:

- `ductus.http.export_client()` generates the TypeScript client from the app's own OpenAPI.
- `ductus.http.export_types()` generates TypeScript interfaces for `Report`, `Segment`, `Signal` and `Span` **from the dataclasses themselves**, by introspection.
- Both outputs are committed under `frontend/src/generated/`, so `npm install && npm run dev` works without a Python toolchain.
- `tests/test_generated_client.py` regenerates them and asserts the committed files match. **A changed Python signature or dataclass field is a failing Python test**, not a runtime surprise in a browser.

If this frontend ever grows a form, a table or a filter — the things schema-generated UI is actually for — a Zod schema derived from the same generated types becomes the right next step, and it is an addition at the boundary that already exists.

### 2. "The UI is generated from the schema" — not applicable

There is no form and no table. There is a text editor with decorations, a verdict panel and a list of findings. Schema-generated UI has nothing to generate here; `zodal`'s generators (`toColumnDefs`, `toFormConfig`, `toFilterConfig`) have no input.

### 3. "State is zustand, mutated through immer" — one store, hand-written

There is one screen and one state object of eight fields. `zustand` earns its place by sharing state across a component tree and by keeping derived values as selectors rather than duplicated state. The second half of that is the part that matters, and it is honoured: `state.ts` holds one immutable object, every derived value is computed at render time, and nothing is stored twice.

What is skipped is the library, for a store that one person reads in thirty seconds. **The cost:** a second screen, or state shared between two independently-mounted trees, is the point at which this becomes worse than zustand rather than simpler, and the conversion is mechanical.

### 4. "Storage goes behind a store interface" — there is no storage

Nothing is persisted. Not a draft, not the last-scored text, not a preference. Two reasons, and the second is the real one:

- The research's re-anchoring work — fuzzy matching a saved `(quote, prefix, suffix)` back onto changed text, and demoting the failures to an orphan list — is needed **only at persistence and reload**. Not persisting is what keeps that out of a first version honestly, rather than half-building it.
- **Quietly keeping someone's writing in their browser is a decision about their privacy that a tool like this should not make for them.** People paste things into an AI-detector that they would not paste anywhere else. Starting empty on every load is the behaviour that needs no explanation.

If persistence is added, invariant 4 applies in full and a `DataProvider` is the way in — and the orphan list becomes a real piece of UI, not a footnote.

### 5. "Commands are declared once" — correctly premature

The invariant says to reach for `acture` "when a *second* surface appears, not before". There is one surface with three actions (score, edit, re-score). Skipping it is the invariant, not a departure from it.

### 6. "Progressive disclosure" — kept

Paste and press one button. Everything else — the segmenter, the detector subset — is not in the first screen at all.

## No React

The router's table says a per-user-mutable-state app is "Vite + React + TS". This one is not, for three reasons:

1. **ProseMirror owns its DOM, and so does React.** Putting them together needs a bridge, and that bridge is a well-known source of subtle bugs in exactly the area this app cannot afford them: position tracking during editing.
2. **There is almost no chrome.** The non-editor UI is a header, a verdict panel, a findings list and a limits panel — a handful of functions that build DOM.
3. **The reader is learning.** Plain TypeScript that appends elements to a parent is readable top to bottom. React asks a novice to hold reconciliation, hooks and effect ordering in their head before they can follow what happens when a button is pressed — and `useEffect` races are precisely the failure `tw-frontend-ux`'s first principle is about.

**The cost, named.** Routes, several screens, or shared stateful components are the point where hand-rolled DOM stops being simpler and starts being a worse React. The ProseMirror layer would survive that rewrite; the chrome would not.

## The editor must not normalise the text — this one is not a preference

The obvious way to build this is a rich-text editor over paragraphs. **It would destroy the evidence.**

`ductus`'s `forensic` detector reads, among others:

| Signal | Direction | What a normalising editor does to it |
|---|---|---|
| `mid-sentence-newline` | machine-leaning when absent, decisive when present | Paragraph normalisation deletes single newlines outright |
| `mixed-apostrophes` | **human**, weight 0.35 | Smart-quote substitution converts `'` to `’` and the mixture disappears |
| `trailing-whitespace` | **human**, weight 0.25 | Every editor trims it |

Two of those three are among the strongest *human*-leaning signals the package has, and `CLAUDE.md` names mechanical artifacts as "often the most decisive evidence in a file". An editor that silently tidies the text would systematically delete the evidence that exonerates people, and would do it invisibly — the user would see their text, unchanged to the eye, score worse.

So the ProseMirror schema is one whitespace-preserving block node holding text, with `Enter` inserting a literal newline. This also buys an exact, trivial offset bijection: a plain-text offset `o` is ProseMirror position `o + 1`, with no node-boundary arithmetic and no place for an off-by-one to hide. `tests/` and the editor's own assertions pin it.

**The cost, named.** No bold, no headings, no lists — and paragraph breaks are literal blank lines. For a tool whose every finding is anchored to exact characters, showing exactly those characters is the right trade, but it does mean this is a text editor and not a document editor.

## The colour ramp is duplicated, knowingly

`ductus/render.py` defines the two-channel palette — hue encodes score and only score, overlap goes to a separate structural lane — as OKLCH stops inside a Python string. The frontend needs the same stops so that the shipped HTML report and the UI do not disagree about what orange means.

Factoring this out would mean either parsing CSS out of a Python string literal or generating the stylesheet from Python. Both cost more than they save for six colour values. So `frontend/src/palette.css` restates them, with a comment naming `ductus/render.py` as the origin. **This is a real, if small, second source of truth**, and if the ramp is ever tuned, both files need the change. Recorded here so that is a known cost and not a discovery.

## What is deliberately not built

- **Persistence, reload and fuzzy re-anchoring.** See invariant 4. The redundant selectors are already on every `Span` and are what this would be built from; the orphan list is the part with real design in it.
- **PDF upload.** Text files (`.txt`, `.md`) open since 2026-09, read in the browser and sent nowhere until "Read" (`frontend/src/upload.ts`). The rule that makes that safe: an opened file yields exactly the text `ductus gauge <file>` would read — invalid UTF-8 refused rather than replaced with `�`, `\r\n`/`\r` folded to `\n` as Python's text mode does, a BOM kept. PDF is refused with a reason: extracted text carries the extractor's line breaks and hyphenation, which `ductus` would score as the writer's — a different problem wearing the same button.
- **A compare view** ("last-scored vs current"). The research offers it as an optional secondary view. Invalidation is the correctness requirement; the diff is a convenience.

## The interface must not make the verdict feel more certain than it is

This is the part a UI gets wrong, so it is written down as a constraint and not left to taste.

The measured facts it has to hold: **6.0% of 350 human-written documents are called `leans-machine` by the shipped defaults**, every one of those is wrong, and the bias runs toward *formal, fluent* prose — in the measured corpus the native-speaker control was the most-accused group. A careful essayist is the likeliest person to be wronged by this page.

A text report can put that in a footer. An interface cannot, because an interface makes a verdict feel authoritative in a way a paragraph does not: the colour arrives before the caveat, and the caveat is below the fold.

So:

1. **The false-positive rate sits beside the verdict, not in a footer** — and it is stated most loudly in the one case where it is a claim about a person: when the label is `leans-machine`.
2. **Natural frequency, not a percentage.** "About one in sixteen" rather than "6.0%", both because the no-percentage rule is load-bearing next to a verdict and because frequencies are read more accurately than rates.
3. **Evidence first.** The findings list — quote, reason, weight, direction — is the main column. The verdict is small. A reader should be pulled toward *what it found* rather than toward *what colour it is*.
4. **The bias direction is stated in the interface**, not only in the README, because the person most likely to be misled by this page is the one whose careful prose it just lit up.
5. **"No findings" says it is a weak result, not a clean bill** — in the empty state, where a reader will otherwise read absence as innocence.
6. **Human-leaning findings are rendered as first-class**, with the same prominence as machine-leaning ones. A tool that shows accusations in colour and exonerations in grey is an accusation machine whatever its documentation says.
7. **No percentage anywhere**, and nothing from which one can be reconstructed.
