# Phase 2 result: what this package does to human writers

Phase 1 ended with a finding that made this the next thing to measure: *every* false machine flag the model-based detectors produced was plain human prose — casual email, wire-service sport, flat narration. That is the mechanism Liang et al. document, and a package whose central document spends its length on other people's false-positive rates has no business not measuring its own.

So this phase is mostly measurement. Three things came out of it, and only one was expected.

1. **The shipped defaults falsely accuse human writers often** — 34.3% of 350 human-written documents, before this phase's change. That is now 20.6%, and it is still not small.
2. **Most of that was a length artefact, not a language one.** The chance of a false accusation ran from 11% to 74% with document length alone. That is a defect in the document-level roll-up, it was found by measurement rather than by reading the code, and fixing it is what the `aggregate=` seam is for.
3. **The bias runs the opposite way from the literature.** These detectors over-flag *formal, fluent, essayistic* writing, not simple writing. The native-speaker control was the most-accused group in the corpus, not the least.

The design decision that had to be settled before any of this could be fitted is in [`what-calibration-means-here.md`](what-calibration-means-here.md). Reproduce with `python misc/measure_false_positives.py` (the corpus downloads on first run).

## The corpus, and why it is not in this repository

BEA-2019 **W&I+LOCNESS**: 350 texts, every one written by a person, every one carrying a **CEFR proficiency level**.

| band | source | writers | texts |
|---|---|---|---|
| A | Cambridge English Write & Improve | non-native, beginner (A1–A2) | 130 |
| B | Write & Improve | non-native, intermediate (B1–B2) | 100 |
| C | Write & Improve | non-native, advanced (C1–C2+) | 70 |
| N | LOCNESS | native-speaker control | 50 |

This is the closest license-obtainable analogue of the TOEFL11 essays Liang et al. used, and better in one respect: the proficiency labels mean the false-positive rate can be reported *by band against a native control* rather than as one aggregate that hides who pays.

It is released for **non-commercial research use with no redistribution**, so it is not vendored. `misc/measure_false_positives.py` downloads it to `~/.local/share/ductus/corpora/` on first run and the *numbers* are committed here. Measuring a corpus does not require vendoring it, and the alternative — dropping the measurement because the licence was inconvenient — would have been the wrong trade by a wide margin.

TOEFL11 itself is LDC-paid and ICNALE/EFCAMDAT are registration-gated; none of them were needed.

## The headline

Per-document false accusations, sentence granularity, deterministic defaults. **Every one of these is wrong** — the corpus is entirely human-written.

| band | before Phase 2 | **shipped now** |
|---|---|---|
| A (beginner, non-native) | 20/130 (15.4%) | 19/130 (14.6%) |
| B (intermediate, non-native) | 36/100 (36.0%) | 23/100 (23.0%) |
| C (advanced, non-native) | 32/70 (45.7%) | 18/70 (25.7%) |
| N (native control) | 32/50 (64.0%) | 12/50 (24.0%) |
| **all** | **120/350 (34.3%)** | **72/350 (20.6%)** |

At paragraph granularity, 71/350 (20.3%) → 42/350 (12.0%), with the native control moving 60.0% → 24.0%.

**A flagged sentence is much better evidence than a flagged document.** The per-*segment* rate barely moves across bands — 2.1%, 3.0%, 3.1%, 2.9% — while the per-document rate quadruples. That gap is the finding below.

## Why: the roll-up was counting, not measuring

Pooling all 350 documents and cutting by length instead of by band, with the pre-Phase-2 scorer:

| document length | texts | falsely accused |
|---|---|---|
| under 750 chars | 97 | 11 (11.3%) |
| 750–1250 | 127 | 38 (29.9%) |
| 1250–1750 | 53 | 25 (47.2%) |
| 1750–2500 | 42 | 23 (54.8%) |
| over 2500 | 31 | 23 (74.2%) |

A human document was nearly seven times more likely to be accused for being long. The mechanism is plain once seen: `lean` is a *ratio* of evidence weights and `strength` a *total*, so neither has any notion of how much text the evidence was drawn from. Two stray signals in 600 characters and two in 3000 produced identical output. Longer text simply gives more chances to trip one rule, and nothing downstream knew the difference.

This is also why the native control looked so bad: LOCNESS essays have a median length of 2458 characters against 616 for band A. Length and band were confounded, and most of the apparent proficiency effect was length.

### The fix, and where it lives

The `aggregate=` seam could not express the fix, because **it never saw how much text produced the evidence**. Its signature took signals and nothing else. That is a seam that was specified too narrowly, and per this repo's own rule the seam is what gets fixed rather than papered over at the call site.

