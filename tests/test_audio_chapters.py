from daily_news.app_export import (
    _build_chapters_fallback,
    _build_chapters_from_audio,
)
from daily_news.summarize import parse_audio_script, strip_audio_markers


def test_parse_audio_script_strips_markers_and_records_segments():
    script = (
        "[[INTRO]]\n"
        "Good morning, Midya.\n\n"
        "[[SECTION:higher_ed_canada]]\n"
        "Higher ed first today.\n\n"
        "[[SECTION:ai]]\n"
        "AI second.\n\n"
        "[[OUTRO]]\n"
        "Have a good one."
    )
    stripped, segments = parse_audio_script(script)
    assert "[[" not in stripped, "markers must be stripped from output"
    assert stripped.startswith("Good morning, Midya.")
    assert stripped.endswith("Have a good one.")

    roles = [s["role"] for s in segments]
    assert roles == ["intro", "section", "section", "outro"]

    # offsets must point to the right places in the stripped string
    intro = segments[0]
    higher_ed = segments[1]
    ai = segments[2]
    outro = segments[3]

    assert stripped[intro["start_char"]:intro["end_char"]].strip().startswith(
        "Good morning"
    )
    assert stripped[higher_ed["start_char"]:higher_ed["end_char"]].strip().startswith(
        "Higher ed first"
    )
    assert higher_ed["topic_key"] == "higher_ed_canada"
    assert stripped[ai["start_char"]:ai["end_char"]].strip().startswith("AI second")
    assert ai["topic_key"] == "ai"
    assert stripped[outro["start_char"]:outro["end_char"]].strip().startswith(
        "Have a good one"
    )


def test_parse_audio_script_returns_no_segments_when_no_markers():
    script = "Good morning. Some news. Goodbye."
    stripped, segments = parse_audio_script(script)
    assert stripped == script
    assert segments == []


def test_strip_audio_markers_helper():
    script = "[[INTRO]]\nHi.\n[[OUTRO]]\nBye."
    assert strip_audio_markers(script).strip() == "Hi.\nBye."


def test_chapters_in_narration_order_not_section_list_order():
    """Claude is free to narrate sections in a different order than they
    appear in the JSON sections array. Chapter order must match narration."""
    higher_ed_text = "A" * 100  # 100 chars
    ai_text = "B" * 50          # 50 chars
    script = (
        "[[INTRO]]\nIntro line.\n"
        + "[[SECTION:higher_ed_canada]]\n" + higher_ed_text + "\n"
        + "[[SECTION:ai]]\n" + ai_text + "\n"
        + "[[OUTRO]]\nOutro."
    )
    chapters = _build_chapters_from_audio(script, total_seconds=300)
    assert chapters is not None

    # Higher Ed should come first because it was narrated first, even though
    # the JSON section order would put AI before Higher Ed.
    assert chapters[0]["title"] == "Higher Education"
    assert chapters[1]["title"] == "AI & Tech"

    # Higher Ed has 2x the char count of AI, so it should get ~2x the duration.
    higher_ed_seconds = _to_seconds(chapters[0]["duration"])
    ai_seconds = _to_seconds(chapters[1]["duration"])
    assert higher_ed_seconds > ai_seconds
    # ~2:1 ratio with some rounding slack
    assert 1.7 < higher_ed_seconds / max(1, ai_seconds) < 2.3


def test_chapters_returns_none_when_no_markers_so_caller_can_fallback():
    script = "Plain narration with no markers anywhere."
    assert _build_chapters_from_audio(script, total_seconds=300) is None


def test_fallback_used_when_no_markers():
    sections = [
        {"name": "AI & Tech", "topic_key": "ai", "stories": [
            {"headline": "h" * 20, "summary": "s" * 80},  # 100 chars
        ]},
        {"name": "Local News", "topic_key": "kamloops_sun_peaks", "stories": [
            {"headline": "h" * 10, "summary": "s" * 40},  # 50 chars
        ]},
    ]
    chapters = _build_chapters_fallback(sections, total_seconds=300)
    assert len(chapters) == 2
    assert chapters[0]["title"] == "AI & Tech"
    assert chapters[1]["title"] == "Local News"
    # AI got 100 of 150 chars → 200s; Local got 50 of 150 → 100s
    assert _to_seconds(chapters[0]["duration"]) == 200
    assert _to_seconds(chapters[1]["duration"]) == 100
    # cumulative startSeconds
    assert chapters[0]["startSeconds"] == 0
    assert chapters[1]["startSeconds"] == 200


def test_adjacent_same_topic_segments_merge_into_one_chapter():
    """Two segments with the same topic_key right next to each other become
    one chapter (rare but tidy)."""
    block_a = "A" * 50
    block_b = "B" * 50
    script = (
        "[[SECTION:ai]]\n" + block_a + "\n"
        + "[[SECTION:ai]]\n" + block_b + "\n"
    )
    chapters = _build_chapters_from_audio(script, total_seconds=200)
    assert chapters is not None
    assert len(chapters) == 1
    assert chapters[0]["title"] == "AI & Tech"
    # Combined ~100/100 chars of narration → full 200 seconds
    assert _to_seconds(chapters[0]["duration"]) >= 195


def _to_seconds(mmss: str) -> int:
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)
