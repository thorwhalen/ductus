# Driving the false-accusation rate down: 20.6% → 6.0%

Phase 2 measured what this package does to people who wrote their own work — **20.6% of 350 human-written documents called `leans-machine`** — and localised the harm precisely: the per-*segment* rate was flat and tolerable, the per-*document* rate quadrupled. This is the work that followed from that, and it was chosen over the HTTP and frontend surfaces because a UI on top of a one-in-five false-accusation rate is shipping the problem wider.

The decision and all three gates were fixed before the numbers they gate: [`document-verdict-decision.md`](document-verdict-decision.md). Reproduce with `python misc/measure_rules.py` and `python misc/measure_false_positives.py`.

## Result

| | before | after |
|---|---|---|
| **human documents falsely accused** (paragraph, the default) | 42/350 (12.0%) | **22/350 (6.3%)** |
| **human documents falsely accused** (sentence) | 72/350 (20.6%) | **21/350 (6.0%)** |
| human *segments* falsely accused (sentence) | 2.1 / 3.0 / 3.1 / 2.9% | **0.4 / 1.6 / 2.0 / 0.4%** |
| correctly-flagged machine segments, LLMTrace | 1/40 at 1/1 precision | **1/40 at 1/1** |
| correctly-flagged machine segments, RoFT | 0/75, 1 false flag | **0/75, 0 false flags** |

**Nothing was traded away.** Not one correctly-flagged machine segment was lost on either mixed fixture, and RoFT lost its single false flag. That is a 3.4× reduction on the sentence path at no measured cost in findings — which is not the usual shape of this trade and is worth being suspicious of, so the reason is set out below: two of the three changes removed rules that were finding *nothing*, and the third changed only how findings are summarised.

Per band, sentence granularity:

| band | before | after |
|---|---|---|
| A (beginner, non-native) | 15.4% | 2.3% |
| B (intermediate) | 23.0% | 10.0% |
| C (advanced) | 25.7% | 10.0% |
| N (native control) | 24.0% | 2.0% |

## The per-rule table, which is where the cheap win was

Every deterministic rule, counted against 350 human-written texts and both mixed fixtures. A signal is a *true positive* when its span lies inside machine-written ground truth.

| rule | detector | human docs implicated | human matches | true positives |
|---|---|---|---|---|
| `triad` | tells | 96 | 137 | 2 |
| `discourse-opener` | rhetoric | 88 | 117 | 4 |
| `exclamation` | tells | 54 | 87 | 8 |
| **`not-x-but-y`** | rhetoric | **42** | 47 | **0** |
| **`summary-closer`** | tells | **25** | 25 | **0** |
| `empty-transition` | tells | 22 | 27 | 1 |
| **`contrastive-negation`** | tells | **19** | 21 | **0** |
| everything else | | ≤ 3 each | | |

Three rules were finding **nothing at all** while implicating 86 human documents between them. That is Gate 2's definition of negative value, and it is the cheapest win in the package: they cost a great deal and earned literally zero.

### What they were actually matching

This is the part worth reading, because two of the three were not miscalibrated — they were **broken**.

`not-x-but-y` was matching *ordinary negation*. Its pattern made the intensifier optional, so every "not ⟨verb⟩ … but" in English tripped it:

> "I did **not eat from the tree but** from the bush." · "We do **not have to go to New Zealand but** we could." · "She chose **not to run too fast but** to finish."

`contrastive-negation` was matching the **"not only X but also Y" correlative** — a standard construction, used constantly by learners and essayists:

> "It is **not only fast, but** also simple." · "**Not only me but** also my sister went."

Neither is the model's antithesis habit. Both now require `just`, `merely` or `simply`, which is what the habit actually looks like ("not merely useful, but transformative" is still caught, and tested).

`summary-closer` is different: its pattern is correct. It matches `In conclusion,` / `To sum up,` — and that is *taught essay structure*, which is why 25 human writers tripped it and no machine text did.

## Tier and weight answer different questions

`summary-closer` sat at **tier E**, the highest — the tier for assistant chatter and leaked model disclaimers, and the one `acquaint` enforces even for a reader who tolerates AI-sounding prose. As evidence about *authorship* that is plainly wrong. As *style advice* it is defensible; plenty of editors will tell you to cut "In conclusion,".

Those are different claims, and the catalogue previously could not express them separately: `acquaint` enforces by **tier**, `ductus` weighs by **tier**, so they moved together. A rule could not be right about one and wrong about the other.

