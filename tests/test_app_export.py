"""Tests for app_export topic-mapping coverage.

These maps drive how the mobile app categorizes and labels stories. Missing
a topic_key here doesn't crash anything — it silently falls back to a default
('Global' / 'globe' / etc.) — but the result is a story that looks like it
belongs to the wrong section. So every topic_key produced by summarize.py
must have an entry in all three maps.
"""
from daily_news.app_export import (
    TOPIC_TO_CATEGORY,
    TOPIC_TO_THUMBNAIL,
    _SECTION_TITLE_BY_TOPIC,
)
from daily_news.summarize import _TOPIC_KEYS


def test_every_topic_key_has_a_category():
    for key in _TOPIC_KEYS:
        assert key in TOPIC_TO_CATEGORY, f"missing category mapping for topic_key={key}"


def test_every_topic_key_has_a_thumbnail():
    for key in _TOPIC_KEYS:
        assert key in TOPIC_TO_THUMBNAIL, f"missing thumbnail mapping for topic_key={key}"


def test_every_topic_key_has_a_section_title():
    for key in _TOPIC_KEYS:
        assert (
            key in _SECTION_TITLE_BY_TOPIC
        ), f"missing section title for topic_key={key}"


def test_watchlist_specifically_maps_distinctly():
    """The Watchlist section is structurally distinct from the existing topics
    — it shouldn't collapse into another category."""
    assert TOPIC_TO_CATEGORY["watchlist"] == "Watchlist"
    assert _SECTION_TITLE_BY_TOPIC["watchlist"] == "Watchlist"