`aggregate` now takes `n_chars` by keyword, and `ductus.score.density_aggregate` divides evidence by the text that produced it above a reference length. It is the new default. Three properties made it safe to make default, and all three are pinned in `tests/test_density_aggregate.py`:

- **It can only ever remove an accusation.** The scaling divides and never multiplies, so no document gains a finding it did not have.
- **Short passages are untouched.** Below `REFERENCE_CHARS` it is exactly the old scorer, which is why the per-segment rates above are unchanged.
- **`lean` is not touched at all.** It still reads ±1.0 off a single weak signal. Smoothing that is precisely how `lean` would become a quantity-integrating score, which is to say a probability — see [`what-calibration-means-here.md`](what-calibration-means-here.md).

### Choosing the constant

`REFERENCE_CHARS` was selected **on the human corpus** and its cost read off the two mixed fixtures, which the selection never looked at (`python misc/measure_false_positives.py --sweep`):

| REFERENCE_CHARS | A | B | C | N | all human | llmtrace hits | roft hits |
|---|---|---|---|---|---|---|---|
| length-blind (before) | 15% | 36% | 46% | 64% | **34.3%** | 1 | 0 |
| 4000 | 15% | 36% | 46% | 64% | **34.3%** | 1 | 0 |
| 2000 | 15% | 36% | 46% | 44% | **31.4%** | 1 | 0 |
| 1500 | 15% | 33% | 39% | 38% | **28.3%** | 1 | 0 |
| **1000 (shipped)** | 15% | 23% | 26% | 24% | **20.6%** | 1 | 0 |
| 750 | 12% | 21% | 23% | 8% | **16.3%** | 1 | 0 |
| 500 | 7% | 14% | 11% | 2% | **9.1%** | 1 | 0 |

500 looks better on every line, and it was not chosen. **Every fixture document is under about 1600 characters, which is below where the normalisation bites.** So the benefit is measured on long documents and the cost only on short ones, and a setting picked at the bottom of that table would be fitted to the one thing the data can see. 1000 is the least aggressive value that removes most of the length gradient. A reader who wants 500 has the table and the keyword.

## The bias runs the other way

The literature's warning — and this package's own README — is that detectors over-flag non-native writers because the underlying signal measures how *simple* prose is. That is not what these detectors do.

Length-matched to 900–1800 characters, with the pre-Phase-2 scorer, the residual proficiency effect is real and points **up** the proficiency scale:

| band | texts in range | falsely accused |
|---|---|---|
| A (beginner) | 35 | 11 (31.4%) |
| B (intermediate) | 63 | 25 (39.7%) |
| C (advanced) | 45 | 21 (46.7%) |
| N (native) | 7 | too few to compare |

The mechanism is visible in which rules fire. On the native control: `triad` (38), `not-x-but-y` (22), `discourse-opener` (21). On band A: `no-terminal-punctuation` (23), `trailing-whitespace` (22), `exclamation` (22).

So the deterministic layer is measuring **formal argumentative register** — tricolons, antithesis, "However" at the head of a paragraph — which is what a model emits *and* what a native undergraduate writing a persuasive essay was taught to write. Meanwhile beginner writing trips the mechanical *human* signals, which push its lean negative and protect it.

Stated plainly: **this package is biased against good writing, not against non-native writing.** That is a different failure from the one in the literature, it is not obviously a better one, and the people it lands on are students writing well-formed essays.

Both directions belong in the README, and both are now there. Neither is fixed by this phase.

## The model-based detectors, revisited

Two Phase 1 conclusions were wrong in the same direction, and the reason was the fixture.

### On a fixture whose machine text was not written to blend in

Phase 1 closed by flagging that LLMTrace's `fill_gaps` documents — machine text composed to fit a hole in human prose — are close to a worst case for a perplexity method. `tests/fixtures/roft_boundary.json` is now vendored beside it: a RoFT slice (MIT), 18 documents, a human prefix followed by a machine continuation, two documents at each of the nine boundary positions. Deliberately a different ground-truth shape; a detector that only works on one shape has a result about the fixture.

Sentence granularity:

| detector set | machine recall | machine precision | agreement |
|---|---|---|---|
| deterministic (the default) | **0/75 (0%)** | 0/1 (0%) | 8/11 (73%) |
| fast-detect-gpt | **12/75 (16%)** | 12/14 (86%) | 18/24 (75%) |
| binoculars | 9/75 (12%) | 9/12 (75%) | 14/21 (67%) |
| both model-based | 14/75 (19%) | 14/18 (78%) | 21/29 (72%) |

