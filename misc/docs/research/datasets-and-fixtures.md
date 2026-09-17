# Datasets and benchmarks with known human/AI text boundaries

Research date: 2026-09-17. Scope: publicly downloadable datasets where the exact point (or spans) where authorship switches from human to AI is labeled, for building test fixtures for a Python library that scores *which parts* of a text look machine-written.

## 1. Summary table

| Dataset | Identifier | Granularity | Size | Generators | License / vendor-safe? | Load (3 lines) |
|---|---|---|---|---|---|---|
| **RoFT** | HF `liamdugan/roft`; also CSV at `seas.upenn.edu/~ldugan/roft.csv`; code `liamdugan/human-detection` | **Sentence-index boundary** (`true_boundary_index`, 0-9, out of 10 sentences) | 27.6k annotation rows over a smaller pool of ~1k generations (Recipes, Presidential Speeches, Short Stories, NYT) | GPT-2, GPT-2-XL, CTRL, GPT-3/finetuned variants | **MIT** — safe to vendor | `from datasets import load_dataset; d=load_dataset("liamdugan/roft")` |
| **M4GT-Bench** (Task 3) | GitHub `mbzuai-nlp/M4GT-Bench`, data on Google Drive (no HF card found) | Word-index boundary (single change point) | 5,676 + 1,000 examples/domain (essays, peer reviews) × generator | ChatGPT, GPT-4, LLaMA-2 7B/13B/70B | Not explicitly stated; underlying essay/review corpora (student essays, PeerRead) carry their own restrictions — **check before vendoring, likely research-use only** | no clean `load_dataset` path — must pull the Drive folder |
| **M4 / SemEval-2024 Task 8 (subtask C)** | HF `d0rj/SemEval2024-task8`; official `mbzuai-nlp/SemEval2024-task8`, `mbzuai-nlp/M4` | Token/word-index boundary (regression target, MAE-scored) | Subtask C corpus derived from M4 (multi-domain, multi-lingual) | ChatGPT, GPT-4, Cohere, Davinci, Dolly, LLaMA | Mixed — M4 aggregates from Reddit/Wikipedia/WikiHow/arXiv/news with source-level licenses; **audit per-source before vendoring** | `from datasets import load_dataset; d=load_dataset("d0rj/SemEval2024-task8")` |
| **MixSet** | HF `ONE-Lab/MixSet`; code `Dongping-Chen/MixSet` | Document-pair only (`original`/`revised`), **no span offsets** | 3.6k rows (3,000 train + 600 test), 519 unique source texts | GPT-4, GPT-3.5, Llama-2, and 3 more (6 total) | No explicit license posted — **treat as all-rights-reserved until clarified** | `from datasets import load_dataset; d=load_dataset("ONE-Lab/MixSet")` |
| **Beemo** | HF `toloka/beemo`; code `Toloka/beemo` | Document-pair (`model_output` vs `human_edits`/LLM-edits), no offsets | 2,187 rows (6.5k human + 13.1k machine/edited texts total) | 10 open-weight instruction-tuned LLMs (Llama-3.1-70B, etc.) + GPT-4o edits | **Mixed**: prompts/human text CC-BY-NC-4.0 (from No Robots), machine outputs inherit each LLM's license, expert edits MIT — **NC clause blocks commercial vendoring of the human/prompt half** | `from datasets import load_dataset; d=load_dataset("toloka/beemo")` |
| **CoAuthor** | `coauthor.stanford.edu`; interface code `minalee-research/coauthor-interface` | **Keystroke-level provenance** (every keystroke timestamped and attributable to human or GPT-3 suggestion) | 1,445 sessions (830 stories + 615 essays), 63 writers × 4 GPT-3 configs | GPT-3 (davinci) | Research-only release terms on the site (not a standard OSI license) — **check terms before vendoring; likely non-commercial/research** | not `datasets`-library native; download JSONL from the site and parse events |
| **LLM-DetectAIve** | GitHub `mbzuai-nlp/LLM-DetectAIve`, demo Space `raj-tomar001/MGT-New` | **Document-level**, 4-class (human / machine / machine-humanized / human-polished) | ~91k machine, ~104k humanized, ~108k polished (built on M4GT-Bench base of 79k human + 103k machine) | Llama3-8B/70B, Mixtral-8x7B, Gemma/Gemma2, GPT-4o, Gemini-1.5-pro, Mistral-7B | Not clearly posted on a HF dataset card — **verify before vendoring** | no clean HF dataset id found; use GitHub release files |
| **RAID** | HF `liamdugan/raid` | **Document-level only** (no internal boundary — pure vs pure) | ~10M docs / 7.42M rows main split, 16.7 GB | 11 LLMs (ChatGPT, GPT-4, GPT-2, GPT-3, Llama-chat, Mistral, MPT, Cohere) | **MIT** — safe to vendor | `from datasets import load_dataset; raid=load_dataset("liamdugan/raid")` |
| **HC3** | HF `Hello-SimpleAI/HC3` (+ `HC3-Chinese`) | Document-level, paired human vs ChatGPT answers to the same question | Tens of thousands of QA pairs across domains (medicine, finance, law, Reddit, Wikipedia) | ChatGPT | **CC-BY-SA** (or stricter, inherited from source datasets) — vendorable but **share-alike**: derivative data must carry the same license/attribution | `from datasets import load_dataset; d=load_dataset("Hello-SimpleAI/HC3","all")` |
| **GPABench2** | GitHub `liuzey/CheckGPT` | Document-level (human / GPT-written / GPT-completed / GPT-polished abstracts) | 2.8M samples across CS, Physics, Humanities & Social Sciences | GPT-3.5 (ChatGPT) | Not clearly stated on GitHub — **verify before vendoring** | no HF dataset id found; clone GitHub repo |
| **AuTexTification** | HF `symanto/autextification2023` | Document-level, EN+ES, 5 domains | 163k texts, 74.3 MB | BLOOM-1B1/3B/7B1, Babbage, Curie, text-davinci-003 | **CC-BY-NC-SA-4.0** — non-commercial, share-alike; **not safe for a permissively-licensed public repo without matching license** | `from datasets import load_dataset; d=load_dataset("symanto/autextification2023")` |
| **Kaggle "LLM – Detect AI Generated Text" / DAIGT** | Kaggle `competitions/llm-detect-ai-generated-text`; community mirror `thedrcat/daigt-v2-train-dataset` | Document-level (student essays, human vs multiple LLMs) | Official comp ~44k persuasive essays; DAIGT-v2 community mirror ~44.8k rows | GPT-3.5/4 family, open models (varies by mirror) | Kaggle competition data is typically usable for the competition and research per Kaggle's Competition Rules (not a blanket public license); community-uploaded mirrors on Kaggle default to CC0 unless stated otherwise — **verify the specific dataset page's license badge before vendoring** | `import kagglehub; path=kagglehub.dataset_download("thedrcat/daigt-v2-train-dataset")` |
| **LLMTrace** (2025) | HF `iitolstykh/LLMTrace_detection` (localization) + `iitolstykh/LLMTrace_classification` | **Character-level span offsets** (`ai_char_intervals`: list of `[start,end]`) for `mixed`-label docs | 79,342 rows (269 MB); EN + RU | Multiple modern proprietary + open LLMs | **Apache-2.0** — safe to vendor | `from datasets import load_dataset; d=load_dataset("iitolstykh/LLMTrace_detection")` |
| **OpAI-Bench** (2026) | GitHub `VILA-Lab/OpAI-Bench` | Document/sentence/token/span, **9 sequential revision snapshots** per source doc with full provenance at each granularity | Not yet on HF at time of writing | 5 edit operations × 4 domains | Check repo LICENSE file (not yet HF-hosted) | GitHub clone; no `datasets` one-liner yet |
| **ARB** (2026) | arXiv 2607.29539, code not yet HF-hosted | Document-level, 4 matched variants per source (HUMAN / Free-LLM / H2L / LLM2L) | 1,800 human sources × 4 generators | Llama-3.2-3B, Qwen2.5-7B, Mistral-7B, Gemma-2-9B | Built on XSum/WritingPrompts/OpenWebText — **inherits their licenses**, check before vendoring | not yet packaged for `datasets` |
| **DAMASHA** (2025) | arXiv 2512.04838 | Segmentation-based span attribution in adversarially mixed texts | Not yet located as a standalone public download | Multiple | Unconfirmed | Unconfirmed |

