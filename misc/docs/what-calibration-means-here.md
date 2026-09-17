# What "calibration" can mean in a package that refuses to emit a probability

The roadmap says Phase 2 fits `aggregate=` on labelled data, and adds: *"Even after calibration, no percentage. A fitted scorer changes what `lean` is computed from; it does not change what is reported."*

That sentence is the thing to check, not to quote. This document checks it, finds that **as usually implemented it is false**, and states the rule that survives. Written before anything was fitted, for the same reason [`curvature-as-evidence.md`](curvature-as-evidence.md) was written before anything was implemented.

## The trap, stated precisely

Fitting a scorer on labelled data is *the* standard route to a calibrated probability. It is the artifact [`why-no-percentage.md`](why-no-percentage.md) argues must never be reported. So Phase 2 as written walks straight at the thing Phase 0 forbade, and "we relabel the output" is not obviously a defence.

Take the natural implementation. Fit per-detector coefficients on the fixtures, score a document as `p = σ(Σ wᵈ xᵈ)`, report `lean = 2p − 1` to keep the [-1, +1] range the package promises.

Now ask what a reader can do with that. `lean = 2p − 1` is a bijection. Anyone who knows the procedure recovers `p = (lean + 1) / 2` exactly. A reported lean of +0.74 *is* "87% AI" with two extra keystrokes. The number was not changed, only its coordinates, and the costume `why-no-percentage.md` objects to is the costume, not the fabric.

So the roadmap's reassurance does not hold for that design. It is worth being blunt about this, because it is the design anyone would reach for first, and the failure is invisible from inside it: nothing in the output says "probability" anywhere.

## What actually keeps the current output from being a probability

Two properties, and they are worth naming because they are the things fitting must not destroy.

**`lean` deliberately discards quantity.** It is `(machine − human) / directional`, so it reads +1.0 whether one weak signal fired or six strong ones. A probability *must* integrate quantity — that is most of what makes it a probability. `lean` refuses to, and `strength` carries the discarded information on a separate axis that the package never combines back in. **The two-axis output is itself the anti-percentage device.** It is not presentational.

**`lean` is not a sufficient statistic for authorship.** Two documents with identical lean can warrant completely different conclusions depending on how much evidence there was and which detectors produced it. In the `σ(Σwx)` design, by construction, lean *is* sufficient — it is the whole posterior. That is the difference, and it is checkable.

## The rule

> **Calibrate the instrument, not the verdict.**
>
> Fitting is legitimate when it tunes how much each *kind of evidence* weighs relative to the others, or how evidence is normalised — properties of the detector set, measured once, publishable as a table a reader can inspect and disagree with.
>
> Fitting is illegitimate when it produces a per-document number estimating the probability that this document was machine-written, however that number is scaled or renamed.

The first kind of claim is about the tool and is the same for every document. The second is about a document, and through it about a person.

## The test that tells them apart

The rule needs an operational form, or it is just a sentiment. This is it:

> **The sufficiency test.** If a reader who knows the fitting procedure can recover an estimate of P(machine) from the reported output alone, the package is emitting a probability regardless of what it calls it.

`lean = 2p − 1` fails immediately. A lean that remains a ratio of fitted weights passes, because recovering a probability from it would require knowing *which* detectors fired and *how much* evidence there was — information that lives in the signal list and in `strength`, not in `lean`. The map from `lean` to P(machine) is many-to-one and stays that way.

A second, cruder check worth running on any proposed scorer: **does `lean` still reach ±1.0 on a single weak signal?** If a fitted scorer smooths that away — if one weak signal now yields +0.31 and six strong ones +0.93 — then lean has quietly become a quantity-integrating score, which is to say a probability. The jaggedness is not a defect to be fitted out. It is the guardrail.

## What that permits Phase 2 to fit

Three things, all of which are properties of the instrument:

1. **Relative evidence weights.** The current numbers — the tier→weight map, `0.12` for an em dash, `0.45` for a colon-tricolon, the `0.30/0.45` curvature bands — are hand-set guesses. Measuring how much each kind of evidence actually discriminates is a statement about the detector set, and it publishes as a table.
2. **How evidence is normalised.** Whether `strength` should saturate at a fixed total weight regardless of document length, or at a *rate* per unit text, is a question about the instrument that labelled data can answer. (Phase 2's measurement says it is the wrong question to have guessed at — see [`phase-2-results.md`](phase-2-results.md).)
3. **Where the label thresholds sit.** `LEAN_THRESHOLD` and `STRENGTH_FLOOR` decide when the package says anything at all. Moving them trades false accusations against silence, and that trade should be made against measured rates rather than taste.

None of those three requires a per-document probability to exist anywhere, even internally.

## What Phase 2 must therefore report

Not a score. **Operating characteristics**: how often the instrument accuses human writers, broken out by the populations who would pay for the error. That is a claim about the tool, it is the same kind of claim as "this scale reads 2g heavy", and it is publishable without ever attaching a number to a document.

It is also the claim this field routinely does not make about itself. `why-no-percentage.md` spends its length on other people's false-positive rates; a package that would not measure its own would be making exactly the move it criticises.

## Does a fitted `aggregate=` become the default?

**Gated on measurement, same as Phase 1, and the prior is opt-in.** A fitted scorer joins the default only if it measurably reduces false accusations on human-written text without hollowing out what the instrument can still find. The criterion is fixed in [`phase-2-results.md`](phase-2-results.md) before the numbers were looked at, and the answer recorded there is the answer, including if it is unflattering.

One asymmetry is worth stating up front, because it decides close calls: **on this package's terms a reduction in false accusations is worth more than an equal-sized reduction in findings.** `why-no-percentage.md` is an argument about who pays for the error, and the answer is not the tool's owner. Silence is a disappointment; a false accusation is a harm.
