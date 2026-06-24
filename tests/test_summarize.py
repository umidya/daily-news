"""Tests for summarize.py — the publish-gate that blocks truncated briefings.

The Claude API call is not exercised here; we only test the deterministic
validation logic. This is the regression guard for the recurring "briefing cut
short" failure (e.g. 2026-06-17): the audio_script is the final field of a
single schema-constrained Claude call, so when generation is cut off the JSON
still parses but the narration is a fragment. validate_digest() must reject
that fragment so the pipeline fails loud (app keeps yesterday's briefing)
instead of publishing a ~4-minute stub."""
from daily_news.summarize import AUDIO_SCRIPT_MIN_WORDS, Digest, validate_digest


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
