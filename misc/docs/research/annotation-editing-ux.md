# Editing text with overlapping span annotations: anchoring, editor tech, interaction patterns, and heat-highlight color

## (A) What the local survey already covers — don't repeat

a local annotation-systems survey already establishes: standoff annotation as the architectural default (annotations separate from source, reunited by reference — brat, ELAN, W3C Web Annotation, Praat); the W3C Web Annotation Data Model's selector vocabulary (TextQuoteSelector, TextPositionSelector, RangeSelector, refinement chains); the interval-tree as the core data structure for overlap queries (O(log n + k), Python `intervaltree`); the naming of "offset invalidation" as *the* standoff weak point, with a one-line mention of W3C's multi-selector fallback and STAM's validation extensions as answers; a brief, honest flag that CRDT relative positions (Yjs, Automerge) exist but that "representing concurrent interval boundary modifications... requires custom CRDT semantics beyond what standard libraries provide." It does not name the anchoring-failure literature, does not give the actual re-anchoring algorithms, does not cover editor-internal position-mapping (ProseMirror/CodeMirror/Slate/Lexical), says nothing about interaction-design patterns for edit-vs-annotation, and says nothing about overlap-rendering technique or color/accessibility for a continuous score. That's the gap this report fills.

## (B) The anchoring problem: names and algorithms

**Names in the literature.** The problem has no single canonical name but converges on a handful: **annotation anchoring** / **re-anchoring** / **reattachment** (Hypothes.is's own vocabulary [2]), **robust anchoring** or **robust locations** (the older hypertext-literature term, from Phelps & Wilensky's "robust hyperlinks" work [5]), **anchor drift** (informal, used when structural anchors like XPath silently point at the wrong node after a DOM change), and **orphaned / orphan annotations** — Hypothes.is's term for an annotation that fails every reattachment strategy and is demoted out of the document into a separate list rather than deleted or mis-attached [2].

**Hypothes.is fuzzy anchoring** [2] is the most fully documented implementation and the de facto reference algorithm. It stores three selectors per annotation — a legacy `RangeSelector` (XPath + offsets, inherited from Annotator.js v1 [6]), a `TextPositionSelector` (global character offsets), and a `TextQuoteSelector` (exact quoted text plus ~32-character prefix/suffix context) — and reattaches in a strict fallback order: (1) try the XPath range directly, verify the text still matches — fast, but fails on any structural change; (2) try the position selector, verify text match — survives structural change but not content shift; (3) *fuzzy* context-first match — approximate-search for the saved prefix near the expected offset, then the suffix, then check the text between them against a similarity threshold; (4) last-ditch fuzzy full-text search for the exact quote anywhere in the document. The fuzzy matching itself is built on a modified `google-diff-match-patch` [11], which combines the **Bitap algorithm** (approximate string search within an edit-distance bound) with **Myers' diff algorithm** for verification/scoring. This is genuinely expensive for short, generic quotes in long documents — tracked as a real performance bug in the client [issue #3919, referenced in 2]. Annotations that clear no threshold become orphans, shown separately rather than silently mis-anchored or dropped.

**W3C Web Annotation's own answer** [1] is not an algorithm but a data-model policy: selectors are non-exclusive and combinable (`refinedBy` chains, or arrays of selectors on one target), and the *recommended implementer practice*, confirmed independently by at least one modern reimplementation [7], is to persist all of TextQuoteSelector + TextPositionSelector at write time, then at read time prefer the quote (survives reflow and content that moves elsewhere in the document) while using position purely as a disambiguating hint when the same quote occurs more than once — i.e. structurally the same layered strategy Hypothes.is uses, just without a mandated algorithm.

**Phelps & Wilensky's "robust locations"** [5] predate all of this (hypertext literature, ~2000): the core idea — often summarized as "robust hyperlinks cost just five words each" — is to characterize a target by a small set of distinctive surrounding keywords and relocate it in a changed document by searching for the best-matching keyword window. This is conceptually the direct ancestor of TextQuoteSelector's prefix/suffix context.

