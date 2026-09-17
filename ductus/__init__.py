"""ductus -- gauge which parts of a text read as machine-written, and why.

In palaeography the *ductus* is the characteristic manner and sequence of strokes
by which a scribe's hand is recognised. This package looks for the equivalent in
prose: not a verdict about who wrote something, but evidence about how it reads,
attached to the exact characters that carry it.

    >>> from ductus import gauge
    >>> report = gauge("Great question! Let's delve into this robust tapestry.")
    >>> report.document.label
    'leans-machine'
    >>> report.segments[0].signals[0].name
    'chat-leftover'

Every finding is a :class:`Signal` with a direction, a weight, the detector that
produced it, a reason, and a :class:`Span` carrying both character offsets and
W3C-style quote/prefix/suffix selectors, so highlights survive an edit.

**There is no percentage anywhere in this package, and that is deliberate.** A
number like "87% AI" reads as a calibrated probability, is not one, and is how
people get falsely accused. What you get instead is a lean in [-1, +1], an
evidence strength, and a coarse label you can argue with. See
:mod:`ductus.score`.

Three seams, each one keyword argument with a working default:
``segmenter=`` (how the text is cut up), ``detectors=`` (what produces evidence),
``aggregate=`` (how evidence becomes a lean).
"""

from ductus.base import (
    LABELS,
    SCHEMA_VERSION,
    Report,
    Segment,
    Signal,
    Span,
)
from ductus.core import gauge, iter_segments
from ductus.detect import DETECTORS
from ductus.render import to_html, to_json, to_markdown
from ductus.score import aggregate
from ductus.segment import SEGMENTERS
from ductus.tells import TellMatch, TellRule, iter_tell_matches, load_rules

try:  # the installed distribution is the source of truth; CI bumps pyproject.toml
    from importlib.metadata import version as _version

    __version__ = _version("ductus")
except Exception:  # running from a source tree that was never installed
    __version__ = "0.0.0+unknown"

__all__ = [
    "DETECTORS",
    "LABELS",
    "SCHEMA_VERSION",
    "SEGMENTERS",
    "Report",
    "Segment",
    "Signal",
    "Span",
    "TellMatch",
    "TellRule",
    "__version__",
    "aggregate",
    "gauge",
    "iter_segments",
    "iter_tell_matches",
    "load_rules",
    "to_html",
    "to_json",
    "to_markdown",
]
