"""Model-based detectors -- the ``[local]`` extra. Two more functions of the same shape.

:func:`fast_detect_gpt` and :func:`binoculars` are ``(text, span) -> Iterator[Signal]``
like every other detector here. They differ in one way that matters: their evidence
is a number a reader cannot inspect, produced by a language model rather than quoted
from the text. The whole design of how that number becomes a :class:`~ductus.base.Signal`
is argued in ``misc/docs/curvature-as-evidence.md``; the short version is:

* the statistic is the published one, evaluated over the span's tokens;
* it is compared to **the same statistic over the rest of this document**, never to a
  threshold lifted from a paper's benchmark -- so no calibration is claimed anywhere;
* the standing is banded, not mapped continuously: a mid-range score emits *nothing*,
  because a mid-range score is this detector having nothing to say;
* both directions are emitted, because a detector that can only accuse is not a
  measuring instrument.

The consequence, accepted knowingly: these detectors cannot say whether a whole
document is machine-written. With no rest-of-the-document to compare against, they
return nothing.

``torch`` and ``transformers`` are imported only when a detector actually runs, so
``import ductus`` stays as cheap as it was.

>>> band_of(0.9) is None, band_of(1.8), band_of(-3.0)
(True, 0.3, 0.45)
>>> round(robust_z(10.0, [1.0, 2.0, 3.0, 4.0, 5.0]), 2)
4.72
"""

from __future__ import annotations

import statistics
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import lru_cache

from ductus.base import Signal, Span

__all__ = [
    "BANDS",
    "BINOCULARS_OBSERVER",
    "BINOCULARS_PERFORMER",
    "FAST_DETECT_MODEL",
    "MIN_TOKENS",
    "MIN_WINDOWS",
    "band_of",
    "binoculars",
    "fast_detect_gpt",
    "robust_z",
]

#: Single model, used as both the scoring and the sampling model (the analytic
#: same-model setting of Fast-DetectGPT). Small enough for CPU; the documented
#: upgrade is ``EleutherAI/gpt-neo-2.7B``.
FAST_DETECT_MODEL = "gpt2"

#: Binoculars needs a *closely related* pair sharing one tokenizer, not an
#: arbitrary strong/weak combination. ``distilgpt2`` is a distillation of ``gpt2``.
#: The documented upgrade is the paper's ``tiiuae/falcon-7b`` pair.
BINOCULARS_OBSERVER = "distilgpt2"
BINOCULARS_PERFORMER = "gpt2"

#: ``(|z| threshold, weight)``, lowest first. Below the first threshold the detector
#: emits nothing at all -- the dead zone is the point, not an oversight. Neither
#: weight exceeds the strongest deterministic signal: a statistic the reader cannot
#: inspect does not get to outvote one they can.
BANDS: tuple[tuple[float, float], ...] = ((1.5, 0.30), (2.5, 0.45))

#: Fewer comparable windows than this and there is no reference distribution worth
#: the name, so nothing is emitted.
MIN_WINDOWS = 6

#: A span shorter than this is too few tokens for the statistic to mean anything --
#: roughly a sentence's worth.
MIN_TOKENS = 16

#: Tokens per forward pass. Half of it is context on every chunk after the first.
WINDOW = 512


class ModelDetectorUnavailable(ImportError):
    """Raised when a model-based detector is used without the ``[local]`` extra."""


def _torch():
    """Import ``torch``/``transformers`` on demand, with an actionable error."""
    try:
        import torch
        import transformers  # noqa: F401
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ModelDetectorUnavailable(
            "ductus's model-based detectors need the [local] extra:\n"
            "    pip install 'ductus[local]'\n"
            "which installs torch and transformers. The deterministic detectors "
            "(tells, forensic, rhetoric, rhythm) need neither and are the default."
        ) from e
    return torch


# ------------------------------------------------------------------- pure arithmetic


def robust_z(value: float, reference: Sequence[float]) -> float:
    """How far ``value`` stands out from ``reference``, in MADs.

    Median and MAD rather than mean and standard deviation: on a mixed document the
    machine-written stretches are exactly the outliers that would drag a mean toward
    themselves and hide the thing being looked for.

    A degenerate reference (every value identical) yields ``0.0``, which falls in the
    dead zone and so emits nothing.

    >>> robust_z(3.0, [1.0, 2.0, 3.0, 4.0, 5.0])
    0.0
    >>> robust_z(1.0, [1.0, 1.0, 1.0])
    0.0
    """
    median = statistics.median(reference)
    mad = statistics.median([abs(x - median) for x in reference])
    scale = 1.4826 * mad
    return (value - median) / scale if scale > 0 else 0.0