**Annotator.js v1** [6] is worth naming as the cautionary "before" state: XPath-range-only anchoring, no quote fallback — this is literally why the Hypothes.is team (a fork of Annotator) built fuzzy anchoring in the first place. Notably, even in 2026, not every modern successor has closed this gap: `recogito/text-annotator-js` [12], a current, actively maintained, W3C-aligned, framework-agnostic library in exactly this problem space, documents only a plain character-offset `TextQuoteSelector` with no built-in automatic re-anchoring on edit — you're expected to build that layer yourself.

**Structural (non-offset) anchoring — Google Docs.** Rather than offsets or quotes, Google Docs comments attach to a stable internal per-paragraph "document element" id [8, 9]; edits inside that element leave the comment attached regardless of character drift, but if the element itself is deleted/merged the anchor is lost outright ("Original content deleted" [9]). This trades precision (the comment may no longer point at the exact original substring) for robustness against ordinary in-place editing — a genuinely different strategy from quote/offset matching, closer to "anchor to a container, not a span."

**Coordinate anchoring — PDF/Adobe.** PDF text-markup annotations anchor via **quadpoints** — fixed quadrilaterals in PDF user-space, converted to viewport pixels for rendering [10]. Because PDF layout is fixed rather than reflowable the way HTML is, there is no quote-based fallback in the base format at all; Adobe explicitly disables interactive annotations during "reflow" mode because coordinate anchors don't survive it. This is the degenerate case at the opposite end from Hypothes.is: zero tolerance for content movement.

## (C) Editor-side technical answer

**The four shapes, compared:**

- **ProseMirror `Mapping`/`StepMap` + `Decoration`** [13, 14]: every edit is a `Step`; each `Step` carries a `StepMap` (an array of `[start, oldSize, newSize]` triples); a `Mapping` composes many `StepMap`s so any position — including externally tracked span boundaries — can be pushed through `mapping.map(pos, bias)` and come out exactly correct on the other side. This is **exact, synchronous, deterministic** position tracking, no fuzzy matching, as long as you own the transaction stream. `DecorationSet.map(tr.mapping, tr.doc)` is the built-in primitive for exactly this: spans live in a side-car decoration set, never touch the document schema, and are cheaply remapped (O(number of spans), not O(document)) on every keystroke.
- **Yjs `RelativePosition`** [15]: converts an absolute index into an ID-based reference tied to a specific character's CRDT item, stable under *concurrent* inserts/deletes anywhere in the document — the right tool when multiple users can edit simultaneously and offline. Heavier: requires adopting Yjs's document model end to end (e.g. via `y-prosemirror`).
- **Automerge cursors** [16]: same idea in the Automerge CRDT — a cursor created at an index auto-adjusts as edits land before it, serializable for persistence across sessions. Same trade-off as Yjs: overkill unless you're already using Automerge for sync/versioning.
- **CodeMirror 6 `RangeSet.map(ChangeDesc)`** [17, 18]: structurally identical idea to ProseMirror's StepMap — a `RangeSet` of decorations is mapped through a document's `ChangeDesc` in O(changes). CodeMirror is optimized for code/monospace editing; for prose, ProseMirror or a plain contenteditable is the more natural fit even though the mapping primitive is philosophically the same.
- **Lexical `NodeKey`** [21] and **Slate `Path`/`Point`** [19, 20]: Lexical gives every node a stable identity key at creation, so a wrapping "mark" node keeps its association by node identity rather than offset — but this only helps if your span boundaries can be lifted to real node boundaries, which gets awkward once spans are defined by a scoring model at arbitrary character offsets that don't align to word/node boundaries, especially under overlap. Slate explicitly **removed marks/annotations from its core** [20]: "annotations have been removed from Slate's core and can be fully implemented in userland by defining custom operations and rendering annotated ranges using decorations" — Slate gives you the Point-transform primitive (same shape as ProseMirror's Mapping) but no annotation-tracking layer; you build it yourself, same as with `text-annotator-js`.

