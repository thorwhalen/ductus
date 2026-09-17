# Turning a curvature score into a `Signal`

Fast-DetectGPT and Binoculars each reduce a passage to one continuous number. `Signal` wants a direction, a weight in [0, 1], and a reason a person can argue with. Getting from the first to the second is the whole design problem of the `[local]` detectors, and it is the place where this package could most easily lose the thing it exists to protect. This document is the decision, written before the detectors were implemented.

The companion argument is [`why-no-percentage.md`](why-no-percentage.md). Everything here follows from it.

## The obvious mapping, and why it is not allowed

Both methods produce a score with a direction of increasing machine-likeness. Fast-DetectGPT's conditional probability curvature *d* is higher for machine text; Binoculars' ratio *B* is lower for machine text. The one-line implementation is

```python
weight = min(max((d - lo) / (hi - lo), 0.0), 1.0)  # do not do this
```

and it is exactly the percentage, wearing a different hat.

A weight of 0.78 arrived at this way asserts that this passage carries 0.78 of the maximum evidence a detector can carry — a quantitative claim about strength of evidence, derived from an uncalibrated statistic, on a document from a domain nobody measured. `aggregate()` then divides it by other weights and reports a lean to three decimal places. The output has all the surface properties of "87% AI" while being harder to audit, because the number entered through a detector rather than through a scorer and no longer looks like a claim at all.

Three further things go wrong, and each one matters on its own:

**It floods the evidence pool.** `strength` saturates at 1.5 total signal weight — roughly three moderate signals. A detector that emits one continuous-weight signal for *every* segment maxes `strength` out on a twelve-paragraph document before any deterministic detector has said anything. The document would read as heavily evidenced when nothing at all was found.

**It is not inspectable.** Every other signal in this package points at something the reader can go and check: a word, an apostrophe, a line break. A curvature score points at a passage and says "a language model found this unsurprising". The reader cannot verify that by looking. That is a different *kind* of evidence and it should not be priced identically to the kind you can exhibit.

**The published thresholds do not transfer.** Binoculars ships a threshold of 0.9015 — for the Falcon-7B pair, on its own benchmark. Fast-DetectGPT reports AUROC, not an operating point, and its black-box numbers trail its white-box numbers. Neither transfers to a CPU-sized proxy pair, and RAID's finding is that fixed thresholds do not survive a domain change even when the model is the one that was benchmarked \[1]. Hard-coding a constant lifted from a paper is a calibration claim made on somebody else's data.

## What these detectors are actually allowed to claim

Not "this text is machine-written". They cannot support that without a calibration this package does not have.

What they *can* support, from the same numbers and with no threshold borrowed from anywhere, is a comparison **inside one document**:

> This passage is markedly flatter — more predictable to a language model — than the rest of this document.

That claim needs no reference corpus, because the document supplies its own reference. It is falsifiable by a reader who rescores the document. And it happens to be the question the package is for: *ductus* gauges which **parts** of a text read as machine-written. Localization is the job, not a consolation prize.

So: **the curvature detectors score relatively, against the document they are reading, and never against an absolute threshold.**

## The mapping, stated exactly

1. **One pass, per document.** Per-token log-likelihood and the analytic reference moments are computed once over the whole text and cached. Everything below is arithmetic on those arrays; scoring a second span costs no model time.

2. **A span's score is the method's own statistic over that span's tokens.** For Fast-DetectGPT, `d = Σ(ll_i − μ_i) / sqrt(Σ σ²_i)`; for Binoculars, `B = mean(−log p_perf) / mean(cross-entropy observer→performer)`. No new statistic is invented — a span is just a window, and the published statistic is evaluated on it.

3. **The null distribution is empirical and local.** The same statistic is evaluated over every same-token-length window of the document that does *not* overlap the span. A span's standing is `z = (score − median) / (1.4826 · MAD)` against that set. Median and MAD rather than mean and standard deviation, because on a mixed document the machine-written stretches are exactly the outliers that would drag a mean toward themselves.

4. **Bands, with a dead zone in the middle.** `z` is quantized into three regions, not mapped continuously:

   | \|z\| | emitted |
   |---|---|
   | < 1.5 | **nothing** |
   | 1.5 – 2.5 | one signal, weight **0.30** |
   | ≥ 2.5 | one signal, weight **0.45** |

   The dead zone is the important half of this. A mid-range score is not weak evidence that something is going on; it is this detector having nothing to say, and the honest encoding of nothing is no signal. A weight of 0.05 on every segment is not humility, it is noise with a direction attached.

   The two weights are deliberately *not* larger than the strongest deterministic signal (`colon-tricolon`, 0.45). A statistic the reader cannot inspect does not get to outvote one they can. That is a judgment about evidence, and it is being stated rather than smuggled in as a constant.

