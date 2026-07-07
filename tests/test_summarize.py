"""Tests for summarize.py — schema, watchlist prompt-injection logic, and the
publish-gate that blocks truncated briefings.

The actual Claude API call is not exercised here; we only test the
deterministic pre/post-processing and validation logic. validate_digest() is
the regression guard for the recurring "briefing cut short" failure (e.g.
2026-06-17): the audio_script is the final field of a single
schema-constrained Claude call, so when generation is cut off the JSON still
parses but the narration is a fragment — it must be rejected so the pipeline
fails loud (app keeps yesterday's briefing) instead of publishing a stub."""
from daily_news.config import Watchlist, WatchlistOrg
from daily_news.summarize import (
    _DIGEST_SCHEMA,
    _TOPIC_KEYS,
    AUDIO_SCRIPT_MIN_WORDS,
    Digest,
    build_watchlist_context_block,
    validate_digest,
)


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


_SECTIONS = [
    {"name": "Marketing & Business", "topic_key": "marketing",
     "stories": [{"headline": "h", "summary": "s", "source": "src", "url": "u1"}]},
    {"name": "AI & Tech", "topic_key": "ai",
     "stories": [{"headline": "h", "summary": "s", "source": "src", "url": "u2"}]},
]


def _digest(audio_script: str, sections=None) -> Digest:
    return Digest(
        why_this_matters="Today matters because of X, Y, and Z for the consulting pivot.",
        sections=_SECTIONS if sections is None else sections,
        audio_script=audio_script,
        chosen_url_hashes=["a", "b"],
        raw_response="{}",
    )


def _complete_script() -> str:
    body = " ".join(["word"] * (AUDIO_SCRIPT_MIN_WORDS // 2 + 200))
    return (
        "[[INTRO]]\nGood morning, Midya. It's Wednesday. Here's what matters today.\n\n"
        "[[SECTION:marketing]]\nLet's lead with marketing. " + body + ".\n\n"
        "[[SECTION:ai]]\nAnd on AI. " + body + ".\n\n"
        "[[OUTRO]]\nThat's your briefing, Midya. Have a focused day."
    )


def test_validate_digest_accepts_complete_briefing():
    assert validate_digest(_digest(_complete_script())) == []


def test_validate_digest_rejects_truncated_2026_06_17_shape():
    """The actual 2026-06-17 failure: intro + 2 sections, NO outro, ends
    mid-sentence ('...moving from'), well under the word floor."""
    truncated = (
        "[[INTRO]]\nGood morning, Midya. It's Wednesday, June seventeenth.\n\n"
        "[[SECTION:marketing]]\nLet's lead with marketing. " + " ".join(["word"] * 300) + ".\n\n"
        "[[SECTION:ai]]\nOn the AI front, Genesis AI unveiled a robot. This matters "
        "because it signals a maturation in how the robotics industry is thinking "
        "about deployment: moving from"
    )
    problems = validate_digest(_digest(truncated))
    assert problems, "a truncated briefing must be rejected"
    joined = " ".join(problems).lower()
    assert "outro" in joined            # missing sign-off
    assert "punctuation" in joined      # ends mid-sentence


def test_validate_digest_flags_short_script():
    problems = validate_digest(_digest("[[INTRO]]\nGood morning. Short. [[OUTRO]]\nBye."))
    assert any("word" in p.lower() for p in problems)


def test_validate_digest_flags_missing_outro():
    script = "[[INTRO]]\nGood morning, Midya.\n\n[[SECTION:ai]]\n" + " ".join(["word"] * 1600) + "."
    problems = validate_digest(_digest(script))
    assert any("outro" in p.lower() for p in problems)
    assert not any("punctuation" in p.lower() for p in problems)  # it ends with '.'


def test_validate_digest_flags_empty_audio_script():
    problems = validate_digest(_digest(""))
    assert any("audio_script is empty" in p.lower() for p in problems)


def test_validate_digest_flags_empty_sections():
    problems = validate_digest(_digest(_complete_script(), sections=[]))
    assert any("section" in p.lower() for p in problems)