**Recommendation.** ProseMirror's Mapping/Decoration pair is the right shape for a *read-mostly, occasionally edited* annotated-text viewer: it needs no CRDT stack (single-user, not live-collaborative), it keeps annotations entirely outside the document schema (satisfying the local survey's own pitfall #1 — "mixing annotations with source data"), and it solves position tracking exactly for the one case that actually recurs constantly (every keystroke inside an active edit session), leaving only two narrow boundaries where the *harder*, fuzzy Hypothes.is-style algorithm is still needed: (1) persistence/reload across sessions, where you no longer have the Step log to replay, and (2) any edit that bypasses the tracked editor (external paste of a whole new version, undo-history cleared). For those two boundaries, persist each span as `(quote, prefix, suffix, start_offset, end_offset, score)` — the W3C-style redundant selector set [1] — and re-anchor with a small bitap/diff-match-patch fuzzy match [11] on load, demoting failures to an orphan list rather than guessing.

**Minimal concrete design:**
1. Spans live in a side-car array `{from, to, score, id}` per re-score run, never in the document.
2. Show mode: text rendered read-only (ProseMirror `editable: false`, or a plain div); spans → `Decoration.inline` with background/underline styles keyed off `score`.
3. Edit mode: switch to a live ProseMirror instance seeded from the same doc/offsets — decorations carry over 1:1 (same text, same offsets at the moment of the switch).
4. While typing: `DecorationSet.map(tr.mapping, tr.doc)` after every transaction — positions stay exact; visually mark spans "unverified" (dim/hatch, not deleted) because only the *score* is stale, not the *anchor* — see (D).
5. Re-score (explicit action or debounced): POST current text, get back a fresh span list computed directly against current text (no anchoring problem at all at that instant — offsets are freshly correct by construction), and replace the DecorationSet wholesale.
6. Persist/export/reload: serialize the redundant selector set; re-anchor fuzzily only here.

## (D) Interaction patterns

| Pattern | Named examples | Right when | Cost |
|---|---|---|---|
| (a) Separate pane / diff view, original preserved | Git/GitHub PR diffs, Google Docs "compare versions," Word "Compare Documents" | Provenance of the original matters as much as the edit; recompute is expensive and you want the user to see *what changed* before deciding to re-run | Doubles screen real estate; never shows one merged "current annotated state" — the reader must mentally recombine diff + annotation |
| (b) Edit in place, annotations invalidated/dimmed until re-run | IDE stale-coverage/stale-lint overlays; GitHub's "outdated" PR review comment (pinned to the old diff hunk, collapsed/greyed once the diff moves past it) | Recompute is a real model call (slow/costly); you must never present a stale score as fresh — a correctness/trust requirement | Between edits and the next run the user gets no live feedback; feels sluggish if runs are slow and not clearly triggerable |
| (c) Edit in place, annotations re-anchored live | Google Docs comments (structural paragraph anchor survives edits automatically); Grammarly-style underlines (feels live because re-check is fast, not because old results are remapped) | The anchor's *position* needs to track edits cheaply and correctly (plumbing), or the annotation's meaning doesn't depend on exact text (a paragraph-level comment) | For a semantic score like "how AI-generated," true live re-anchoring of an *old* score onto *new* text is actively misleading — the number was never computed for the text it now points at |
| (d) Suggestion / track-changes mode | Word/Google Docs Suggesting mode; CKEditor 5 Track Changes [22] (ops recorded as suggestion objects, shown as inline balloons in a side rail) | The edit itself needs a second party's review/approval, or you want a full accept/reject audit trail of changes since the last score | Heavyweight — you're building a mini version-control layer over the document, not just a decoration layer; usually overkill single-user |

**Recommendation for a "score → edit → re-score" tool:** use (b) as the *policy* — dim/flag spans as unverified the instant the underlying text changes, never silently reattach an old score to new text — implemented with (c)'s technique (ProseMirror Mapping) purely as internal plumbing to keep *positions*, not *validity*, correct while typing. Offer (a) as an optional secondary "compare last-scored vs. current text" view before a re-score, since you already have the previous snapshot for diffing once you keep it around at all. Skip (d) unless a second human reviewer is an actual requirement.

## (E) Overlap visualization + palette guidance