5. **Direction is two-sided.** Flatter than the rest of the document leans `machine`; more surprising than the rest of the document leans `human`. Both are emitted. A detector that can only accuse is not a measuring instrument, and the human-leaning tail is real evidence: idiosyncratic word choice, domain jargon, typos and code-switching all raise perplexity, and all of them are traces of a person.

6. **Nothing is emitted when the comparison is impossible.** Fewer than six usable windows, or a degenerate spread (MAD of zero), and the detector yields nothing at all. "No findings" is already documented as a weak result rather than a clean bill; this is the same rule one level down.

## What the reason string has to say

For the deterministic detectors the reason is a gloss on something quoted. Here it is the entire evidence, so it carries three things — the number, the comparison class, and the model that produced it:

```
conditional probability curvature 2.496 under gpt2, 2.3 MADs flatter than the
rest of this document (25 comparable windows); unlike the other detectors this
is a model's opinion about the text, not a quotation from it
```

The clause after the double dash is not decoration. The reader is being asked to accept something they cannot check by looking at their own document, and the output should say so every time rather than once in a README. It is also what makes the finding reproducible: model id, statistic, comparison class and window count are everything needed to recompute it.

## What this costs, stated plainly

**These detectors cannot answer "was this whole document written by a machine?"** With one segment there is no reference distribution, and they return nothing. A uniformly machine-written document has no flat passages *relative to itself* and will come back empty. That is a real loss of capability, accepted knowingly: the absolute version of the question is the one that cannot be answered honestly without calibration, and Phase 2 is where calibration gets designed — not here, and not by hard-coding a constant from a paper.

**A wholly human document with one unusually plain paragraph will produce a machine-leaning signal.** Relative scoring always finds a most-extreme passage; the `|z| ≥ 1.5` floor and the window-count minimum make that require a genuine outlier rather than merely the largest of several similar values, but they do not eliminate it. The mitigations are that the weight is modest — one such signal alone lands at the `strength` floor — and that the reason string names the comparison class, so a reader can see the claim is about this document's internal variation and judge it accordingly.

**The bias documented in `why-no-percentage.md` is not fixed by any of this.** Low-perplexity prose is what these statistics measure, and a careful writer working in a second language produces low-perplexity prose. Scoring relatively contains the damage — a uniformly plain document has no internal outlier to flag — but a bilingual writer's plainest paragraph is still their plainest paragraph. This is the failure mode Phase 2 has to measure, and until it does, the honest statement is that it is present and unquantified.

## Choosing the models

The default pair is the smallest thing that works on a CPU, because a detector that requires a GPU is a detector most readers never run.

| Detector | Default | Documented upgrade |
|---|---|---|
| `fast_detect_gpt` | `gpt2` (124M), scoring and sampling in one pass | `EleutherAI/gpt-neo-2.7B`, or the paper's `gpt-j-6B` scoring model |
| `binoculars` | observer `distilgpt2`, performer `gpt2` | `tiiuae/falcon-7b` / `tiiuae/falcon-7b-instruct`, the paper's pair |

Binoculars' own ablations show the method depends on observer and performer being a *closely related* pair rather than an arbitrary strong/weak combination \[2]. `distilgpt2` is a distillation of `gpt2` and shares its tokenizer exactly, which is both the closeness the method wants and a hard requirement — the two models have to agree on what a token is for the cross-perplexity term to mean anything.

**Phase 2 measured this ladder and left both defaults where they were.** A `gpt2`/`gpt2-large` Binoculars pair finds substantially more machine text on both fixtures *and* nearly doubles the rate at which it accuses human writers (6.3% → 11.4%), so it was argued for and then refused. Recall and false-positive rate move together as the proxy gets stronger; "upgrade" is the wrong word for that trade. Anyone changing `model=`, `observer=` or `performer=` should re-run `python misc/measure_false_positives.py --pair-check` for their pair. The full ladder is in [`phase-2-results.md`](phase-2-results.md).

Both models are pulled from Hugging Face on first use and cached. The detectors are not in the default `detectors=` list and the core does not import `torch`; see the gate result in [`phase-1-results.md`](phase-1-results.md).

## REFERENCES

\[1] [Dugan L, et al. RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors. ACL 2024.](https://arxiv.org/abs/2405.07940)

\[2] [Hans A, et al. Spotting LLMs With Binoculars: Zero-Shot Detection of Machine-Generated Text. ICML 2024.](https://arxiv.org/abs/2401.12070)

\[3] [Bao G, et al. Fast-DetectGPT: Efficient Zero-Shot Detection of Machine-Generated Text via Conditional Probability Curvature. ICLR 2024.](https://arxiv.org/abs/2310.05130)
