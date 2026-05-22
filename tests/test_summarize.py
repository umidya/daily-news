"""Tests for summarize.py — schema, prompt-injection logic, and the
top-level topic_key registry.

The actual Claude API call is not exercised here; we only test the
deterministic pre/post-processing."""
from daily_news.config import Watchlist, WatchlistOrg
from daily_news.summarize import _DIGEST_SCHEMA, _TOPIC_KEYS, build_watchlist_context_block


def test_watchlist_is_a_known_topic_key():
    """summarize.py emits a JSON schema with topic_key constrained to this
    enum — adding a new section requires adding the key here."""
    assert "watchlist" in _TOPIC_KEYS


def test_schema_topic_key_enum_includes_watchlist():
    """The schema enum is what the API enforces; _TOPIC_KEYS alone isn't enough."""
    section_schema = _DIGEST_SCHEMA["properties"]["sections"]["items"]
    enum = section_schema["properties"]["topic_key"]["enum"]
    assert "watchlist" in enum


def test_build_watchlist_context_block_returns_empty_string_for_none():
    """When no watchlist is configured, the user message gets nothing extra."""
    assert build_watchlist_context_block(None) == ""


def test_build_watchlist_context_block_lists_orgs_by_section():
    wl = Watchlist(
        clients=[WatchlistOrg(org="Capilano University", industry="higher_ed_canada")],
        prospects=[WatchlistOrg(org="Some Prospect U", industry="higher_ed_canada", stage="discovery")],
        peer_orgs=[WatchlistOrg(org="AACRAO", relationship="consortium_peer")],
        thought_leadership_themes=["AI in marketing operations"],
    )
    block = build_watchlist_context_block(wl)
    assert "WATCHLIST_ORGS" in block
    assert "Capilano University" in block
    assert "Some Prospect U" in block
    assert "AACRAO" in block
    assert "AI in marketing operations" in block


def test_build_watchlist_context_block_includes_framing_reminder():
    """The framing rule is load-bearing — the block must remind Claude not to
    surface relationships, even though the system prompt also covers this."""
    wl = Watchlist(clients=[WatchlistOrg(org="X")])
    block = build_watchlist_context_block(wl)
    # Some signal that the orgs are NOT to be framed as relationships.
    block_lower = block.lower()
    assert "never" in block_lower or "do not" in block_lower
    assert "relationship" in block_lower or "client" in block_lower