**Standard techniques, compared.** Single-hue **background fill** is the default and reads fastest for one layer but muddies under alpha-blended overlap (2+ translucent fills stacking into an unreadable third color). **Underlines** (color-coded) are what live checkers (Grammarly-style) and GLTR [25, 26] use for a single layer; GLTR specifically fills token *backgrounds* with a deliberately **categorical, not continuous**, 4-bucket rank scheme (top-10/top-100/top-1000/rest) because a bucketed read is faster at a glance than a gradient a reader must calibrate. **Left-margin/stacked-lane bars** are exactly what Prodigy's `spans.manual`/`spancat` UI does for overlaps: each overlapping span gets its own bracket row *below* the token line rather than blending into the fill [31] — this is the cleanest solution to "which spans overlap here" independent of color. displaCy's `spancat` "span" style does the analogous thing *above* the text, stacking multiple span labels vertically and tuning spacing between them [29, 30]. brat instead resolves overlap through explicit configuration of which entity types are permitted to `contain`/`equal`/`cross` [32]; INCEpTION exposes a per-layer "stacking" toggle and renders permitted overlaps as nested/stacked highlights, with click-to-inspect for the exact set at a point [33]. Attention/saliency tools (BertViz [27], Ecco [28], Google PAIR's LIT) solve a related but different problem — a token's relationship to *many* other tokens — with continuous single-hue intensity ramps, but represent that as small-multiples or a matrix, not as overlapping intervals on one line; they don't have an overlap-on-the-same-span problem the way span annotation does.

**Recommendation for continuous [0,1] scores with possible overlap:** split into two independent visual channels rather than trying to encode both score and overlap-count in hue. (1) **Color channel** — a single-hue-or-perceptually-uniform sequential fill for the *dominant* (max, or top-z-order) score at each character, per the local survey's interval-tree overlap-resolution model. (2) **Structural channel** — a Prodigy/displaCy-style stacked underline/bracket row for overlap identity and count, independent of hue, revealed fully on hover/click (Label Studio's `from_name`/`to_name` popover pattern is the reference UX for "click to see everything stacked here"). This keeps hue reserved purely for "how confident," never overloaded to also mean "how many things overlap here."

## (F) Color/accessibility guidance for a [0,1] confidence heat-highlight

- **Never use a rainbow/jet colormap.** Use a perceptually uniform sequential ramp: **Viridis** or **Cividis** are the concrete, named, widely available options [35]. Cividis was purpose-built and empirically validated (Nuñez, Anderton & Renslow, *PLOS ONE* 2018, DOI: 10.1371/journal.pone.0199239) so that readers with and without red-green color-vision deficiency perceive nearly the same image — the safer default when colorblind-safety is a hard requirement; Viridis is more broadly recognized and still strong (not perfect) under CVD simulation.
- If a single-hue, more "branded" ramp is preferred over a multi-hue perceptual one, **ColorBrewer's single-hue sequential families** (e.g. "Blues," "Oranges") are the standard named reference and are explicitly filterable for colorblind safety on colorbrewer2.org [37]; vary only lightness/saturation for the score, never hue, and keep the hue identical across light/dark themes.
- **Don't rely on color alone.** WCAG's guidance that state/meaning must not be color-only [38] applies directly here — pair the color ramp with the structural overlap channel from (E), or a numeric tooltip, so a color-deficient or grayscale reader isn't locked out of the score.
- **Contrast is a per-stop problem, not an endpoints problem.** Because the ramp is a *background* under real body text, check foreground/background contrast at every stop on the ramp, not just its two extremes. WCAG 2.1's 4.5:1 (body text) / 3:1 (large text) ratios [38] are the audited minimum; **APCA** (Advanced Perceptual Contrast Algorithm, developed for WCAG 3) [39] is the more accurate check for this exact situation because it scores light-text-on-dark and dark-text-on-light asymmetrically, which a single fixed ratio does not — directly relevant since the requirement spans both themes.
- **Light and dark mode need separate lightness ranges, not one reused hex ramp.** Viridis/Cividis's native range (dark purple/blue → bright yellow) was tuned as a *foreground/data-ink* palette against a light background; used as-is for a *background fill* on a dark UI, the yellow end washes out against light body text. Define the ramp in a perceptual space (OKLCH/CIELAB) and re-clamp its lightness range per theme — e.g. cap max lightness around L*70 for dark mode so the lightest stop still clears contrast against light-colored text, and invert the direction for light mode against dark text — rather than shipping one set of hex values for both themes.