## 2. Detail notes on the items you asked me to specifically pin down

**RoFT.** Yes, fully downloadable — both as `liamdugan/roft` on the HF Hub and as a flat CSV. MIT-licensed. The dataset card exposes exactly the fields you want: `dataset` (genre: Recipes / Presidential Speeches / Short Stories / New York Times), `model` (generator), `prompt_body`/`gen_body` (the actual text), and — critically — `true_boundary_index`, an integer 0-9 naming which of the 10 sentences is the first machine-generated one. `predicted_boundary_index` is the human annotator's guess (useful as a difficulty signal, not ground truth). This is the single dataset in this list purpose-built around "one document, one known switch point, human-annotated for difficulty."

**M4GT-Bench Task 3 / M4 / SemEval-2024 Task 8 subtask C.** These three are the same lineage: M4 (the base multi-generator/multi-domain/multi-lingual corpus) → SemEval-2024 Task 8 (shared task split of M4, subtask C = boundary detection, evaluated by mean absolute error between predicted and true switch-word index) → M4GT-Bench (a later, cleaner benchmark repackaging with its own Task 3 for the same boundary problem, built on academic essays and peer reviews with 0–50% human-written prefix). The M4/M4GT-Bench data is distributed via GitHub + a Google Drive folder rather than a clean `datasets`-library card, and it inherits licensing from its component corpora (OUTFOX student essays, PeerRead reviews, Reddit, WikiHow, Wikipedia, arXiv) — some of those are research-use-only, so this family is not a drop-in "safe to vendor" pick even though it's public and free to download. The SemEval-2024 Task 8 mirror `d0rj/SemEval2024-task8` on HF is the most convenient loading path.

