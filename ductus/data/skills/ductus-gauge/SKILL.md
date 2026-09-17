---
name: ductus-gauge
description: Do a full reading of a text for machine-written prose — run the deterministic detectors, add your own judgment pass for the shapes a regular expression cannot see, and produce a markdown or HTML report with evidence anchored to exact characters. Use when asked which parts of a text read as AI-generated, to analyse or diagnose a document's authorship signals, to check a draft before sending, or to verify a rewrite. Triggers on "which parts sound like AI", "analyse this text", "gauge this", "is this AI-written", "run the detectors", "AI reading of this document", "check this draft". Read the `ductus` skill first for what may and may not be claimed.
metadata:
  audience: users
---

# ductus-gauge — the full reading

Three passes. The first is free, the second is the one that matters, the third is the write-up. **Read the `ductus` skill's limits section before reporting anything.**

## Pass 1 — the deterministic scan

```bash
ductus gauge <file> --format json --out /tmp/ductus-scan.json
ductus gauge <file>          # the same scan, as readable markdown
```

Read what fired and where. This pass finds catalogue phrases, typographic artifacts, a few sentence shapes, and sentence-length variance. **Expect it to find nothing on careful text. That is not evidence of human authorship** — it is the limit of regular expressions.

## Pass 2 — your own reading (this is the valuable one)

Read the text yourself and look for the shapes below. For each one you find, record a judgment. Quote exactly — the quote is how it gets anchored.

### Machine-leaning shapes

| Shape | What it looks like | Weight |
|---|---|---|
| **Pattern-naming tricolon** | Names a behaviour, then unrolls it as three parallel clauses: "This is a recurring pattern: you decide X, invest Y, and then get frustrated when Z." | 0.5 |
| **Principle generalisation** | Lifts a specific complaint into a balanced maxim: "Time spent can't by itself be a measure of value." | 0.45 |
| **Aphoristic closer** | A one-sentence moral capping a paragraph that did not need one. | 0.4 |
| **Concede-then-pivot** | "I do value X. At the same time, Y." The diplomatic-feedback move. | 0.35 |
| **Term reversal** | Takes the other party's own word and turns it back neatly in the closing clause. | 0.35 |
| **False balance** | "While X has benefits, it also has drawbacks" where the author plainly holds a view. | 0.35 |
| **Uniform paragraph architecture** | Every paragraph the same length, same shape, same one-point-then-elaborate rhythm. | 0.3 |
| **Reassurance pair** | Two short declaratives doing emotional management mid-argument: "Software is difficult and review is normal." | 0.3 |
| **Over-explanation** | More words than the facts need; uniformly perfect formality in a casual channel. | 0.25 |

### Human-leaning shapes (look as hard for these)

| Shape | What it looks like | Weight |
|---|---|---|
| **Typing and paste artifacts** | A hard line break mid-sentence, a doubled word, trailing whitespace, a missing final period. | 0.45 |
| **Insertion seams** | Paragraph separation that is inconsistent — three joins missing the blank line the rest of the document uses. Marks where text was added in a later pass. | 0.4 |
| **L2 grammar slips** | Article, countability or preposition errors ("it's always a team work"). Models essentially never emit these. | 0.6 |
| **Unhedged specificity** | A named person, a measured number, an unglossed particular, with no scaffolding around it. | 0.3 |
| **Absent habits** | Zero em dashes across a long reflective text; no bullet lists where a model would reach for one. | 0.35 |
| **Cost-bearing opinion** | A claim the author would have to defend, stated without balancing it. | 0.3 |

Write them to a file:

```json
[
  {"quote": "exact text from the document",
   "direction": "machine",
   "name": "pattern-naming-tricolon",
   "weight": 0.5,
   "note": "Names a pattern, then three parallel verb phrases."},
  {"quote": "it's always a team work",
   "direction": "human",
   "name": "l2-grammar-slip",
   "weight": 0.6,
   "note": "Article and countability error; models do not produce this."}
]
```

Then fold it in:

```bash
ductus gauge <file> --judgments judgments.json --format html --out report.html
ductus gauge <file> --judgments judgments.json --out reading.md
```

A quote that no longer occurs in the text is dropped rather than mis-anchored, so re-running after an edit is safe.

## Pass 3 — the write-up

Lead with **what kind of passage** carries which signal, not with the number. The useful sentence is usually of the form *"the passages that generalise carry the machine signal; the specific ones carry typing artifacts"*, because that describes a **process** — someone wrote their own material and reached for help framing it — rather than pronouncing on a person.

Then, in order:

1. The strongest **mechanical** evidence (artifacts, seams, slips). It is the hardest to fake in either direction and should be weighted accordingly.
2. The strongest **rhetorical** evidence, quoted.
3. What is **ambiguous**, said plainly. Consistent curly apostrophes mean the text was composed outside the channel it was sent in; they say nothing about who composed it.
4. The **limits** from the `ductus` skill — at least the editing confound and this tool's own measured false-positive rate (20.6% of human-written documents; 2–3% per sentence), including that its bias runs toward *formal, fluent* writing rather than simple writing.
5. **What would actually settle it**, which is almost never more detection. Usually: a sample of the same author's earlier writing to compare against, or asking them.

## If the text is private

Keep every artifact out of any repository and out of any external service. Write reports beside the source file, not into a project directory. Quote the text only in files that live where the source does.
