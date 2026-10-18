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

### Several readers: when the question is "did this rewrite help?"

One reader is enough to describe a text. It is **not** enough to compare two versions of one: independent strict readers each flag dozens of shapes in a long text, mostly different ones, so a single reader's count moves with the reader, not the rewrite. Use at least two **cold** readers (fresh subagents that have not seen your own reading or each other's), and count only the sentences they agree on.

Spawn each reader with this prompt, one per output file (`essay.a.json`, `essay.b.json`, ...):

```text
You are a close reader. Read the ductus-gauge skill (the Pass 2 tables only), then read
<FILE> in full, cold. You have no stake in it. Do not read any other file beside it.

Find every passage that reads as machine-written prose, using the machine-leaning shapes
in that table, plus: "not X but Y" / "didn't X. It Y." constructions, colon-reveal lists,
signposting teasers, and summary closers that restate the section. Be strict, but do not
flag things just for being well written. Lists of cited names, code, and image alt text
are not findings. Record the human-leaning shapes too.

Write a JSON list to <OUT>. Each finding is {"quote": "<exact verbatim substring, 6-40
words>", "direction": "machine"|"human", "name": "<kebab-case shape>", "weight": <from the
table>, "note": "<one line>"}. Quotes must match the file exactly (check with grep -F).
Do not edit the text.
```

Then:

```bash
ductus gauge essay.md --judgments essay.a.json --judgments essay.b.json          # -k 2 is the default
ductus baseline old-1.md old-2.md --out baseline.json   # the same readers' prompt, on the author's own earlier writing
ductus gauge essay.md --judgments essay.a.json --judgments essay.b.json --baseline baseline.json
```

The report's **Readers** section gives each reader's count and the consensus per 1,000 words. Report the consensus **next to the baseline**, never alone, and give the baseline's per-text range — reference texts by one author vary a lot. Use the same number of readers and the same `k` for the text and its baseline; the report flags it when they differ. Keep reference texts and their judgment files where the source lives, never in a repository.

## Pass 3 — the write-up

Lead with **what kind of passage** carries which signal, not with the number. The useful sentence is usually of the form *"the passages that generalise carry the machine signal; the specific ones carry typing artifacts"*, because that describes a **process** — someone wrote their own material and reached for help framing it — rather than pronouncing on a person.

Then, in order:

1. The strongest **mechanical** evidence (artifacts, seams, slips). It is the hardest to fake in either direction and should be weighted accordingly.
2. The strongest **rhetorical** evidence, quoted. With several readers, quote the consensus sentences, and give the consensus density beside the author's baseline — never a bare density.
3. What is **ambiguous**, said plainly. Consistent curly apostrophes mean the text was composed outside the channel it was sent in; they say nothing about who composed it.
4. The **limits** from the `ductus` skill — at least the editing confound and this tool's own measured false-positive rate (6% of human-written documents; 0.4–2% per sentence, and about 10% for intermediate and advanced non-native writers), including that its bias runs toward *formal, fluent* writing rather than simple writing.
5. **What would actually settle it**, which is almost never more detection. Usually: a sample of the same author's earlier writing to compare against, or asking them.

## If the text is private

Keep every artifact out of any repository and out of any external service. Write reports beside the source file, not into a project directory. Quote the text only in files that live where the source does.