---

## REFERENCES

[1] R. Sanderson, P. Ciccarese, B. Young, "Web Annotation Data Model," W3C Recommendation, 23 Feb 2017. [https://www.w3.org/TR/annotation-model/](https://www.w3.org/TR/annotation-model/)

[2] Hypothes.is, "Fuzzy Anchoring." [https://web.hypothes.is/blog/fuzzy-anchoring/](https://web.hypothes.is/blog/fuzzy-anchoring/)

[3] J. Udell, "Notes for an annotation SDK," 3 Sept 2021. [https://blog.jonudell.net/2021/09/03/notes-for-an-annotation-sdk/](https://blog.jonudell.net/2021/09/03/notes-for-an-annotation-sdk/)

[4] "Fuzzy text quote matching," Apache Incubator Annotator, Issue #83. [https://github.com/apache/incubator-annotator/issues/83](https://github.com/apache/incubator-annotator/issues/83)

[5] T. A. Phelps, R. Wilensky, "Robustly Anchoring Annotations Using Keywords," Microsoft Research Tech Report. [https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2001-107.pdf](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2001-107.pdf)

[6] "Annotation format," Annotator 1.2.10 documentation. [http://docs.annotatorjs.org/en/v1.2.x/annotation-format.html](http://docs.annotatorjs.org/en/v1.2.x/annotation-format.html)

[7] "W3C Selectors," Semiont documentation, The AI Alliance. [https://github.com/The-AI-Alliance/semiont/blob/main/docs/protocol/W3C-SELECTORS.md](https://github.com/The-AI-Alliance/semiont/blob/main/docs/protocol/W3C-SELECTORS.md)

[8] "Custom Google Docs comment anchoring schema," lmmx devnotes wiki. [https://github.com/lmmx/devnotes/wiki/Custom-Google-Docs-comment-anchoring-schema](https://github.com/lmmx/devnotes/wiki/Custom-Google-Docs-comment-anchoring-schema)

[9] "drive comments create: anchor field results in 'Original content deleted' in Google Docs," googleworkspace/cli, Issue #169. [https://github.com/googleworkspace/cli/issues/169](https://github.com/googleworkspace/cli/issues/169)

[10] Nutrient, "How to use PDF.js to highlight text programmatically." [https://www.nutrient.io/blog/how-to-add-highlight-annotations-to-pdfs-in-javascript/](https://www.nutrient.io/blog/how-to-add-highlight-annotations-to-pdfs-in-javascript/)

[11] Google, "diff-match-patch." [https://github.com/google/diff-match-patch](https://github.com/google/diff-match-patch)

[12] Recogito, "text-annotator-js." [https://github.com/recogito/text-annotator-js](https://github.com/recogito/text-annotator-js)

[13] "prosemirror-transform README" (Mapping, StepMap). [https://github.com/ProseMirror/prosemirror-transform/blob/master/src/README.md](https://github.com/ProseMirror/prosemirror-transform/blob/master/src/README.md)

[14] "ProseMirror Guide" (Decorations). [https://prosemirror.net/docs/guide/](https://prosemirror.net/docs/guide/)

[15] "Y.RelativePosition," Yjs Docs. [https://docs.yjs.dev/api/relative-positions](https://docs.yjs.dev/api/relative-positions)

[16] "Understanding CRDTs in Automerge" (cursors). [https://cran.r-project.org/web/packages/automerge/vignettes/crdt-concepts.html](https://cran.r-project.org/web/packages/automerge/vignettes/crdt-concepts.html)

[17] "CodeMirror Decoration Example." [https://codemirror.net/examples/decoration/](https://codemirror.net/examples/decoration/)

[18] "@codemirror/state README" (ChangeDesc). [https://github.com/codemirror/state/blob/main/src/README.md](https://github.com/codemirror/state/blob/main/src/README.md)

[19] "Point," Slate API docs. [https://docs.slatejs.org/api/locations/point](https://docs.slatejs.org/api/locations/point)

[20] "Migrating," Slate docs (marks/annotations removed from core). [https://docs.slatejs.org/concepts/xx-migrating](https://docs.slatejs.org/concepts/xx-migrating)

[21] "Node Transforms," Lexical docs. [https://lexical.dev/docs/concepts/transforms](https://lexical.dev/docs/concepts/transforms)

[22] "Track changes overview," CKEditor 5 Documentation. [https://ckeditor.com/docs/ckeditor5/latest/features/collaboration/track-changes/track-changes.html](https://ckeditor.com/docs/ckeditor5/latest/features/collaboration/track-changes/track-changes.html)

[23] "Robust anchoring of annotations to content," US Patent 7,747,943. [https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7747943](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7747943)

[24] "Grammarly Editor user guide," Grammarly Support. [https://support.grammarly.com/hc/en-us/articles/360003474732-Grammarly-Editor-user-guide](https://support.grammarly.com/hc/en-us/articles/360003474732-Grammarly-Editor-user-guide)

[25] S. Gehrmann, H. Strobelt, A. M. Rush, "GLTR: Statistical Detection and Visualization of Generated Text," arXiv:1906.04043, 2019. [https://ar5iv.labs.arxiv.org/html/1906.04043](https://ar5iv.labs.arxiv.org/html/1906.04043)

[26] GLTR (MIT-IBM Watson AI Lab / HarvardNLP). [http://gltr.io/](http://gltr.io/)

[27] J. Vig, "BertViz: Visualize Attention in Transformer Models." [https://github.com/jessevig/bertviz](https://github.com/jessevig/bertviz)

[28] J. Alammar, "Ecco: attention and saliency visualization for NLP models." [https://github.com/jalammar/ecco](https://github.com/jalammar/ecco)

[29] Explosion AI, "Spancat: a new approach for span labeling." [https://explosion.ai/blog/spancat](https://explosion.ai/blog/spancat)

[30] "displaCy: Fix horizontal spacing for multiple span labels," spaCy PR #10994. [https://github.com/explosion/spaCy/pull/10994](https://github.com/explosion/spaCy/pull/10994)

[31] "Span Categorization," Prodigy docs. [https://prodi.gy/docs/span-categorization](https://prodi.gy/docs/span-categorization)

[32] "Configuration," brat rapid annotation tool (overlap rules). [https://brat.nlplab.org/configuration.html](https://brat.nlplab.org/configuration.html)

[33] INCEpTION. [https://inception-project.github.io/](https://inception-project.github.io/)

[34] "Open-Source Annotation Tools Compared," Potato. [https://www.potatoannotator.com/docs/guides/text-annotation-tools-compared](https://www.potatoannotator.com/docs/guides/text-annotation-tools-compared)

[35] "Viridis Color Palette: Hex Codes Reference," SciFig. [https://scifig.ai/blog/viridis-color-palette-hex-codes](https://scifig.ai/blog/viridis-color-palette-hex-codes)

[36] J. R. Nuñez, C. R. Anderton, R. S. Renslow, "Optimizing colormaps with consideration for color vision deficiency," *PLOS ONE* 13(7), 2018. DOI: [10.1371/journal.pone.0199239](https://doi.org/10.1371/journal.pone.0199239)

[37] ColorBrewer: Color Advice for Maps. [https://colorbrewer2.org/](https://colorbrewer2.org/)

[38] "Web Content Accessibility Guidelines (WCAG) 2.1," W3C Recommendation. [https://www.w3.org/TR/WCAG21/](https://www.w3.org/TR/WCAG21/)

[39] E. Leudarovich, "APCA: The new color contrast standard for web accessibility." [https://medium.com/design-bootcamp/apca-the-new-color-contrast-standard-for-web-accessibility-f634511a3462](https://medium.com/design-bootcamp/apca-the-new-color-contrast-standard-for-web-accessibility-f634511a3462)
