"""Emit today.json in the shape the mobile app consumes.

The Expo app (in `app/`) fetches DAILY_NEWS_BASE_URL/today.json on launch and
maps it onto the in-app `Briefing` type. Keeping this writer in the same
pipeline as the existing HTML/RSS render means a single Claude run produces
all three artifacts (web digest + podcast feed + app payload) without
re-summarizing.

Schema is mirrored from app/src/types/news.ts. Keep in lockstep when changing
either side.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config
from .summarize import Digest

log = logging.getLogger(__name__)


# Map pipeline topic_keys to the app's CategoryName values.
TOPIC_TO_CATEGORY: dict[str, str] = {
    "ai": "AI & Tech",
    "marketing": "Marketing",
    "higher_ed_canada": "Higher Ed",
    "higher_ed_global": "Higher Ed",
    "intl_students_canada": "Higher Ed",
    "canadian_real_estate": "Real Estate",
    "kamloops_sun_peaks": "Canada & BC",
    "airbnb_policy": "AirBnb Policy",
    "global_business_tech": "Business",
    "bc_food_recalls": "Canada & BC",
}

# Map pipeline topic_keys to the app's StoryThumbnail kinds.
TOPIC_TO_THUMBNAIL: dict[str, str] = {
    "ai": "chip",
    "marketing": "megaphone",
    "higher_ed_canada": "university",
    "higher_ed_global": "university",
    "intl_students_canada": "university",
    "canadian_real_estate": "house",
    "kamloops_sun_peaks": "mountains",
    "airbnb_policy": "house",
    "global_business_tech": "bars",
    "bc_food_recalls": "leaf",
}


# OpenAI tts-1-hd outputs MP3 at ~96 kbps mono → ~12 KB/sec.
# Used as a fallback when mutagen isn't available.
_BYTES_PER_SECOND_ESTIMATE = 12000


def _estimate_audio_seconds(mp3_path: Path) -> int:
    """Best-effort duration in seconds. Tries mutagen, falls back to filesize."""
    try:
        from mutagen.mp3 import MP3  # type: ignore[import-not-found]

        return int(MP3(str(mp3_path)).info.length)
    except Exception:
        try:
            return int(mp3_path.stat().st_size / _BYTES_PER_SECOND_ESTIMATE)
        except Exception:
            return 600  # 10 min default


def _format_mmss(total_seconds: int) -> str:
    m, s = divmod(max(0, total_seconds), 60)
    return f"{m}:{s:02d}"


def _hook_from_script(script: str) -> str:
    """First sentence of the audio script, lightly cleaned."""
    if not script:
        return "Your personalized morning news briefing"
    first = re.split(r"(?<=[.!?])\s+", script.strip())[0]
    first = first.strip()
    if len(first) > 140:
        first = first[:137].rstrip() + "…"
    return first


def _intro_from_why(why: str) -> str:
    """Short intro paragraph for the Digest screen — first 2-3 sentences."""
    if not why:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", why.strip())
    return " ".join(sentences[:3]).strip()


def _reading_time(stories_count: int) -> str:
    """Rough estimate: ~30 sec per story summary."""
    minutes = max(2, round(stories_count * 0.5))
    return f"{minutes} min read"


def _section_duration(stories_count: int, total_seconds: int, total_stories: int) -> str:
    if total_stories <= 0:
        return _format_mmss(0)
    section_seconds = int(total_seconds * (stories_count / total_stories))
    return _format_mmss(section_seconds)


def _story_to_app(story: dict, topic_key: str, idx: int) -> dict:
    return {
        "id": f"story-{topic_key}-{idx}",
        "category": TOPIC_TO_CATEGORY.get(topic_key, "Global"),
        "headline": story.get("headline", "").strip(),
        "summary": story.get("summary", "").strip(),
        "source": story.get("source", "").strip(),
        "url": story.get("url", ""),
        "readingTime": "2 min read",
        "audioSegmentLength": "—",
        "thumbnailKind": TOPIC_TO_THUMBNAIL.get(topic_key, "globe"),
    }


def build_app_payload(
    digest: Digest,
    date_label: str,
    human_label: str,
    audio_url: str,
    audio_path: Path,
) -> dict:
    """Build the app-shaped Briefing payload from a pipeline Digest."""
    total_seconds = _estimate_audio_seconds(audio_path)
    total_duration = _format_mmss(total_seconds)

    # Flatten stories with topic_key context preserved.
    sections = digest.sections or []
    flat_stories: list[dict] = []
    for section in sections:
        topic_key = section.get("topic_key", "global_business_tech")
        for i, story in enumerate(section.get("stories", [])):
            flat_stories.append(_story_to_app(story, topic_key, i))

    total_story_count = max(1, len(flat_stories))

    # Audio chapters mirror sections.
    chapters = []
    for i, section in enumerate(sections):
        topic_key = section.get("topic_key", "global_business_tech")
        section_stories = section.get("stories", [])
        chapters.append(
            {
                "id": f"c{i + 1}",
                "title": TOPIC_TO_CATEGORY.get(topic_key, "Global"),
                "duration": _section_duration(
                    len(section_stories), total_seconds, total_story_count
                ),
            }
        )

    top_stories = flat_stories[:3]
    digest_stories = flat_stories[:8]
    up_next = flat_stories[0] if flat_stories else None

    return {
        "schemaVersion": 1,
        "date": human_label,
        "dateIso": date_label,
        "greeting": "Good morning, Midya",
        "totalDuration": total_duration,
        "currentTime": "0:00",
        "remaining": f"{total_seconds // 60} min total",
        "hookCopy": _hook_from_script(digest.audio_script),
        "digestIntro": _intro_from_why(digest.why_this_matters),
        "digestReadingTime": _reading_time(len(flat_stories)),
        "whyItMatters": digest.why_this_matters.strip(),
        "audioUrl": audio_url,
        "audioDurationSeconds": total_seconds,
        "topStories": top_stories,
        "digestStories": digest_stories,
        "audioChapters": chapters,
        "upNext": up_next,
    }


def write_app_briefing(
    digest: Digest,
    date_label: str,
    human_label: str,
    audio_url: str,
    audio_path: Path,
    cfg: Config,
) -> tuple[Path, Path]:
    """Write today.json (latest) and briefings/<date>.json (archive). Returns
    both paths."""
    payload = build_app_payload(digest, date_label, human_label, audio_url, audio_path)

    public = cfg.public_dir
    public.mkdir(parents=True, exist_ok=True)
    archive_dir = public / "briefings"
    archive_dir.mkdir(parents=True, exist_ok=True)

    today_path = public / "today.json"
    archive_path = archive_dir / f"{date_label}.json"

    body = json.dumps(payload, ensure_ascii=False, indent=2)
    today_path.write_text(body, encoding="utf-8")
    archive_path.write_text(body, encoding="utf-8")

    log.info("App briefing JSON written to %s and %s", today_path, archive_path)
    return today_path, archive_path