The deterministic detectors find **nothing at all** here — creative fiction contains no "delve" and no tricolons — while the model-based pair clears the Phase 1 gate outright, on both recall and precision. The Phase 1 caveat was correct, and it was load-bearing rather than decorative.

### And they accuse human writers less often than the default does

Measured alone on the same 350 human texts, sentence granularity, with the pre-Phase-2 scorer so the comparison is like for like:

| band | deterministic | fast-detect-gpt | binoculars | both |
|---|---|---|---|---|
| A | 15.4% | 9.2% | 8.5% | 12.3% |
| B | 36.0% | 14.0% | 8.0% | 9.0% |
| C | 45.7% | 10.0% | 10.0% | 8.6% |
| N | 64.0% | 22.0% | 24.0% | 24.0% |

They are better on every band, dramatically so on B, C and N. Their band profile is also nearly flat across A/B/C, which is what you would expect from a detector that is not keyed to register.

### So why are they still not the default?

Not accuracy — **dependencies**. `DEFAULT_DETECTORS` has to work on `pip install ductus` with no `torch` and no model download, and that constraint is not negotiable by measurement. The honest recommendation is therefore conditional, and the README now says it: *if you have installed the extra, turn them on.*

## Does the proxy model change the answer?

Yes, and more than the fixture did. This is the lever Phase 1 named as cheapest-untried, and it turns out to have been understating the case: **the CPU-sized defaults are the weakest rung by a wide margin**, and Phase 1's "gate not cleared" verdict was as much an artifact of the proxy models as of the fixture.

`python misc/measure_model_ladder.py`, sentence granularity.

### The rule for changing a shipped default, fixed before the second half was seen

The llmtrace numbers below were in hand when this was written; the RoFT numbers were not. Stating it here rather than afterwards:

> A default proxy model changes only if the better pair wins **on both fixtures**. One fixture with 40 decisive machine segments, where a one-document difference moves a percentage point, is not a basis for changing what every user downloads.

And a second condition, added once the ladder was in and before the corresponding measurement was run, because the first one left a hole this package should not leave:

> ...**and only if its false-positive rate on human-written text is not worse.** Promoting a proxy model on recall and precision alone, without checking what it does to human writers, would contradict everything else in this document.

### LLMTrace (40 decisive machine segments)

| detector | proxy model | machine recall | precision | agreement | time |
|---|---|---|---|---|---|
| fast-detect-gpt | **gpt2 (124M, the default)** | 2/40 (5%) | 2/4 (50%) | 10/12 (83%) | 12s |
| fast-detect-gpt | gpt2-large (774M) | 5/40 (12%) | 5/6 (83%) | 11/12 (92%) | 22s |
| fast-detect-gpt | gpt2-xl (1.5B) | 5/40 (12%) | 5/7 (71%) | 12/14 (86%) | 39s |
| binoculars | **distilgpt2/gpt2 (the default, kept)** | 1/40 (2%) | 1/5 (20%) | 9/13 (69%) | 10s |
| binoculars | gpt2/gpt2-large | 6/40 (15%) | 6/8 (75%) | 14/16 (88%) | 22s |
| binoculars | gpt2-large/gpt2-xl | 6/40 (15%) | 6/10 (60%) | 17/21 (81%) | 336s |

### RoFT (75 decisive machine segments)

| detector | proxy model | machine recall | precision | agreement | time |
|---|---|---|---|---|---|
| fast-detect-gpt | **gpt2 (124M, the default)** | 12/75 (16%) | 12/14 (86%) | 18/24 (75%) | 7s |
| fast-detect-gpt | gpt2-large (774M) | 9/75 (12%) | 9/10 (90%) | 16/20 (80%) | 21s |
| fast-detect-gpt | gpt2-xl (1.5B) | 11/75 (15%) | 11/13 (85%) | 21/26 (81%) | 43s |
| binoculars | **distilgpt2/gpt2 (the default, kept)** | 9/75 (12%) | 9/12 (75%) | 14/21 (67%) | 14s |
| binoculars | gpt2/gpt2-large | 13/75 (17%) | 13/17 (76%) | 23/28 (82%) | 35s |
| binoculars | gpt2-large/gpt2-xl | 11/75 (15%) | 11/12 (92%) | 22/26 (85%) | 530s |

### What the rule decided

The two-fixture rule gave **different answers for the two detectors**, which is the whole reason for having written it down first.

**`fast-detect-gpt` keeps `gpt2`.** Going up to `gpt2-large` more than doubles recall on LLMTrace (2→5) and lifts precision from 50% to 83% — and then *loses* recall on RoFT (12→9). A model that wins decisively on one fixture and loses on the other has not earned a change to what every user downloads. That is exactly the case the rule exists to refuse.

