# What a document-level verdict is a function of

Phase 2 measured a false-accusation rate of **20.6%** on 350 human-written documents and localised it precisely: the per-*segment* rate is flat and tolerable — 2.1%, 3.0%, 3.1%, 2.9% across proficiency bands — while the per-*document* rate quadruples. The segment evidence is in reasonable shape. The roll-up is where the harm is.

This document decides what to do about that, and fixes the gates, **before any of the numbers it gates were looked at**. Same discipline as [`curvature-as-evidence.md`](curvature-as-evidence.md) and [`phase-2-results.md`](phase-2-results.md); it is what caught the Binoculars proxy model that won on recall and would have shipped nearly double the false accusations.

## The mechanism, stated plainly

`Report.document` pools every signal in the document and runs one `aggregate` over the lot. With a per-segment false-flag rate of about 3%, the chance that *at least one* segment falsely fires is `1 − 0.97ⁿ`: 26% at ten segments, 60% at thirty. LOCNESS essays run to about twenty sentences, and were falsely accused 64% of the time before Phase 2.

`density_aggregate` damps this — it divides evidence by text length — but it does not remove the mechanism. `lean` still reads +1.0 whenever the only signals that fired were machine-leaning, however few, and a single moderate signal in a thousand characters still clears the strength floor. **Pooling treats accumulation as if it were corroboration.** Three 0.3-weight signals in three different paragraphs of a long essay are not three converging pieces of evidence about one claim; they are three independent low-precision events, and what matters about them is their *rate*.

## The shapes considered

**Keep pooling, damp harder.** Rejected in Phase 2 for reasons that still hold: the aggressive end of `REFERENCE_CHARS` was fitted to the only thing the fixtures could see, and re-treading it does not touch the mechanism.

**Refuse a document-level label entirely.** The most defensible thing the data alone supports, and genuinely tempting: the document verdict is the least supportable number this package emits and the one most likely to be quoted at somebody. What it costs is real — the CLI headline, `to_markdown`'s synopsis, the MCP verb's return shape, `Report.document` as a public field, and the shipped skills' reporting guidance all assume it exists. It is held in reserve below rather than dismissed.

**Make the document verdict a function of the segment verdicts.** Chosen. It attacks the mechanism directly instead of damping its output, and it is length-normalised *by construction* rather than by a constant that had to be fitted.

## The chosen shape, and the trap inside it

> The document-level `lean`, `strength` and `label` are computed from the **segment verdicts**, not from the pooled signals.

The trap is immediate and worth naming before implementing it. "What proportion of this document's segments lean machine" is one careless step from "what percentage of this document is AI" — the exact number [`why-no-percentage.md`](why-no-percentage.md) exists to refuse. A reported document lean that a reader can invert into a fraction-of-the-document has reintroduced the percentage through the roll-up instead of through the scorer.

So the two axes keep their existing meanings, and the quantity goes where quantity already goes:

- **`lean` stays a direction ratio.** `(machine-leaning segments − human-leaning segments) / (segments leaning either way)`. Exactly the shape segment-level lean already has. It says *which way the flagged parts point*, and it says nothing about how much of the document was flagged. It still reaches ±1.0 off a single flagged segment — the jaggedness that [`what-calibration-means-here.md`](what-calibration-means-here.md) identifies as the guardrail.
- **`strength` carries the rate.** A function of *what fraction of the document's segments carry directional evidence*, not of how many do. This is what makes it length-normalised by construction: one flagged segment in twenty is the same claim whether the document has twenty segments or two hundred.

Because `lean` is not a function of the rate and `strength` is not a function of the direction, neither one alone can be read as "how much of this is machine-written", and the pair cannot be inverted into one either. That is the same sufficiency argument Phase 2 made, applied one level up.

**Segment-level output does not change at all.** This is a change to the roll-up only, which makes the "did we trade away true positives" question answerable by inspection as well as by measurement.

### What it costs

`Report.document` keeps its type and its field names, so no consumer breaks. But its `lean` and `strength` now mean something slightly different — a ratio over *segments* rather than over *signals* — and `Report.document.signals` was always empty, which now matters more because the evidence genuinely lives one level down. The renderers and the skills must stop presenting the document line as the headline finding and start presenting it as a summary of the segments beneath it. That is a documentation change as much as a code change, and it is the honest one: **a flagged sentence is much better evidence than a flagged document**, and the output should stop implying otherwise.

## The gates, fixed before the numbers

**Gate 1 — the roll-up.** The rate-based roll-up replaces pooling only if:

1. it **reduces** document-level false accusations on the 350-document human corpus; and
2. it does **not reduce** the number of correctly-flagged machine segments on *either* mixed fixture — LLMTrace and RoFT, both.

Condition 2 is nearly free here, since segment labels are untouched by construction, but it is stated so that a later change which quietly alters them fails the gate rather than passing unnoticed.

**Gate 2 — a rule is negative value** if, across both mixed fixtures, it produces **no matches inside machine-written ground-truth spans**, and it matches **five or more** documents in the human corpus. Zero true positives with any false positives is strictly negative on this evidence; the threshold of five is there so that a rule which simply never fires is not condemned for being rare.

**Gate 3 — how a negative-value rule is corrected**, and this is the cross-package fork:

- If the rule is a genuine machine tell that merely also occurs in formal human writing, it is **demoted in `ductus` only**, via a per-rule weight. `acquaint` is right to keep flagging it for a writer; `ductus` is wrong to weigh it as heavily as evidence *about authorship*. This changes `ductus` alone.
- If the rule fires on good human writing that nobody should be advised to remove, then `acquaint` telling a writer to remove it is **also wrong**, and the rule's **tier** changes in `tells.yaml`. That is a two-repo change: `acquaint`'s suite pins verdicts, so it gets run and the change gets landed there too, not left drifted.

The second is harder, and being harder is not a reason to reach for the first. Nor is the first to be skipped merely because the second is available: a tier change alters what every `acquaint` user's linter enforces, so it requires the evidence to say the rule is *wrong*, not merely *noisy here*.

Note that the two loudest offenders Phase 2 named — `not-x-but-y` and `discourse-opener` — are not catalogue rules at all. They live in `ductus/detect.py` with hard-coded weights, so changing them touches no other package.

## Held in reserve

If the rate-based roll-up cannot bring document-level false accusations down without violating Gate 1's second condition, the conclusion is that **a document-level verdict is not supportable from evidence of this kind**, and the right answer is to stop emitting one. That outcome would be recorded and acted on rather than softened; it is written here so that it is a pre-registered branch rather than a retreat invented afterwards.
