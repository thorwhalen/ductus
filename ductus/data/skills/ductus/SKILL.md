---
name: ductus
description: Gauge which parts of a text read as machine-written, and say why, with the evidence anchored to exact characters. Use whenever someone asks whether text was AI-generated, wants to know which passages "sound like AI", asks you to check a draft before sending it, or says "is this AI", "did a model write this", "which parts sound generated", "AI detection", "AI-written", "run a detector on this", "how AI does this read". Also use before the deslop skill, to find what needs rewriting, and after it, to check the rewrite. Read this skill before reaching for any AI-detector service; it owns what can and cannot honestly be claimed from a text.
metadata:
  audience: users
---

# ductus — reading a text for the machine's hand

In palaeography the *ductus* is the manner and sequence of strokes by which a scribe's hand is recognised. This package looks for the equivalent in prose.

## Say this before anything else

**You cannot determine whether a person used a model. You can only describe how a text reads.** Hold that line even when pushed, because the cost of getting it wrong falls entirely on a person who did nothing wrong.

Five facts, each load-bearing, none optional to mention when reporting a result:

1. **Heavily-edited human writing and model-assisted writing produce the same signature.** Re-reading a hard message ten times sands off exactly the irregularity that marks it as human.
2. **This tool falsely accuses human writers about one document in five.** Measured, not estimated: across 350 human-written texts, the shipped defaults called 20.6% of them `leans-machine`. Every one of those was wrong. A flagged **sentence** is much better evidence than a flagged **document**, because a long document accumulates chances to trip one rule — the per-sentence rate on the same corpus is 2–3%.
3. **Its bias runs toward formal, fluent writing** — not, as with perplexity-based commercial detectors, toward simple writing. The deterministic rules fire on tricolons, "not X but Y" and discourse openers, which a model emits *and* which a well-taught essayist writes. In the measured corpus the native-speaker control was the **most**-accused group, not the least. Do not tell a reader this tool is biased against non-native writers; it is biased against good writing. (The commercial-detector finding — 61.3% false positives on non-native TOEFL essays, Liang et al., *Patterns* 2023 — is still true of the field, and of this package's own optional model-based detectors.)
4. **Register contamination is real.** Someone who reads model output all day starts writing like it, unassisted.
5. **No detector survives a motivated adversary**, and that is a proven result, not a gap in current tooling (Sadasivan et al., arXiv:2303.11156).

So: **never produce a percentage**, never say "this was AI-generated", and never hand someone a result to confront a third party with. Say what fired, where, and how much it weighs. If the question behind the request is really "did my colleague use AI", the answer that helps is *ask them*, and say so.

## Which task is this?

| The ask | Do this |
|---|---|
| "Which parts of this read as AI?" / "is this AI-written?" | the **ductus-gauge** skill — the full reading |
| "Check this before I send it" / "make it sound like me" | the **deslop** skill first; gauge after, to check the rewrite |
| "Just give me a quick look" | `ductus gauge <file>` and report the segments that fired |
| "What does it actually look for?" | `ductus tells` and `ductus detectors` |

## The quick pass

```bash
ductus gauge draft.md                          # markdown diagnosis on stdout
ductus gauge draft.md --format html --out report.html
ductus gauge - --format json < draft.md        # machine-readable
ductus tells --tier E                          # near-certain patterns only
```

The deterministic pass costs nothing and needs no key. **It finds phrases, mechanical artifacts and a few sentence shapes. It does not find prose that is machine-written and bland** — for that you have to read, which is what `ductus-gauge` is for.

## Reading the output

- `lean` runs from **-1 (all evidence argues human)** to **+1 (all argues machine)**. It is a ratio of the weights present, not a probability.
- `strength` is how much evidence there was at all. **A lean of +1.00 at strength 0.15 is one weak signal, not a finding.** Always read the two together.
- Signals with direction `human` are as important as `machine` ones. A hard line break mid-sentence, mixed straight-and-curly apostrophes, a missing final period — models do not produce these, and they are often the most decisive thing in the file.
- Zero findings is a real result and a weak one. Say so rather than reporting "clean".

## What tends to be true, when it is true

The pattern worth looking for is not "which sentences are flagged" but **what kind of sentence is flagged**. In mixed-authorship text the machine-leaning passages are usually the ones that *generalise* — naming a pattern, stating a principle, managing a relationship — while the human-leaning ones are the *specific* ones: a number someone measured, a named person, a particular grievance. When you see that split, say it. It is more informative than any score.

## Never

- Give a percentage, a confidence, or a verdict about a person.
- Report a document-level number without saying which segments drove it.
- Use this to help someone evade detection. The package exists to describe text, and its sibling `deslop` exists to make writing *good*, not to launder it.