So the catalogue gained an optional per-rule `weight:`. `summary-closer` keeps tier E — `acquaint`'s linter is unchanged — and drops to weight 0.15, the floor, in `ductus`. **`acquaint` reads `tier` and never reads `weight`**, which was verified in its source before relying on it, so this is a one-package change by construction rather than by hope.

This is what Gate 3's first fork is for, and it is the honest answer here: the evidence I have is about authorship discrimination, which is `ductus`'s question. It says nothing about whether "In conclusion," is worth flagging as style advice, which is `acquaint`'s. **I have not answered `acquaint`'s question and have not changed its behaviour.** Whether tier E — enforced even at the most permissive tolerance — is right for a stylistic preference is a real question, and it is left open rather than settled by data that does not bear on it.

The `contrastive-negation` narrowing *is* a two-package change, and correctly so: telling a writer to remove "not only X but also Y" was bad advice as well as bad evidence. It landed in `acquaint` too, with a regression test pinning the correlative as ordinary English.

## The roll-up: the document verdict is now a function of the segment verdicts

With a ~3% per-segment false-flag rate, pooling every signal in a document and scoring the heap gives `1 − 0.97ⁿ`: a coin toss by thirty segments. **Pooling treated accumulation as though it were corroboration.** `density_aggregate` damped that; it did not remove the mechanism.

`ductus.score.roll_up` asks a different question — what *fraction* of the document's segments carry directional evidence, and which way does the evidence point — and it is length-normalised by construction rather than by a constant that had to be fitted on a corpus.

The two axes keep their existing meanings, which is what stops "proportion of segments leaning machine" from becoming "percentage AI":

- **`lean` is unchanged**: the direction ratio over signal weights. It says which way the evidence points and nothing about how much of the document it covers, and it still reaches ±1.0 off a single signal.
- **`strength` carries the quantity**, judged two ways and believed at its weakest: the *rate* of directional segments, and the evidence *density* per unit text.

### Two things that went wrong on the way, both instructive

**The rate view alone made the default worse.** Rate-only scoring cut the sentence path to 16.3% but pushed the paragraph path *up*, 12.0% → 13.7% — and paragraph is the default segmenter. With two paragraphs, one flagged is a rate of 50%, so the rate view throws away exactly the length normalisation that was protecting long two-paragraph documents. Requiring a document to satisfy **both** views, and believing the weaker, fixed it. Each view guards a failure the other misses.

**Counting segment labels silently discarded human evidence.** Computing `lean` from segment *labels* rather than signal weights drops every signal in a segment that never reached a label — and those are disproportionately the human-leaning ones, since human-leaning evidence tends to be quieter. Documents that should have read as mixed came out as `leans-machine`. Human-leaning signals are first-class in this package, and the first shape of the roll-up quietly demoted them. Reverted, and pinned by a test.

Neither was caught by reasoning. Both were caught by measuring the default configuration, which is the argument for measuring both segmenters every time.

## What is still there, and not acted on

The three most expensive rules survive Gate 2 because they are not worthless — `triad` (96 human documents, 2 true positives), `discourse-opener` (88, 4), `exclamation` (54, 8). They are the dominant remaining cost and their cost-to-benefit ratio is terrible.

They were **not** touched, and deliberately: Gate 2 was fixed before the table was seen, they do not trip it, and inventing a second criterion after seeing which rules a first one missed is exactly the move this project has avoided three times now. All three already sit at or near the weight floor, so there is little to demote; the real options are narrowing their patterns or cutting them, and both need a criterion set in advance and a reason better than "they are what is left". The evidence is recorded here for whoever sets that criterion.

`summary-closer` likewise still reads as negative value in the table — zero true positives, 25 human documents — because Gate 2 counts matches, not weights. It is retained at the floor because it is legitimate style advice for the other package.

## Is 6% the floor for rules of this kind?

Not obviously, but the remaining errors look different from the ones removed. What is left is concentrated in bands B and C (10% each) against 2.3% and 2.0% for beginners and natives — intermediate and advanced non-native writers, whose prose is fluent enough to reach for essayistic constructions and careful enough to avoid the mechanical human tells that would otherwise argue in their favour. That is the same mechanism Phase 2 named, now much smaller but not gone.

Lowering it further means either narrowing `triad`/`discourse-opener`/`exclamation`, or accepting that phrase-level rules cannot separate "formal essay register" from "machine register" because the two genuinely overlap. The second is a real possibility and would be worth saying plainly in the README if it turns out to be true.
