# Phase 1 result: the model-based detectors did not earn a place in the default

**They ship, and they ship off by default.** Fast-DetectGPT and Binoculars are implemented, registered and usable — `--detectors fast-detect-gpt` — but they are not in `DEFAULT_DETECTORS`, because they did not clear the gate the roadmap set for them. This document is the measurement, including the numbers that are unflattering, because a gate you move after seeing the result is not a gate.

Reproduce it with `python misc/measure_detectors.py` (needs the `[local]` extra; the proxy models download on first run). The design being evaluated is in [`curvature-as-evidence.md`](curvature-as-evidence.md).

## The criterion, fixed before the numbers were looked at

> A detector set beats the baseline when it correctly flags **strictly more** machine-written decisive segments, **without** its machine-side precision falling below the baseline's.

Recall is what Phase 1 existed to fix — that is why the first clause is about recall. The second clause is what stops recall being bought with false accusations, which on this package's own terms would be a loss disguised as a gain.

A *decisive* segment is one the ground truth is unambiguous about: at least 80% machine-written characters, or at most 20%. Segments straddling a boundary are excluded, exactly as `tests/test_ground_truth.py` excludes them — there is no clean label to score them against. Across the 12 documents at sentence granularity that leaves 40 decisive machine segments and 61 decisive human ones.

## What happened

Sentence granularity, 12 documents, CPU, `gpt2` and `distilgpt2`:

| detector set | signals | machine recall | machine precision | human recall | human precision | agreement | time |
|---|---|---|---|---|---|---|---|
| deterministic (baseline) | 7 | 1/40 (2%) | 1/1 (100%) | 0/61 (0%) | — | 6/6 (100%) | <1s |
| fast-detect-gpt | 12 | 2/40 (5%) | 2/4 (50%) | 8/61 (13%) | 8/8 (100%) | 10/12 (83%) | 11s |
| binoculars | 13 | 1/40 (2%) | 1/5 (20%) | 8/61 (13%) | 8/8 (100%) | 9/13 (69%) | 5s |
| both model-based | 25 | 2/40 (5%) | 2/7 (29%) | 10/61 (16%) | 10/10 (100%) | 12/17 (71%) | 8s |
| deterministic + model-based | 32 | 3/40 (8%) | 3/8 (38%) | 10/61 (16%) | 10/10 (100%) | 18/23 (78%) | 7s |

**No row clears the gate.** The best machine-side recall on offer is 3/40 against the baseline's 1/40, and it costs precision falling from 1/1 to 3/8. Recall did move in the intended direction; it did not move far, and it did not move cleanly.

Two honest caveats about that table, in both directions:

The baseline's "100% precision" is one correct flag out of one flag. That is not a measurement, it is a single coin landing heads, and a gate anchored to it is stricter than it looks. This is why the `agreement` column is there — it is the metric `tests/test_ground_truth.py` already uses, over a larger denominator. On that metric too the model detectors are behind: 100% for the baseline (6/6), 83% for Fast-DetectGPT (10/12), 69% for Binoculars (9/13).

And the fixture is close to a worst case for these methods. LLMTrace's `fill_gaps` documents are machine text written *to fit the surrounding human prose* — the case where a perplexity gap is smallest by construction — scored here by `gpt2`, a weak proxy, against a `gemini-2.5-flash` generator. Better proxy models would very likely do better. That is a reason to retest at the documented upgrade, not a reason to waive the gate: the gate was set against the fixture that exists.

At paragraph granularity the model detectors emit nothing at all, and correctly so: the fixture's documents have one to three paragraphs, which is fewer comparable windows than the minimum, so there is no reference distribution to stand against. The fixture also contains **no** decisive machine-written paragraph (every paragraph is mixed), so paragraph granularity cannot measure machine-side recall for anything, baseline included. It is reported for completeness and says nothing.

## The finding that is not in the gate

The gate asks about accusation. The more interesting result is on the other side.

**The model detectors found 10 human-leaning segments where the deterministic set found 0, and all 10 were right.** Against a base rate of 61/101 decisive segments being human, ten correct calls in a row lands at p ≈ 0.006 — suggestive rather than established at that sample size, but it is a real capability the package did not have this morning. Under this package's stated position — "a detector that can only accuse is not a measuring instrument", and human-leaning signals are first-class — that is the kind of gain worth having, and it is the reason these detectors ship at all rather than being deleted.

It did not change the decision, because the gate is about recall on machine text and was written that way on purpose.

## The failures are the documented failures

Every false machine flag the model detectors produced is plain, unadorned human prose:

```
llmtrace-08035  "Hi Pamela,The Zune Car thingy should be able to play what you have..."
llmtrace-08035  "You don't want it to play the radio from the zune because your cars..."
llmtrace-08059  "The searchers stumble upon the crashed car and find the two children..."
llmtrace-08088  "Roy Keane was spotted in the stands at Goodison Park on Monday night..."
llmtrace-08088  "Keane left his position as Paul Lambert's assistant after just six months..."
```

Casual email, plain narration, wire-service sport reporting. This is precisely the mechanism Liang et al. document: the statistic measures how *simple* the prose is and the reader hears how *synthetic* it is \[1]. Scoring relative to the document contains it but does not remove it — a document's plainest passage is still its plainest passage.

That these are the false positives, rather than a scatter of unrelated ones, is worth more than the recall numbers. It says the failure mode is the known one and behaves as predicted, which is what makes it something Phase 2 can measure rather than something that has to be discovered again.

## Decision

- **Not in `DEFAULT_DETECTORS`.** `detectors=None` still means the four deterministic detectors, and `import ductus` still costs no `torch`.
- **Shipped, registered and documented as opt-in.** `--detectors fast-detect-gpt,binoculars`, or `detectors=[...]` in Python. Someone reading a long document, who has the extra installed and a minute to spend, gets the human-side evidence and a second opinion on the machine side.
- **`misc/measure_detectors.py` is committed**, so re-running the gate after a change to the bands, the proxy models or the fixture is one command rather than a reconstruction.

## What would change the answer

In roughly descending order of expected effect:

1. **A better proxy pair.** `EleutherAI/gpt-neo-2.7B` for Fast-DetectGPT, `tiiuae/falcon-7b` / `-instruct` for Binoculars — the models these methods were actually benchmarked with. The band arithmetic does not change; only the `model=` argument does. This is the single cheapest thing to try and the one most likely to move the numbers.
2. **A fixture whose machine text was not written to blend in.** `fill_gaps` is the adversarial case. RoFT (Phase 2) is human-prefix-then-machine-continuation, a different and less hostile shape.
3. **Calibration (Phase 2).** The bands are currently `|z| ≥ 1.5` and `≥ 2.5`, chosen as "a real outlier" and "a strong one" rather than fitted — deliberately, since fitting them on this fixture and then reporting a gate pass on the same fixture would be the cherry-picking `CLAUDE.md` forbids. Fitting them on a *separate* corpus, and reporting the false-positive rate that comes with them, is exactly Phase 2's job.

None of these is Phase 1's to do.

## REFERENCES

\[1] [Liang W, Yuksekgonul M, Mao Y, Wu E, Zou J. GPT detectors are biased against non-native English writers. *Patterns* 2023.](https://arxiv.org/abs/2304.02819)
