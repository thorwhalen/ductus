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