**MixSet.** Confirmed downloadable at `ONE-Lab/MixSet` on HF and `Dongping-Chen/MixSet` on GitHub. It is explicitly *not* a naive-concatenation dataset — it models "mixtext" via five operations (AI: polish/complete/rewrite; human: adapt/humanize) rather than a clean two-segment splice, so it has **no span/offset field at all**, only paired `original`/`revised` full texts. Useful for realism, not for offset-based fixtures.

**Beemo.** Confirmed at `toloka/beemo`. Designed for "detector fooled by expert editing" evaluation, not boundary localization — again, whole-text pairs (`model_output` vs `human_edits`), no in-text spans. Mixed license (No Robots' CC-BY-NC-4.0 underlies the human/prompt half), so commercial-safe vendoring is blocked by the NC clause even though it's public.

**CoAuthor.** Hosted at coauthor.stanford.edu, not on HF/Kaggle. Its distinguishing feature is keystroke-level event logs, so you can, in principle, derive exact character provenance (every inserted/accepted span is tagged as human-typed vs GPT-3 suggestion) — richer than any of the sentence/word-boundary corpora above, but it requires you to reconstruct the final text from the event stream yourself, and the license on the site is research-terms rather than a standard permissive license.

**LLM-DetectAIve.** Confirmed as a real 4-class scheme (human / machine / machine-then-humanized / human-then-polished), built by extending M4GT-Bench. I could not find a clean standalone HF *dataset* card (only a HF *Space* demo and the GitHub repo) — data licensing needs verification before use, and like M4GT-Bench it inherits mixed-provenance source text.

## 3. RAID, HC3, GPABench2, AuTexTification, Kaggle/DAIGT

All five are confirmed real and downloadable (table above has exact ids/licenses). None of them label an internal boundary — they are pure-human vs pure-machine document pairs, useful for whole-document baselines but not directly for span/offset fixtures. RAID is the most rigorously licensed (MIT) and largest; HC3 is CC-BY-SA (share-alike, attribution required); AuTexTification is CC-BY-NC-SA (blocks commercial vendoring); GPABench2 and the Kaggle DAIGT mirrors have unclear or per-uploader licensing that must be checked per dataset page.

## 4. What's new for 2025-2026 on span-level / partial-authorship detection

- **LLMTrace** (Sept 2025) is the first dataset I found that gives **explicit character-level intervals** for AI-generated spans inside mixed-authorship documents, released as two Apache-2.0 HF datasets (`iitolstykh/LLMTrace_classification`, `iitolstykh/LLMTrace_detection`). This is the most direct match to "exact character offsets" of anything surveyed.
- **OpAI-Bench** (Jun 2026, `VILA-Lab/OpAI-Bench`) reframes the problem as *progressive* human→AI revision: nine snapshots per document under controlled AI-coverage levels and five edit operations, with full provenance at document/sentence/token/span granularity — built specifically to avoid the "single abrupt splice" artifact (see §6).
- **ARB** (Jul 2026, arXiv 2607.29539) is a matched-variant benchmark (human / free-LLM continuation / LLM-rewrite-of-human / LLM-rewrite-of-LLM) purpose-built to test whether rewriting/paraphrase degrades detectors relative to naive generation — directly relevant evidence for the splice-detectability question below.
- **DAMASHA** (arXiv 2512.04838) and **HACo-det** address segmentation-based attribution and fine-grained human-AI-coauthoring detection respectively; both are very recent (late 2025/2026) and I could not confirm a stable public download for either as of this search — treat as "watch, not yet usable."
- **Span-level detection of AI-generated scientific text via contrastive learning and structural calibration** (arXiv 2510.00890 / ScienceDirect 2025) is a methods paper, not primarily a new dataset release.

## 5. Which ONE dataset for a tiny (10-30 doc) public fixture with exact character offsets?

**Primary recommendation: RoFT (`liamdugan/roft`, MIT).** It is small, mature, extremely well-documented, and its boundary label is already a clean integer per document — you don't need clever parsing logic, and the MIT license means you can vendor a 10-30 row slice into your repo outright, including the raw text.

Loading and offset recovery:

```python
from datasets import load_dataset
import nltk  # or your own sentence splitter — RoFT sentences are pre-segmented

ds = load_dataset("liamdugan/roft", split="train")
# pick a small, license-clean slice: dedupe by (dataset, model) and keep the first N
sample = ds.filter(lambda r: r["true_boundary_index"] is not None).select(range(20))

def recover_char_offset(row):
    full_text = row["prompt_body"] + row["gen_body"]     # reconstruct full doc
    sentences = nltk.sent_tokenize(full_text)              # 10 sentences per RoFT design
    boundary_sentence_idx = row["true_boundary_index"]
    human_part = " ".join(sentences[:boundary_sentence_idx])
    char_offset = len(human_part)                          # everything after this = AI
    return char_offset
```

Because each RoFT document is exactly 10 sentences with a single, human-annotated switch point, character offsets fall right out of a sentence tokenizer — no fuzzy alignment needed. It also gives you a *difficulty* axis for free (`points`, `reason` — grammar/repetition/common-sense/contradicts-knowledge), useful for building both "easy" and "hard" fixture tiers.

**Strong secondary/complement: LLMTrace (`iitolstykh/LLMTrace_detection`, Apache-2.0).** If you want offsets with *zero* reconstruction (they're stored directly as `ai_char_intervals`), and don't mind a much newer, less battle-tested resource, filter `label == "mixed"` and take the first 10-30 rows:

```python
from datasets import load_dataset
ds = load_dataset("iitolstykh/LLMTrace_detection", split="test")
mixed = ds.filter(lambda r: r["label"] == "mixed").select(range(20))
# mixed[i]["ai_char_intervals"] is already [[start, end], ...] into mixed[i]["text"]
```

I'd ship RoFT as the default fixture generator (maturity, citation trail, trivial license) and keep LLMTrace as a second fixture set to validate against a differently-shaped ground truth (multiple spans vs single boundary, bilingual).

## 6. Is there a license-clean way to construct fixtures ourselves?

Yes, and it's a reasonable fallback or supplement, but it has real, well-documented pitfalls.

**The clean-license recipe:** take public-domain human text — Project Gutenberg (pre-1929 US works, or explicitly PD-marked later ones), U.S. federal government publications (public domain by statute, 17 U.S.C. §105), or CC0-licensed sources — and splice in your own LLM continuation, generated under your own account so the *output* carries whatever license your model provider's terms grant you (OpenAI/Anthropic/etc. generally grant you ownership/no-claim on outputs; still worth reading the specific provider ToS before committing to a public repo). Avoid Wikipedia/Wikidata for this purpose unless you're fine with CC-BY-SA's share-alike/attribution obligations spreading to your fixture data directory — that's a common trap for an otherwise-MIT-licensed repo.

**Pitfalls, with the literature that documents them:**

1. **Domain/register mismatch is a giveaway, not a genuine detection signal.** Splicing a modern instruct-tuned LLM's continuation onto 19th-century Gutenberg prose creates a stylistic cliff (vocabulary, syntax, discourse markers) that any detector — or even a naive perplexity threshold — picks up instantly, for the wrong reason. This is exactly the concern MixSet's authors raise in motivating revision-based operations (polish/rewrite/complete) instead of blunt generate-and-concatenate splices [7].
2. **The seam itself is trivially detectable when the LLM is only given the last few tokens of context.** RoFT's own analysis found strong genre and "reason" effects (irrelevance, repetition, common-sense violations, knowledge contradictions) precisely because short-context continuations drift semantically from the human prefix — see the RoFT paper [1] and the follow-up "AI-generated text boundary detection with RoFT" [2], which studies exactly this seam-detectability question.
3. **Naive concatenation over-represents an unrealistic threat model.** ARB (2026) explicitly separates "Free-LLM" (raw continuation — easy, high-seam-signal) from "H2L"/"LLM2L" (LLM rewriting of existing text) to show detector performance degrades substantially once you move past naive splicing to realistic rewriting [12]. If your fixtures are only naive splices, they'll systematically overstate how well a "scores which parts look machine-written" tool performs on real-world mixed text.
4. **Progressive/partial edits are harder than single abrupt splices, and non-monotonic.** OpAI-Bench (2026) found that intermediate, partially-revised documents are often *harder* to localize than either pure endpoint — a single 50/50 splice is not representative of the hardest real cases (light polishing, incremental co-writing) [13].
5. **Frequent authorship alternation and human post-editing blur the boundary further.** The hybrid-text detection paper built on CoAuthor logs [11] shows that once a human edits/selects AI suggestions (rather than accepting a block verbatim), segment-level classification degrades because segments get short and stylistically diluted — worth modeling if your library is meant for realistic co-writing, not just prompt-then-generate splices.

**Practical mitigations if you build your own splices:**
- Feed the LLM substantial context (a full paragraph or more, not just the last sentence) and prompt it to continue in-register ("continue in the same style, period, and vocabulary as the preceding text") to reduce the register cliff.
- Prefer instruct models with an explicit style-matching system prompt over base-model raw continuation, and sample several candidates, discarding ones with cliché discourse markers ("Furthermore," "In conclusion," "It is important to note") that are themselves a shortcut tell unrelated to your intended signal.
- Consider also generating "polish"/"lightly-edited" variants (à la MixSet/Beemo) alongside pure splices, so your fixture set spans the difficulty range MixSet and OpAI-Bench show matters, rather than only the easiest, most detectable case.
- Sanity-check your synthetic splices with an existing detector (Binoculars, DetectGPT, or even a simple perplexity curve) before shipping them as fixtures — if the ground-truth boundary is trivially the single sharpest perplexity cliff in the whole document, you've built an easy fixture, which is fine for a smoke test but should be labeled as such and not your only fixture tier.

## REFERENCES

[1] [Dugan L, Ippolito D, Kirubarajan A, Shi S, Callison-Burch C. Real or Fake Text?: Investigating Human Ability to Detect Boundaries Between Human-Written and Machine-Generated Text. AAAI 2023.](https://arxiv.org/abs/2212.12672)

[2] [AI-generated text boundary detection with RoFT.](https://arxiv.org/pdf/2311.08349)

[3] [Dataset: RoFT (liamdugan/roft), Hugging Face.](https://huggingface.co/datasets/liamdugan/roft)

[4] [Code: liamdugan/human-detection, GitHub.](https://github.com/liamdugan/human-detection)

[5] [Su J, et al. M4GT-Bench: Evaluation Benchmark for Black-Box Machine-Generated Text Detection. ACL 2024.](https://arxiv.org/abs/2402.11175)

[6] [Repository: mbzuai-nlp/M4GT-Bench, GitHub.](https://github.com/mbzuai-nlp/M4GT-Bench)

[7] [Chen D, et al. LLM-as-a-Coauthor: Can Mixed Human-Written and Machine-Generated Text Be Detected? NAACL Findings 2024.](https://aclanthology.org/2024.findings-naacl.29/)

[8] [Dataset: ONE-Lab/MixSet, Hugging Face.](https://huggingface.co/datasets/ONE-Lab/MixSet)

[9] [Toloka AI. Beemo: Benchmark of Expert-edited Machine-generated Outputs. NAACL 2025.](https://arxiv.org/abs/2411.04032)

[10] [Dataset: toloka/beemo, Hugging Face.](https://huggingface.co/datasets/toloka/beemo)

[11] [Towards Detecting AI-Generated Text within Human-AI Collaborative Hybrid Texts.](https://arxiv.org/abs/2403.03506)

[12] [Perrone G, Romano SP. ARB: A Matched Authorship-Rewriting Benchmark Dataset for AI-Text Detector Evaluation.](https://arxiv.org/abs/2607.29539)

[13] [OpAI-Bench: Operation-Guided Progressive Human-to-AI Text Transformation Benchmark for Multi-Granularity AI-Text Detection.](https://arxiv.org/abs/2606.06481)

[14] [Repository: VILA-Lab/OpAI-Bench, GitHub.](https://github.com/VILA-Lab/OpAI-Bench)

[15] [Lee M, Liang P, Yang Q. CoAuthor: Designing a Human-AI Collaborative Writing Dataset for Exploring Language Model Capabilities. CHI 2022.](https://arxiv.org/abs/2201.06796)

[16] [CoAuthor dataset and interface, Stanford.](https://coauthor.stanford.edu)

[17] [LLM-DetectAIve: a Tool for Fine-Grained Machine-Generated Text Detection. EMNLP Demo 2024.](https://arxiv.org/abs/2408.04284)

[18] [Repository: mbzuai-nlp/LLM-DetectAIve, GitHub.](https://github.com/mbzuai-nlp/LLM-DetectAIve)

[19] [Dugan L, Hwang A, Trhlík F, Zhu A, Ludan JM, Xu H, Ippolito D, Callison-Burch C. RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors. ACL 2024.](https://arxiv.org/abs/2405.07940)

[20] [Dataset: liamdugan/raid, Hugging Face.](https://huggingface.co/datasets/liamdugan/raid)

[21] [Guo B, et al. How Close is ChatGPT to Human Experts? Comparison Corpus, Evaluation, and Detection (HC3).](https://github.com/Hello-SimpleAI/chatgpt-comparison-detection)

[22] [Dataset: Hello-SimpleAI/HC3, Hugging Face.](https://huggingface.co/datasets/Hello-SimpleAI/HC3)

[23] [Liu Z, et al. On the Detectability of ChatGPT Content: Benchmarking, Methodology, and Evaluation through the Lens of Academic Writing (GPABench2 / CheckGPT). ACM CCS 2024.](https://arxiv.org/abs/2306.05524)

[24] [Repository: liuzey/CheckGPT, GitHub.](https://github.com/liuzey/CheckGPT)

[25] [Sarvazyan AM, et al. Overview of AuTexTification at IberLEF 2023: Detection and Attribution of Machine-Generated Text in Multiple Domains.](https://arxiv.org/abs/2309.11285)

[26] [Dataset: symanto/autextification2023, Hugging Face.](https://huggingface.co/datasets/symanto/autextification2023)

[27] [Kaggle competition: LLM - Detect AI Generated Text.](https://www.kaggle.com/competitions/llm-detect-ai-generated-text)

[28] [Kaggle dataset: DAIGT V2 Train Dataset (thedrcat).](https://www.kaggle.com/datasets/thedrcat/daigt-v2-train-dataset)

[29] [LLMTrace: A Corpus for Classification and Fine-Grained Localization of AI-Written Text.](https://arxiv.org/abs/2509.21269)

[30] [Dataset: iitolstykh/LLMTrace_detection, Hugging Face.](https://huggingface.co/datasets/iitolstykh/LLMTrace_detection)

[31] [Dataset: iitolstykh/LLMTrace_classification, Hugging Face.](https://huggingface.co/datasets/iitolstykh/LLMTrace_classification)

[32] [d0rj/SemEval2024-task8 mirror, Hugging Face.](https://huggingface.co/datasets/d0rj/SemEval2024-task8)

[33] [Wang Y, et al. M4: Multi-generator, Multi-domain, and Multi-lingual Black-Box Machine-Generated Text Detection. EACL 2024.](https://arxiv.org/abs/2305.14902)

[34] [Repository: mbzuai-nlp/M4, GitHub.](https://github.com/mbzuai-nlp/M4)
