# Detecting AI-Generated Text: State of the Art (2026)

## Comparison table

| Method | Needs | Granularity | Python entry point | License | Notes |
|---|---|---|---|---|---|
| **Log-likelihood / perplexity threshold** | White-box logits from the suspected model, or any proxy LM | Document (extendable to per-token) | Any HF `AutoModelForCausalLM` + `torch` — no dedicated package | N/A (technique, not a package) | Baseline in almost every paper below; weak alone, easily beaten by paraphrase, biased toward flagging simple/non-native prose [1,15] |
| **GLTR** (rank/entropy visualization) | White-box or proxy LM (orig. GPT-2) | Token (visual), rollup to document | [github.com/HendrikStrobelt/detecting-fake-text](https://github.com/HendrikStrobelt/detecting-fake-text) | MIT | 2019, MIT-IBM/HarvardNLP; a *human-in-the-loop* visualizer, not a classifier — colors tokens by predicted rank/entropy [2] |
| **DetectGPT** | White-box log-probs of the target LM + a mask-infill model (e.g. T5) for perturbations | Document | [github.com/eric-mitchell/detect-gpt](https://github.com/eric-mitchell/detect-gpt); arXiv 2301.11305 | MIT | Perturb→score→compare probability curvature; no training needed but ~100 perturbations per doc = slow, and needs the *generating* model's logits for best results [3,4] |
| **Fast-DetectGPT** | Same signal as DetectGPT but only 1 sampling pass; works with a smaller open proxy (e.g. GPT-Neo/GPT-J) as "sampling model" | Document | [github.com/baoguangsheng/fast-detect-gpt](https://github.com/baoguangsheng/fast-detect-gpt); arXiv 2310.05130 | MIT | Conditional probability curvature; ~340× faster than DetectGPT, +75% relative AUROC; works black-box (surrogate model) too [5,6] |
| **DetectLLM (LRR / NPR)** | White-box logits (LRR: log-likelihood/log-rank ratio, cheap) or + perturbation model (NPR, slower) | Document | [github.com/mbzuai-nlp/DetectLLM](https://github.com/mbzuai-nlp/DetectLLM); arXiv 2306.05540 | MIT | LRR is a single forward pass, no perturbation model — the cheapest zero-shot score in this family [7] |
| **Binoculars** | Two off-the-shelf open LMs (observer + performer, e.g. Falcon-7B / Falcon-7B-Instruct) — **not** the actual generator | Document (per-sentence in the HF Space demo) | [github.com/ahans30/Binoculars](https://github.com/ahans30/Binoculars); `pip install -e .` from clone; arXiv 2401.12070 | BSD-3-Clause | Ratio of perplexity to cross-perplexity between a paired observer/performer LM; ICML 2024; near-zero-shot generalization across generators (works without knowing which LLM wrote the text), reported ~0.92–0.98 AUROC on standard sets, lower (~0.74) on adversarial RAID [8,9,10] |
| **Lastde / Lastde++** | White-box or proxy-model token-probability sequence | Document | [github.com/TrustMedia-zju/Lastde_Detector](https://github.com/TrustMedia-zju/Lastde_Detector); arXiv 2410.06072 (ICLR 2025) | MIT | Treats token-probability sequence as a time series, scores via multiscale diversity entropy; training-free, matches/exceeds Fast-DetectGPT in black-box setting [11] |
| **RADAR** | GPU + pretrained RoBERTa-large classifier fine-tuned adversarially against a paraphraser | Document | [huggingface.co/TrustSafeAI/RADAR-Vicuna-7B](https://huggingface.co/TrustSafeAI/RADAR-Vicuna-7B) (`transformers`); arXiv 2307.03838 | Non-commercial only | Supervised, but trained adversarially vs. a paraphraser for robustness; NeurIPS 2023 [12] |
| **OpenAI RoBERTa detector** (retired) | GPU, RoBERTa weights | Document | [huggingface.co/openai-community/roberta-base-openai-detector](https://huggingface.co/openai-community/roberta-base-openai-detector) | MIT | Detects GPT-2 only; OpenAI officially discontinued its own classifier tool in 2023 for low accuracy; weights still on HF but explicitly not fit for ChatGPT/GPT-4 or academic-misconduct use [13] |
| **Hello-SimpleAI chatgpt-detector-roberta** | GPU, RoBERTa-base | Document | [huggingface.co/Hello-SimpleAI/chatgpt-detector-roberta](https://huggingface.co/Hello-SimpleAI/chatgpt-detector-roberta) | Apache-2.0 | Trained on the HC3 human-vs-ChatGPT QA corpus; narrow domain (QA-style answers), degrades on other genres/newer models [14] |
| **desklib AI text detector** | GPU, DeBERTa-v3-large | Document | [huggingface.co/desklib/ai-text-detector-v1.01](https://huggingface.co/desklib/ai-text-detector-v1.01) and `-academic-v1.01` variant | Apache-2.0 | Currently tops the RAID leaderboard among open supervised models; academic variant tuned for essay-style text [16,17] |
| **MAGE** | GPU, Longformer-base | Document | [huggingface.co/yaful/MAGE](https://huggingface.co/yaful/MAGE); arXiv 2305.13242 | MIT | Trained on 27 LLMs × 10 domains "in the wild" benchmark; ~86.5% OOD accuracy on unseen LLMs; ACL 2024 [18] |
| **LLM-DetectAIve** | GPU, fine-grained 4-way classifier (human / machine / machine-humanized / human-polished) | Document | [github.com/mbzuai-nlp/LLM-DetectAIve](https://github.com/mbzuai-nlp/LLM-DetectAIve); HF Space `raj-tomar001/MGT-New`; arXiv 2408.04284 | MIT | Goes beyond binary: distinguishes "AI-polished human text" from pure human/AI; claims 97.5% binary accuracy, beating GPTZero/ZeroGPT/Sapling in their own eval [19] |
| **SeqXGPT** | White-box perplexity *lists* from several open LMs (GPT2-XL, GPT-Neo, GPT-J, LLaMA) as features + a CNN/self-attention head | **Sentence-level**, aggregable to document | [github.com/Jihuai-wpy/SeqXGPT](https://github.com/Jihuai-wpy/SeqXGPT); arXiv 2310.08903 | MIT | Purpose-built for sentence-level boundary/localization in mixed human+AI documents; treats logit sequences as a waveform [20] |
| **GPTZero** | API key (SaaS) | **Sentence-level** (per-sentence "burstiness"/perplexity highlighting) | REST API, `https://api.gptzero.me`; official docs | Proprietary | Vendor claims ≤1% FPR / 99.5% acc.; independent tests show 80–87% accuracy, 7–12% FPR on academic prose, and a Stanford-style non-native-English FPR problem persists in the family; ~$45.99/mo Pro incl. API [21,22,23] |
| **Originality.ai** | API key (SaaS) | Document + some span highlighting | REST API | Proprietary | Independent FPR 8–12% on human text generally, 15–18%+ on ESL/technical writing; vendor disputes the non-native bias framing [24] |
| **Pangram Labs** | API key (SaaS) | Document, span-level flags | REST API + Python SDK, `$0.05/1,000 words` | Proprietary | Best independently-validated numbers in the field: Pangram 4 reports AUROC 0.9916, FPR 0.0041%, FNR 0.34% on frontier models (Claude, GPT-5.x); third-party eval by U. Chicago/U. Maryland researchers cited [25,26] |
| **Winston AI** | API key (SaaS) | Sentence-level breakdown | REST API, `$0.015/1,000 words` | Proprietary | Percentage score + sentence-by-sentence flags [27] |
| **Sapling AI** | API key (SaaS) | Document + optional **per-sentence and per-token** scores | REST API, `sapling.ai/docs/api/detector` from `$0.005/1,000 chars` | Proprietary | One of the few commercial APIs that documents a genuine token-level response (`token_probs`) alongside `sentence_scores`, useful for boundary work [28] |
| **Copyleaks** | API key (SaaS) | **Sentence-level** AI-probability scores | REST API, `~$0.001/text` unit, enterprise tiers | Proprietary | Publishes 99%+ self-reported accuracy; independent tests ~9–11% FPR on ESL writing [29] |
| **ZeroGPT / Turnitin** | Web UI mainly; ZeroGPT has a nascent API, Turnitin is institution-licensed (no public API) | Document, Turnitin gives a percentage + highlighted spans in its LMS integration | No stable public Python SDK for either | Proprietary | Turnitin claims ~98% accuracy / <1% FPR at >20% AI-content threshold (vendor-reported, not independently replicated); over 50 universities have restricted or banned AI-detector use as of 2026 due to reliability concerns [30,31,32] |
| **SynthID-Text (Google DeepMind)** | Requires being the model provider (bias logits at generation time); open detector needs the provider's watermark config | Document, with per-token watermark strength internally | `pip install synthid-text` (PyPI) / [github.com/google-deepmind/synthid-text](https://github.com/google-deepmind/synthid-text); Dathathri et al., *Nature* 2024 | Apache-2.0 | Only detects text from models that were watermarked with the *same* key at generation time — i.e., practically, Gemini text only (or your own fine-tune if you adopt the scheme) [33,34] |
| **Kirchenbauer et al. green-list watermark** | Requires being the model provider (bias logits at generation) | Document/token (per-token green/red assignment) | [github.com/jwkirchenbauer/lm-watermarking](https://github.com/jwkirchenbauer/lm-watermarking); arXiv 2301.10226 | MIT | The foundational soft-watermark scheme; detection needs no model access, only the seeding scheme + hash key; broken by paraphrase attacks (TPR@1%FPR 99.8%→9.7%) [35,36] |
| **Unigram-Watermark** | Requires being the model provider | Document/token | [github.com/XuandongZhao/Unigram-Watermark](https://github.com/XuandongZhao/Unigram-Watermark); arXiv 2306.17439 | MIT | Fixed (not context-dependent) green/red partition — provably ~2× more robust to edits than Kirchenbauer's scheme; ICLR 2024 [37] |
| **Anthropic Claude watermark** | Requires being Anthropic; third parties get a detection API (private preview, Sept 2026) | Document (works less reliably on short/fact-heavy text) | No public Python client yet; REST API in private preview | Proprietary | Adopts the SynthID Text approach; rolled out for EU AI Act Article 50 compliance; all Claude models released after Aug 2, 2025 support it, older models retrofitted through late 2026 [38,39] |
| **OpenAI text watermark** | N/A | — | — | — | OpenAI has **not** shipped a public text watermark as of Sept 2026 (image/audio provenance signals exist, text does not) [39] |
| **Stylometric / feature-based (function words, burstiness, em-dash rate, POS n-grams, TTR)** | CPU only, no GPU, no API | Document, trivially extendable to sentence-level features | [pypi.org/project/stylo-metrix](https://pypi.org/project/stylo-metrix/) (`StyloMetrix`, multilingual); [github.com/craigtrim/pystylometry](https://github.com/craigtrim/pystylometry) (50+ metrics incl. AI-detection features); `textstat`, `lexicalrichness` for individual metrics | Apache-2.0 (StyloMetrix), varies | Non-neural signal, cheap and interpretable; burstiness (word-gap std/mean) and reduced sentence-length variance are the most consistently reported LLM tells; weak alone, useful as an ensemble feature or explainability layer [40,41,42] |
| **RAID benchmark/toolkit** | CPU for eval harness; models plugged in separately | Document | [github.com/liamdugan/raid](https://github.com/liamdugan/raid); `pip`-installable eval package; arXiv 2405.07940 | MIT | Not a detector itself — the standard 10M-document, 11-model, 12-adversarial-attack benchmark and leaderboard everything above gets scored against (ACL 2024) [43] |

## If I were building a Python library with pluggable detectors

In priority order, with the rationale for each slot:

1. **Fast-DetectGPT** (or its close cousin Binoculars) as the zero-shot default. Neither needs training data, an API key, or knowledge of the generating model; Fast-DetectGPT is the cheaper of the two (single forward pass) and posts the best RAID AUROC among training-free methods [5,9]. Ship it first because it's the only tier that works entirely offline with a small open proxy model (e.g., GPT-Neo-125M/1.3B on CPU-tolerable latency, or Falcon-7B pair on a single GPU).
2. **Binoculars** as a second zero-shot backend rather than an alternative to (1) — its observer/performer design generalizes better across *unseen* generators than single-model perplexity methods, which matters when you don't know if the input came from GPT, Claude, or Llama [8,10]. Having both lets an ensemble vote and gives users a CPU-cheap-vs-cross-generator-robust tradeoff.
3. **desklib's DeBERTa-v3 classifier** as the supervised backend — it's open-weight (Apache-2.0), sits at the top of the RAID leaderboard among free models, and gives a second, architecturally-independent signal (learned features vs. probability curvature) to combine with (1)/(2) [16,17].
4. **Sapling's API** as the first commercial adapter — of all the paid vendors it is the only one that documents a genuine token-level response (`token_probs`) in addition to sentence scores, which is exactly the shape a "pluggable detector" interface needs for per-span highlighting, and its pricing is transparent and cheap enough to default-enable [28].
5. **Pangram's API** as the "trust this one most" commercial adapter, gated behind an explicit opt-in/API key — its independently-audited FPR (per-10,000-documents) is an order of magnitude better than the rest of the commercial field, making it the right choice when a false accusation is costly (e.g., academic integrity use cases) [25,26].
6. **SeqXGPT-style sentence localization** as the boundary-detection module — none of 1–5 natively tell you *where* in a mixed document the AI text starts; wrapping SeqXGPT (or reproducing its per-token perplexity-waveform + linear-head approach over open proxy models) is the natural extension once document-level scoring works [20].
7. **A stylometric feature extractor (StyloMetrix or a custom burstiness/em-dash/TTR module)** as a cheap, explainable, no-GPU fallback and as auxiliary features for an ensemble/calibration layer — useful when GPU/API budget is zero and for generating human-readable "why we flagged this" explanations [40,41].
8. **RAID's evaluation harness** not as a runtime detector but as the CI/regression-testing backend — any pluggable-detector library needs a standard, adversarial benchmark to catch silent accuracy regressions when a new LLM ships; RAID is the field's de facto standard and ships as an installable Python package [43].

I would explicitly *not* wrap watermark detectors (SynthID/Kirchenbauer/Anthropic) as a general "detect AI text" backend — they only work when you also control (or trust) the generator's watermark key, which is a fundamentally different deployment model from the classifier/zero-shot stack above. They belong as an optional, clearly-labeled "watermark verification" mode, not the default path.

## Caveats to state in the README

- **No detector is reliable against a motivated adversary.** Sadasivan et al. prove a theoretical impossibility result: as an LLM's output distribution approaches the human text distribution, the AUROC of *any* best-possible detector approaches 0.5 (random), and they show empirically that a single paraphrasing pass collapses watermark TPR@1%FPR from 99.8% to 9.7% [15].
- **Paraphrase/"humanizer" tools are an effective, cheap attack today.** DIPPER dropped DetectGPT's accuracy from 70.3% to 4.6% without materially changing meaning; it also defeats GPTZero and OpenAI's retired classifier in the same study [36].
- **False positives disproportionately hit non-native English writers.** Liang et al. (Stanford, *Patterns* 2023) found a 61.3% average false-positive rate across seven commercial/academic detectors on TOEFL essays by non-native speakers, vs. near-zero on native-speaker control essays — the bias tracks reduced lexical/syntactic complexity, not actual AI use [23,15].
- **Vendor-reported accuracy and independent-evaluation accuracy routinely diverge by 10–20+ points.** E.g., GPTZero claims ≤1% FPR / 99.5% accuracy; independent studies find 80–87% accuracy and 7–12% FPR on academic prose [21,22].
- **Detectors degrade out-of-distribution against unseen models/domains.** Even the strongest open benchmark result (MAGE) tops out at ~86.5% accuracy on text from LLMs it wasn't trained on; RAID shows current detectors "easily fooled" by decoding-strategy or repetition-penalty changes alone [18,43].
- **Watermarking only certifies text from a cooperating, known generator.** SynthID/Anthropic's scheme cannot say anything about text from a different provider, cannot prove *how much* of a document was AI-authored (light edit vs. full generation), and is weaker on short or fact-constrained passages [33,38,39].
- **Zero-shot methods need the right proxy model, and results can be sensitive to that choice.** Binoculars' own ablations show performance depends on observer/performer being a *closely related pair* rather than an arbitrary strong/weak combination, and Fast-DetectGPT's black-box (surrogate-model) numbers trail its white-box numbers [8,5].
- **Institutions are walking back reliance on these tools.** Over 50 universities (MIT, Yale, Vanderbilt, UC Waterloo, others) have banned or discouraged AI-detector use as of 2026, citing the false-positive risk to students [22].
- **A single document-level score hides where the problem is.** Only a handful of methods (SeqXGPT, Sapling's token/sentence scores, Copyleaks' sentence scores, some SemEval-2024 Task 8 boundary-detection systems) attempt localization; most commercial and zero-shot tools still collapse a whole document to one number, which is a poor match for "who wrote which paragraph" questions [20,28,29,44].
- **Calibration and thresholds are dataset-specific and not portable.** Reported AUROC/accuracy numbers come from benchmark-specific operating points; deploying any of these with a fixed threshold on your own domain without re-calibrating will reproduce the FPR problems documented above [43,15].

## REFERENCES

[1] [GPT detectors are biased against non-native English writers](https://arxiv.org/pdf/2304.02819) — arXiv:2304.02819.

[2] [HendrikStrobelt/detecting-fake-text (GLTR)](https://github.com/HendrikStrobelt/detecting-fake-text) — GitHub.

[3] [DetectGPT: Zero-Shot Machine-Generated Text Detection using Probability Curvature](https://arxiv.org/abs/2301.11305) — arXiv:2301.11305.

[4] [eric-mitchell/detect-gpt](https://github.com/eric-mitchell/detect-gpt) — GitHub.

[5] [Fast-DetectGPT: Efficient Zero-Shot Detection of Machine-Generated Text via Conditional Probability Curvature](https://arxiv.org/abs/2310.05130) — arXiv:2310.05130 (ICLR 2024).

[6] [baoguangsheng/fast-detect-gpt](https://github.com/baoguangsheng/fast-detect-gpt) — GitHub.

[7] [DetectLLM: Leveraging Log Rank Information for Zero-Shot Detection of Machine-Generated Text](https://arxiv.org/abs/2306.05540) — arXiv:2306.05540; [mbzuai-nlp/DetectLLM](https://github.com/mbzuai-nlp/DetectLLM).

[8] [Spotting LLMs With Binoculars: Zero-Shot Detection of Machine-Generated Text](https://arxiv.org/abs/2401.12070) — arXiv:2401.12070 (ICML 2024).

[9] [ahans30/Binoculars](https://github.com/ahans30/Binoculars) — GitHub.

[10] [Spotting LLMs With Binoculars](https://weaviate.io/papers/paper24) — Weaviate paper summary.

[11] [Training-free LLM-generated Text Detection by Mining Token Probability Sequences (Lastde/Lastde++)](https://arxiv.org/html/2410.06072) — arXiv:2410.06072 (ICLR 2025); [TrustMedia-zju/Lastde_Detector](https://github.com/TrustMedia-zju/Lastde_Detector).

[12] [RADAR: Robust AI-Text Detection via Adversarial Learning](https://arxiv.org/abs/2307.03838) — arXiv:2307.03838; [TrustSafeAI/RADAR-Vicuna-7B](https://huggingface.co/TrustSafeAI/RADAR-Vicuna-7B).

[13] [openai-community/roberta-base-openai-detector](https://huggingface.co/openai-community/roberta-base-openai-detector) — Hugging Face.

[14] [Hello-SimpleAI/chatgpt-detector-roberta](https://huggingface.co/Hello-SimpleAI/chatgpt-detector-roberta) — Hugging Face.

[15] [Can AI-Generated Text be Reliably Detected?](https://arxiv.org/abs/2303.11156) — Sadasivan et al., arXiv:2303.11156.

[16] [desklib/ai-text-detector-v1.01](https://huggingface.co/desklib/ai-text-detector-v1.01) — Hugging Face.

[17] [desklib/ai-text-detector-academic-v1.01](https://huggingface.co/desklib/ai-text-detector-academic-v1.01) — Hugging Face.

[18] [MAGE: Machine-generated Text Detection in the Wild](https://arxiv.org/abs/2305.13242) — arXiv:2305.13242 (ACL 2024); [yaful/MAGE](https://huggingface.co/yaful/MAGE).

[19] [LLM-DetectAIve: a Tool for Fine-Grained Machine-Generated Text Detection](https://arxiv.org/html/2408.04284v2) — arXiv:2408.04284; [mbzuai-nlp/LLM-DetectAIve](https://github.com/mbzuai-nlp/LLM-DetectAIve).

[20] [SeqXGPT: Sentence-Level AI-Generated Text Detection](https://arxiv.org/pdf/2310.08903) — arXiv:2310.08903; [Jihuai-wpy/SeqXGPT](https://github.com/Jihuai-wpy/SeqXGPT).

[21] [How AI Detection Benchmarking Works at GPTZero (2025)](https://gptzero.me/news/ai-accuracy-benchmarking/) — GPTZero.

[22] [GPTZero Review 2026: Accuracy, Pricing, and Verdict](https://fast.io/resources/gptzero-ai-detector-review-2026/) — Fastio.

[23] [AI Detection Tools Falsely Accuse International Students of Cheating](https://themarkup.org/machine-learning/2023/08/14/ai-detection-tools-falsely-accuse-international-students-of-cheating) — The Markup (citing Liang et al., *Patterns* 2023).

[24] [Originality AI Review 2026: Accuracy, Pricing, and API](https://fast.io/resources/originality-ai-review/) — Fastio.

[25] [Technical Report on the Pangram AI-Generated Text Classifier](https://arxiv.org/pdf/2402.14873) — arXiv:2402.14873.

[26] [Pangram 4 Technical Report](https://arxiv.org/abs/2607.27183) — arXiv:2607.27183.

[27] [Winston AI Detector Review 2026: Accuracy and Pricing Tested](https://fast.io/resources/winston-ai-detector-review-2026/) — Fastio.

[28] [Sapling AI Detector API documentation](https://sapling.ai/docs/api/detector/) — Sapling.ai.

[29] [Copyleaks AI Checker Review 2026](https://fast.io/resources/copyleaks-ai-detector-review-2026/) — Fastio.

[30] [Turnitin AI Detection Accuracy 2026](https://www.tryleap.ai/turnitin/accuracy) — Leap AI.

[31] [ZeroGPT AI Detector](https://www.zerogpt.com/) — ZeroGPT.

[32] [AI Detector Accuracy: The False-Positive Evidence](https://casrai.org/guides/ai-detection-accuracy-higher-education) — CASRAI.

[33] [google-deepmind/synthid-text](https://github.com/google-deepmind/synthid-text) — GitHub.

[34] [SynthID: Tools for watermarking and detecting LLM-generated text](https://ai.google.dev/responsible/docs/safeguards/synthid) — Google AI for Developers.

[35] [A Watermark for Large Language Models](https://arxiv.org/pdf/2301.10226) — Kirchenbauer et al.; [jwkirchenbauer/lm-watermarking](https://github.com/jwkirchenbauer/lm-watermarking).

[36] [Paraphrasing evades detectors of AI-generated text, but retrieval is an effective defense](https://arxiv.org/abs/2303.13408) — Krishna et al., arXiv:2303.13408 (NeurIPS 2023); [martiansideofthemoon/ai-detection-paraphrases](https://github.com/martiansideofthemoon/ai-detection-paraphrases); [kalpeshk2011/dipper-paraphraser-xxl](https://huggingface.co/kalpeshk2011/dipper-paraphraser-xxl).

[37] [Provable Robust Watermarking for AI-Generated Text (Unigram-Watermark)](https://arxiv.org/abs/2306.17439) — arXiv:2306.17439 (ICLR 2024); [XuandongZhao/Unigram-Watermark](https://github.com/XuandongZhao/Unigram-Watermark).

[38] [How Claude's text watermarking works](https://www.anthropic.com/news/claude-text-watermark) — Anthropic.

[39] [Anthropic shares more details about how Claude's new watermarks will work](https://techcrunch.com/2026/08/15/anthropic-shares-more-details-about-how-claudes-new-watermarks-will-work/) — TechCrunch, Aug 2026.

[40] [StyloMetrix: An Open-Source Multilingual Tool for Representing Stylometric Vectors](https://arxiv.org/pdf/2309.12810) — arXiv:2309.12810; [ZILiAT-NASK/StyloMetrix](https://github.com/ZILiAT-NASK/StyloMetrix); [stylo-metrix on PyPI](https://pypi.org/project/stylo-metrix/).

[41] [craigtrim/pystylometry](https://github.com/craigtrim/pystylometry) — GitHub.

[42] [Feature-Based Detection of AI-Generated Text: An Analysis of Stylometric and Perplexity Markers](https://www.researchgate.net/publication/398588043_Feature-Based_Detection_of_AI-Generated_Text_An_Analysis_of_Stylometric_and_Perplexity_Markers_in_Contemporary_Large_Language_Models) — ResearchGate.

[43] [RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors](https://arxiv.org/abs/2405.07940) — arXiv:2405.07940 (ACL 2024); [liamdugan/raid](https://github.com/liamdugan/raid).

[44] [TM-TREK at SemEval-2024 Task 8: Towards LLM-Based Automatic Boundary Detection for Human-Machine Mixed Text](https://arxiv.org/pdf/2404.00899) — arXiv:2404.00899.
