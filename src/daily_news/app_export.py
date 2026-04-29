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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config
from .fetch import fetch_og_image
from .models import Article
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
    "kamloops_sun_peaks": "Local News",
    "airbnb_policy": "AirBnb Policy",
    "global_business_tech": "Global",
    "longevity": "Longevity",
    "misc": "Misc",
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
    "global_business_tech": "globe",
    "longevity": "leaf",
    "misc": "bars",
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


def _story_to_app(story: dict, topic_key: str, idx: int, image_url: Optional[str]) -> dict:
    out = {
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
    if image_url:
        out["imageUrl"] = image_url
    return out


def _resolve_image_urls(
    chosen_urls: list[str],
    candidates: list[Article],
    max_workers: int = 6,
) -> dict[str, Optional[str]]:
    """Build a `url -> image_url` map for the URLs Claude picked.

    Falls back to fetching og:image only for chosen stories that didn't have
    an image in the RSS entry. Caps at ~12 HTTP requests/run.
    """
    by_url: dict[str, Optional[str]] = {}
    needs_scrape: list[str] = []
    candidate_by_url = {a.url: a for a in candidates}
    for url in chosen_urls:
        art = candidate_by_url.get(url)
        if art and art.image_url:
            by_url[url] = art.image_url
        else:
            by_url[url] = None
            needs_scrape.append(url)

    if not needs_scrape:
        return by_url

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_url = {ex.submit(fetch_og_image, u): u for u in needs_scrape}
        for fut in as_completed(future_to_url):
            url = future_to_url[fut]
            try:
                by_url[url] = fut.result()
            except Exception:
                by_url[url] = None
    return by_url


def build_app_payload(
    digest: Digest,
    date_label: str,
    human_label: str,
    audio_url: str,
    audio_path: Path,
    candidates: Optional[list[Article]] = None,
) -> dict:
    """Build the app-shaped Briefing payload from a pipeline Digest."""
    total_seconds = _estimate_audio_seconds(audio_path)
    total_duration = _format_mmss(total_seconds)

    # Look up images for each chosen story (RSS first, og:image fallback).
    chosen_urls: list[str] = []
    for section in digest.sections or []:
        for story in section.get("stories", []):
            if story.get("url"):
                chosen_urls.append(story["url"])
    image_by_url = _resolve_image_urls(chosen_urls, candidates or [])

    # Flatten stories with topic_key context preserved.
    sections = digest.sections or []
    flat_stories: list[dict] = []
    for section in sections:
        topic_key = section.get("topic_key", "global_business_tech")
        for i, story in enumerate(section.get("stories", [])):
            img = image_by_url.get(story.get("url", ""))
            flat_stories.append(_story_to_app(story, topic_key, i, img))

    total_story_count = max(1, len(flat_stories))

    # Audio chapters mirror sections; cumulative startSeconds lets the app
    # seek the audio to that chapter.
    chapters = []
    cumulative = 0
    for i, section in enumerate(sections):
        topic_key = section.get("topic_key", "global_business_tech")
        section_stories = section.get("stories", [])
        duration_str = _section_duration(
            len(section_stories), total_seconds, total_story_count
        )
        chapters.append(
            {
                "id": f"c{i + 1}",
                "title": TOPIC_TO_CATEGORY.get(topic_key, "Global"),
                "duration": duration_str,
                "startSeconds": cumulative,
            }
        )
        # Add this chapter's seconds onto the running total.
        m, s = duration_str.split(":")
        cumulative += int(m) * 60 + int(s)

    top_stories = flat_stories[:3]
    digest_stories = flat_stories[:20]
    up_next = flat_stories[1] if len(flat_stories) > 1 else (flat_stories[0] if flat_stories else None)

    # Hero / "main story of the day" = first story Claude placed in the first
    # section. Fall back to the first story that has an image.
    main_story = flat_stories[0] if flat_stories else None
    hero_image_url: Optional[str] = None
    if main_story and main_story.get("imageUrl"):
        hero_image_url = main_story["imageUrl"]
    else:
        for s in flat_stories:
            if s.get("imageUrl"):
                hero_image_url = s["imageUrl"]
                break

    payload: dict = {
        "schemaVersion": 2,
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
        "audioScript": digest.audio_script.strip(),
        "topStories": top_stories,
        "digestStories": digest_stories,
        "audioChapters": chapters,
        "upNext": up_next,
        "mainStory": main_story,
    }
    if hero_image_url:
        payload["heroImageUrl"] = hero_image_url
    return payload


def write_app_briefing(
    digest: Digest,
    date_label: str,
    human_label: str,
    audio_url: str,
    audio_path: Path,
    cfg: Config,
    candidates: Optional[list[Article]] = None,
) -> tuple[Path, Path]:
    """Write today.json (latest) and briefings/<date>.json (archive). Returns
    both paths."""
    payload = build_app_payload(
        digest, date_label, human_label, audio_url, audio_path, candidates=candidates
    )

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