**`binoculars` passed the first condition.** It wins on both fixtures: LLMTrace 1→6 machine segments and 20%→75% precision, RoFT 9→13 at the same precision with agreement up from 67% to 82%. The old default pair was not merely weaker, it was **close to useless on LLMTrace** — one segment found, four of five flags wrong. Shipping that as the default understated what the method can do and made Phase 1's verdict look like a fact about Binoculars when it was partly a fact about `distilgpt2`.

**Nothing goes above ~1B.** `gpt2-xl` matches `gpt2-large` on recall and does not beat it on precision, and the `gpt2-large`/`gpt2-xl` Binoculars pair costs **530 seconds against 35** for no gain on either fixture. On 40 and 75 decisive segments a one-document difference moves several percentage points, so the flat top of this ladder is a statement about these fixtures, not about the methods.

On the first condition alone, then, the Binoculars default should change — at the cost of a larger download, about 0.9GB to about 3.7GB, paid only by someone who has already installed the `[local]` extra and `torch`. That is where this would have ended if the second condition had not been written down.

### And then the false-positive condition refused it

`python misc/measure_false_positives.py --pair-check`, the same 350 human-written texts:

| band | distilgpt2/gpt2 (kept) | gpt2/gpt2-large (rejected) |
|---|---|---|
| A (beginner, non-native) | 10/130 (7.7%) | 14/130 (10.8%) |
| B (intermediate) | 5/100 (5.0%) | 13/100 (13.0%) |
| C (advanced) | 3/70 (4.3%) | 7/70 (10.0%) |
| N (native control) | 4/50 (8.0%) | 6/50 (12.0%) |
| **all** | **22/350 (6.3%)** | **40/350 (11.4%)** |

**Worse on every band, and nearly double overall.** So the Binoculars default does not change after all, and the paragraphs above stand as the record of a change that was argued for and then refused.

This is the most useful thing in the phase. A stronger proxy pair found more machine text on *both* mixed fixtures — and almost doubled the rate at which it accuses people who wrote their own work. It is not "better". **Recall and false-positive rate move together as the proxy model gets stronger**, which is exactly why this package will not collapse its output into one number that hides which of the two you are buying.

Had the second condition not been written down, a measurably more dangerous default would have shipped on a measurably better recall figure, in the same release as a document arguing that false positives are the thing that matters most.

### What this does say about turning them on

At their shipped defaults and under the shipped scorer, the model-based detectors accuse human writers **far less often than the deterministic default does**: 6.3% for `binoculars` against 20.6%. Combined with clearing the Phase 1 gate on RoFT, that is the basis for the README's recommendation — install the extra, turn them on — and it is a recommendation about the *default* models, not an invitation to scale up.

Anyone who does scale up should re-run `--pair-check` for their pair before trusting it. The seam takes `model=`, `observer=` and `performer=`; the measurement is one command; and this table is what happens when you skip it.

## What was not done, and what it would take

- **Falcon-7B was not tested.** The Binoculars paper's pair is ~28GB and CPU inference on 7B parameters puts a single fixture document into the minutes — not runnable here, and not runnable by a reader on the hardware this package targets. `python misc/measure_model_ladder.py` spans 124M to 1.5B, which answers *whether* model size moves the result but not where the curve flattens. Anyone with a GPU can pass `model=` / `observer=` / `performer=`; that is what the seam is for.
- **Per-detector weights were not fitted.** [`what-calibration-means-here.md`](what-calibration-means-here.md) permits it, and the data does not support it: seven deterministic signals across twelve LLMTrace documents is not an evidence base for fitting anything. Fitting on it would have produced numbers with the shape of a result and none of the content. The normalisation change was worth making because it rests on 350 documents, not on seven signals.
- **No second non-native corpus.** The proficiency effect here rests on one corpus from one platform. The direction is clear and the mechanism is legible, but a replication on independently collected text would be worth more than another decimal place on these numbers.

## REFERENCES

\[1] [Liang W, Yuksekgonul M, Mao Y, Wu E, Zou J. GPT detectors are biased against non-native English writers. *Patterns* 2023.](https://arxiv.org/abs/2304.02819)

\[2] [Bryant C, Felice M, Andersen ØE, Briscoe T. The BEA-2019 Shared Task on Grammatical Error Correction.](https://aclanthology.org/W19-4406/) — the W&I+LOCNESS release.

\[3] [Dugan L, Ippolito D, Kirubarajan A, Shi S, Callison-Burch C. Real or Fake Text? Investigating Human Ability to Detect Boundaries Between Human-Written and Machine-Generated Text. AAAI 2023.](https://arxiv.org/abs/2212.12672)
