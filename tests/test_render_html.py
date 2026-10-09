"""The HTML rendering's contract: what the page must contain to be readable and honest."""

import json
import re

import pytest

from ductus import gauge, to_html, to_markdown

SAMPLE = (
    "Great question! Let's delve into this robust tapestry.\n\n"
    "It's important to note that the rollout serves as a bridge.\n\n"
    "Sent the export Friday. Two sites, not five."
)


@pytest.fixture(scope="module")
def html():
    return to_html(gauge(SAMPLE), text=SAMPLE)


def test_the_page_is_self_contained(html):
    """No CDN, no build step -- a report has to open from a file:// URL offline."""
    assert "<script src=" not in html
    assert '<link rel="stylesheet"' not in html
    assert "http://" not in html.replace("http://www.w3.org", "")


def test_every_mark_is_closed_and_has_a_tooltip_entry(html):
    assert html.count("<mark") == html.count("</mark>")
    keys = set(re.findall(r'<mark data-k="([^"]+)"', html))
    data = json.loads(re.search(r'id="ductus-data">(.*?)</script>', html, re.S).group(1))
    assert keys and keys == set(data)
    for entry in data.values():
        assert entry["r"], "every highlight must carry its reason"
        assert entry["d"] in ("machine", "human", "neutral")


def test_the_reason_is_anchored_to_the_highlight(html):
    """The reason belongs where the eye already is, not in a corner."""
    assert "aside.at" in html, "the anchored-position class must be styled"
    assert "getBoundingClientRect" in html, "and positioned from the mark's geometry"
    assert "ANCHOR_MIN_WIDTH" in html


def test_it_falls_back_to_a_bottom_sheet_when_too_narrow(html):
    assert "max-width:640px" in html
    assert "innerWidth<ANCHOR_MIN_WIDTH" in html


def test_highlights_are_keyboard_reachable(html):
    """Hover-only evidence is evidence some readers cannot get to."""
    assert "tabIndex=0" in html
    assert "'focus'" in html and "'blur'" in html


def test_both_themes_are_defined(html):
    assert "prefers-color-scheme:dark" in html
    assert 'data-theme="dark"' in html
    assert "oklch(" in html, "a perceptually-uniform ramp, not raw hex"


def test_hue_carries_score_and_the_lane_carries_overlap(html):
    """Two channels: stacking translucent fills is what makes overlap unreadable."""
    assert "color-mix(in oklab" in html
    assert 'class="lane"' in html


def test_the_page_states_its_own_limits(html):
    # "non-native English" used to be in this list. Phase 2 measured the opposite --
    # the bias runs toward formal, fluent prose and the native-speaker control was the
    # most-accused group -- and the page now says so. Repeating the field's warning
    # about a bias this package does not have is not honesty, it is borrowed caution.
    for phrase in (
        "not a verdict",
        "one in sixteen",
        "formal, fluent prose",
        "Do not use this to accuse",
    ):
        assert phrase in html
    assert "non-native" not in html, "the corrected claim must not creep back"
    # Still no percentage anywhere near a verdict about one document: the measured
    # error rate is stated as a natural frequency instead.
    assert "%" not in re.search(r"<footer>(.*?)</footer>", html, re.S).group(1)


def test_markdown_and_html_agree_on_the_verdict():
    report = gauge(SAMPLE)
    assert report.document.label in to_markdown(report)
    assert report.document.label in to_html(report)


@pytest.mark.parametrize("fmt", ["html", "markdown"])
def test_gauge_verb_passes_title_through(fmt):
    """`ductus gauge --title` must reach the rendering, not be silently dropped."""
    from ductus.tools import gauge as gauge_verb

    out = gauge_verb(
        "Sent it Friday. Two sites, not five.", format=fmt, title="Custom heading"
    )
    assert "Custom heading" in out
    assert "Where this reads as machine-written" not in out


def test_gauge_verb_keeps_each_renderers_default_title():
    from ductus.tools import gauge as gauge_verb

    assert gauge_verb("Sent it Friday.", format="markdown").startswith("# Reading")
    assert "Where this reads as machine-written" in gauge_verb(
        "Sent it Friday.", format="html"
    )


    assert "Where this reads as machine-written" in gauge_verb("Sent it Friday.", format="html")


def test_ranked_flags_list_is_ordered_by_weight(html):
    section = html.split('<section class="rank">')[1].split("</section>")[0]
    weights = [float(w) for w in re.findall(r'class="rk-w">([\d.]+)<', section)]
    assert weights and weights == sorted(weights, reverse=True)
    assert "Flags by weight" in section


def test_ranked_flags_escape_the_quoted_text():
    import dataclasses

    report = gauge(SAMPLE)
    seg = next(seg for seg in report.segments if seg.signals)
    sig = seg.signals[0]
    hostile = dataclasses.replace(sig, span=dataclasses.replace(sig.span, quote="<script>x</script>"))
    seg = dataclasses.replace(seg, signals=(hostile, *seg.signals[1:]))
    report = dataclasses.replace(report, segments=[seg])
    section = to_html(report, text=SAMPLE).split('<section class="rank">')[1]
    assert "<script>x" not in section
    assert "&lt;script&gt;x" in section


def test_ranked_flags_say_so_when_nothing_fired():
    section = to_html(gauge("ok.")).split('<section class="rank">')[1]
    assert "weak result, not a clean bill" in section
    assert "<li>" not in section


def test_dark_mode_sets_color_scheme(html):
    """Scrollbars and form controls follow dark mode only with the property itself."""
    assert len(re.findall(r"(?<![-\w])color-scheme:dark", html)) == 2
