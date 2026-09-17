# Why there is no percentage in this package

Every commercial AI-text detector emits a single number: "87% AI". This package deliberately does not, and this is the one design decision worth defending at length, because everything else follows from it.

## The number is not what it looks like

"87%" reads as a calibrated probability — as if, across all texts scoring 87, roughly 87 in 100 were machine-written. No shipping detector supports that reading. The reported operating points come from a specific benchmark, at a specific threshold, against a specific set of generators, and none of it transfers to the document in front of you. Deploying any published detector with a fixed threshold on a new domain without re-calibrating reproduces the false-positive rates documented below [5].

So the number is a score, presented in the costume of a probability. That costume is the entire problem, because of who pays for the mistake.

## Who pays

Liang et al. ran seven commercial and academic detectors over TOEFL essays written by non-native English speakers: **61.3% average false-positive rate**, against near-zero on native-speaker control essays [1]. The bias tracks reduced lexical and syntactic complexity — the detectors are measuring how *simple* the prose is and reporting it as how *synthetic* the prose is. A person writing carefully in their second language trips it; a fluent native speaker using a model may not.

That is not a bug to be tuned away. It is what the underlying signal measures.

Meanwhile the rest of the field's numbers do not survive contact with independent evaluation. GPTZero publishes ≤1% FPR and 99.5% accuracy; independent testing finds 80–87% accuracy and 7–12% FPR on academic prose [3]. Over fifty universities have restricted or banned detector use on this basis [4].

And none of it survives an adversary. Sadasivan et al. prove that as a model's output distribution approaches the human text distribution, the AUROC of *any* best-possible detector approaches 0.5 [2]. Krishna et al. showed a single paraphrase pass dropping watermark true-positive rate from 99.8% to 9.7% [6]. A detector that can be defeated by one round-trip through a paraphraser, while falsely accusing one non-native writer in every two, is not an instrument. It is a liability with a user interface.

## What this package emits instead

Three values, none of which can be mistaken for a probability:

**`lean`**, in [-1, +1]. The ratio of machine-leaning to human-leaning evidence weight actually present. A lean of +1.0 means every signal that fired pointed the same way — it says nothing about how many fired.

**`strength`**, in [0, 1]. How much evidence there was at all. This exists precisely so that `lean = +1.0` cannot be reported alone: at strength 0.15 it is one weak signal, at strength 1.0 it is six converging ones, and collapsing those into a single number is the lie we are refusing to tell.

**`label`**, from a coarse vocabulary: `leans-machine`, `leans-human`, `mixed-signals`, `uncertain`, `no-evidence`. Never finer than the evidence supports.

Under all three sits the list of `Signal`s, each with a direction, a weight, the detector that produced it, a plain-language reason, and the exact span it came from. **Every number in the output can be traced back to a quotation from the text.** That is the property a percentage destroys.

## Two consequences worth stating

**Human-leaning signals are first-class.** A hard line break inside a sentence, mixed straight-and-curly apostrophes, a missing terminal period, an L2 grammar slip — these argue for a human at a keyboard, and the package reports them with the same machinery it reports machine-leaning evidence. A detector that can only ever accuse is not a measuring instrument. In practice these mechanical signals are often the most decisive thing in a document, in either direction.

**"No findings" is reported as a weak result, not a clean bill.** The deterministic detectors find phrases, artifacts and a few sentence shapes. Prose that is machine-written and bland trips none of them. Saying "clean" would be the same overclaim in the other direction.

## The cost we accept

This output is harder to consume. You cannot sort by it, threshold on it, or put it in a compliance report. That is the intended trade: a tool whose output cannot be used as an accusation cannot be misused as one.

If a calibrated score is genuinely needed for some downstream purpose, the `aggregate=` seam takes a replacement scorer in one keyword argument — and whoever fits it owns the calibration claim, the data it was fitted on, and the false-positive rate it carries.

## References

[1] [Liang W, Yuksekgonul M, Mao Y, Wu E, Zou J. GPT detectors are biased against non-native English writers. *Patterns* 2023.](https://arxiv.org/abs/2304.02819)

[2] [Sadasivan VS, Kumar A, Balasubramanian S, Wang W, Feizi S. Can AI-Generated Text be Reliably Detected?](https://arxiv.org/abs/2303.11156)

[3] [GPTZero Review 2026: Accuracy, Pricing, and Verdict.](https://fast.io/resources/gptzero-ai-detector-review-2026/)

[4] [AI Detector Accuracy: The False-Positive Evidence.](https://casrai.org/guides/ai-detection-accuracy-higher-education)

[5] [Dugan L, et al. RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors. ACL 2024.](https://arxiv.org/abs/2405.07940)

[6] [Krishna K, et al. Paraphrasing evades detectors of AI-generated text, but retrieval is an effective defense. NeurIPS 2023.](https://arxiv.org/abs/2303.13408)