def band_of(z: float, bands: Sequence[tuple[float, float]] = BANDS) -> float | None:
    """The weight for a standing of ``z``, or ``None`` when it says nothing.

    >>> band_of(1.49) is None
    True
    >>> band_of(1.5), band_of(2.49), band_of(2.5), band_of(-9.0)
    (0.3, 0.3, 0.45, 0.45)
    """
    weight = None
    for threshold, w in bands:
        if abs(z) >= threshold:
            weight = w
    return weight


def _iter_chunks(n: int, window: int = WINDOW) -> Iterator[tuple[int, int, int]]:
    """``(start, end, first_scored)`` passes covering every position exactly once.

    Position 0 has no prediction. After the first chunk, half the window is context
    whose predictions were already recorded, so every scored position has at least
    ``window // 2`` tokens of history.

    >>> list(_iter_chunks(5, 8))
    [(0, 5, 1)]
    >>> list(_iter_chunks(20, 8))
    [(0, 8, 1), (4, 12, 8), (8, 16, 12), (12, 20, 16)]
    """
    stride = max(1, window // 2)
    start, keep = 0, 1
    while True:
        end = min(start + window, n)
        yield start, end, keep
        if end >= n:
            return
        start, keep = end - stride, end


def _scored_rows(start: int, end: int, keep: int) -> slice:
    """Logit rows predicting document positions ``[keep, end)`` of chunk ``[start, end)``.

    Row ``j`` predicts the token at ``start + j + 1``, so position ``p`` is read from
    row ``p - start - 1``. The chunk's last row predicts a position past its own end
    and is never used.

    >>> _scored_rows(0, 8, 1)
    slice(0, 7, None)
    >>> _scored_rows(4, 12, 8)
    slice(3, 7, None)
    """
    return slice(keep - start - 1, end - start - 1)


@dataclass(frozen=True)
class _Profile:
    """Per-token accumulators for one document, and how a window turns into a score.

    ``a`` and ``b`` are the two sums every statistic here is built from. ``kind``
    says how to combine them; ``machine_sign`` says which end of the resulting scale
    argues machine, so callers never have to remember that Fast-DetectGPT counts up
    and Binoculars counts down.
    """

    offsets: tuple[tuple[int, int], ...]
    a: tuple[float, ...]
    b: tuple[float, ...]
    kind: str  # "curvature" (a / sqrt(b)) or "ratio" (a / b)
    machine_sign: float
    model: str

    def score(self, lo: int, hi: int) -> float:
        """The published statistic over tokens ``[lo, hi)``.

        >>> p = _Profile((), (1.0, 3.0), (4.0, 0.0), "curvature", 1.0, "m")
        >>> p.score(0, 2)
        2.0
        >>> _Profile((), (1.0, 3.0), (2.0, 2.0), "ratio", -1.0, "m").score(0, 2)
        1.0
        """
        a, b = sum(self.a[lo:hi]), sum(self.b[lo:hi])
        if self.kind == "curvature":
            return a / (b**0.5) if b > 0 else 0.0
        return a / b if b else 0.0


def _token_range(profile: _Profile, span: Span) -> tuple[int, int]:
    """The half-open token index range whose characters overlap ``span``.

    >>> p = _Profile(((0, 3), (3, 7), (7, 11)), (), (), "ratio", 1.0, "m")
    >>> _token_range(p, Span(3, 11, "x"))
    (1, 3)
    >>> _token_range(p, Span(20, 30, "x"))
    (0, 0)
    """
    hits = [
        i
        for i, (a, b) in enumerate(profile.offsets)
        if a < span.end and b > span.start and b > a
    ]
    return (hits[0], hits[-1] + 1) if hits else (0, 0)


def _reference_scores(profile: _Profile, lo: int, hi: int) -> list[float]:
    """The same statistic over every same-length window that misses ``[lo, hi)``.

    Stepping by half a window keeps the reference set dense without making it a
    near-copy of itself. Windows that overlap the span are excluded so the span is
    not compared against a distribution it helped define.

    >>> p = _Profile((), tuple([1.0] * 10), tuple([1.0] * 10), "ratio", 1.0, "m")
    >>> len(_reference_scores(p, 0, 2))
    7
    """
    n = len(profile.a)
    width = hi - lo
    step = max(1, width // 2)
    return [
        profile.score(i, i + width)
        for i in range(0, n - width + 1, step)
        if i + width <= lo or i >= hi
    ]


# --------------------------------------------------------------------- model access


@lru_cache(maxsize=4)
def _load(model_id: str, device: str):
    """Tokenizer and model, loaded once per id. Kept warm for the session.

    Warm is the right default: a session that scores several texts with one detector
    pays the load once. The cost is that every model touched stays resident -- four
    GPT-2-family models is about 10GB in float32 -- so code that sweeps across many
    models should call ``_load.cache_clear()`` between them. ``misc/measure_model_ladder.py``
    does exactly that, and was swapping rather than computing until it did.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if not getattr(tokenizer, "is_fast", False):
        raise ModelDetectorUnavailable(
            f"{model_id!r} has no fast tokenizer, so token-to-character offsets are "
            "unavailable and a signal could not be anchored to the text it is about."
        )
    model = AutoModelForCausalLM.from_pretrained(model_id).to(device)
    model.eval()
    return tokenizer, model


def _pick_device(device: str | None) -> str:
    """CUDA when it is there, CPU otherwise. Explicit ``device=`` always wins."""
    if device:
        return device
    torch = _torch()
    return "cuda" if torch.cuda.is_available() else "cpu"


def _encode(tokenizer, text: str):
    """Token ids and their character offsets, with no truncation.

    ``verbose=False`` silences the tokenizer's warning about exceeding the model's
    context length: the sequence is never fed to the model whole, it is fed in
    :data:`WINDOW`-sized chunks by :func:`_iter_chunks`.
    """
    enc = tokenizer(text, return_offsets_mapping=True, return_tensors="pt", verbose=False)
    offsets = tuple((int(a), int(b)) for a, b in enc["offset_mapping"][0].tolist())
    return enc["input_ids"][0], offsets


# ------------------------------------------------------------------ fast-detect-gpt


@lru_cache(maxsize=4)
def _fast_detect_profile(text: str, model_id: str, device: str) -> _Profile:
    """Conditional probability curvature, accumulated per token.

    Per position, ``a`` is the observed log-likelihood minus the model's own expected
    log-likelihood there, and ``b`` is the variance of that expectation. The paper's
    statistic over any window is ``sum(a) / sqrt(sum(b))`` -- which is what
    :meth:`_Profile.score` computes, so a span is scored by exactly the published
    method rather than by anything invented here.
    """
    torch = _torch()
    tokenizer, model = _load(model_id, device)
    ids, offsets = _encode(tokenizer, text)
    n = len(ids)
    a = [0.0] * n
    b = [0.0] * n

    with torch.no_grad():
        for start, end, keep in _iter_chunks(n, WINDOW):
            chunk = ids[start:end].unsqueeze(0).to(device)
            logits = model(chunk).logits[0].float()
            lprobs = torch.log_softmax(logits, dim=-1)
            probs = torch.softmax(logits, dim=-1)
            mean_ref = (probs * lprobs).sum(dim=-1)
            var_ref = (probs * lprobs.square()).sum(dim=-1) - mean_ref.square()
            rows = _scored_rows(start, end, keep)
            labels = ids[keep:end].unsqueeze(-1).to(device)
            ll = lprobs[rows].gather(-1, labels).squeeze(-1)
            a[keep:end] = (ll - mean_ref[rows]).tolist()
            b[keep:end] = var_ref[rows].clamp_min(0.0).tolist()

    return _Profile(offsets, tuple(a), tuple(b), "curvature", +1.0, model_id)


def fast_detect_gpt(
    text: str,
    span: Span,
    *,
    model: str = FAST_DETECT_MODEL,
    bands: Sequence[tuple[float, float]] = BANDS,
    min_windows: int = MIN_WINDOWS,
    min_tokens: int = MIN_TOKENS,
    device: str | None = None,
) -> Iterator[Signal]:
    """Conditional probability curvature, read as a standing within this document.

    A passage a model finds unusually *predictable* compared to the rest of the
    document leans machine; an unusually surprising one leans human. Neither claim
    is absolute, and none of the paper's benchmark thresholds are used.

    Needs the ``[local]`` extra. The first call downloads and caches the proxy model;
    later calls on the same text cost no model time at all.
    """
    yield from _curvature_signals(
        _fast_detect_profile(text, model, _pick_device(device)),
        text,
        span,
        name="curvature-outlier",
        detector="fast-detect-gpt",
        statistic="conditional probability curvature",
        bands=bands,
        min_windows=min_windows,
        min_tokens=min_tokens,
    )


# ----------------------------------------------------------------------- binoculars


@lru_cache(maxsize=4)
def _binoculars_profile(
    text: str, observer_id: str, performer_id: str, device: str
) -> _Profile:
    """Perplexity over cross-perplexity, accumulated per token.

    ``a`` is the performer's surprise at the token actually written; ``b`` is the
    performer's surprise at what the observer expected. Their ratio over a window is
    the paper's *B*. Machine text makes the two agree, so **low** B argues machine --
    which is why this profile carries ``machine_sign = -1``.
    """
    torch = _torch()
    obs_tokenizer, observer = _load(observer_id, device)
    tokenizer, performer = _load(performer_id, device)
    if obs_tokenizer.get_vocab() != tokenizer.get_vocab():
        raise ValueError(
            f"binoculars needs observer and performer to share a tokenizer; "
            f"{observer_id!r} and {performer_id!r} do not. Cross-perplexity between "
            "models that disagree about what a token is has no meaning."
        )

    ids, offsets = _encode(tokenizer, text)
    n = len(ids)
    a = [0.0] * n
    b = [0.0] * n

    with torch.no_grad():
        for start, end, keep in _iter_chunks(n, WINDOW):
            chunk = ids[start:end].unsqueeze(0).to(device)
            lprobs = torch.log_softmax(performer(chunk).logits[0].float(), dim=-1)
            obs_probs = torch.softmax(observer(chunk).logits[0].float(), dim=-1)
            cross = -(obs_probs * lprobs).sum(dim=-1)
            rows = _scored_rows(start, end, keep)
            labels = ids[keep:end].unsqueeze(-1).to(device)
            a[keep:end] = (-lprobs[rows].gather(-1, labels).squeeze(-1)).tolist()
            b[keep:end] = cross[rows].tolist()

    return _Profile(offsets, tuple(a), tuple(b), "ratio", -1.0, performer_id)


def binoculars(
    text: str,
    span: Span,
    *,
    observer: str = BINOCULARS_OBSERVER,
    performer: str = BINOCULARS_PERFORMER,
    bands: Sequence[tuple[float, float]] = BANDS,
    min_windows: int = MIN_WINDOWS,
    min_tokens: int = MIN_TOKENS,
    device: str | None = None,
) -> Iterator[Signal]:
    """Cross-perplexity of a paired observer and performer, as a standing in this text.

    Where :func:`fast_detect_gpt` asks how predictable a passage is, this asks whether
    two closely related models are *unusually unsurprised in the same places* -- which
    generalises better to generators neither model has seen.

    Needs the ``[local]`` extra, and observer and performer must share a tokenizer.
    """
    yield from _curvature_signals(
        _binoculars_profile(text, observer, performer, _pick_device(device)),
        text,
        span,
        name="cross-perplexity-outlier",
        detector="binoculars",
        statistic="perplexity / cross-perplexity",
        bands=bands,
        min_windows=min_windows,
        min_tokens=min_tokens,
    )


# ------------------------------------------------------------------- shared banding


def _curvature_signals(
    profile: _Profile,
    text: str,
    span: Span,
    *,
    name: str,
    detector: str,
    statistic: str,
    bands: Sequence[tuple[float, float]],
    min_windows: int,
    min_tokens: int,
) -> Iterator[Signal]:
    """Band a span's standing against the rest of the document, or say nothing."""
    lo, hi = _token_range(profile, span)
    if hi - lo < min_tokens:
        return
    reference = _reference_scores(profile, lo, hi)
    if len(reference) < min_windows:
        return

    score = profile.score(lo, hi)
    z = profile.machine_sign * robust_z(score, reference)
    weight = band_of(z, bands)
    if weight is None:
        return

    machine = z > 0
    yield Signal(
        name=name,
        direction="machine" if machine else "human",
        weight=weight,
        detector=detector,
        value=round(score, 4),
        note=(
            f"{statistic} {score:.3f} under {profile.model}, {abs(z):.1f} MADs "
            f"{'flatter' if machine else 'more surprising'} than the rest of this "
            f"document ({len(reference)} comparable windows); "
            "unlike the other detectors this is a model's opinion about the text, "
            "not a quotation from it"
        ),
        span=Span.of(text, span.start, span.end, level=span.level),
    )
