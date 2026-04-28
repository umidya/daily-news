from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config, load_config
from .db import (
    connect,
    has_seen_url,
    insert_article,
    list_recent_digests,
    mark_used_in_digest,
    record_digest,
    recent_titles,
)
from .fetch import fetch_feeds, fetch_searches
from .app_export import write_app_briefing
from .render import write_digest_assets, write_index, write_podcast_feed
from .score import score_and_filter
from .summarize import summarize
from .tts import synthesize
from .models import Article

log = logging.getLogger(__name__)

PT = ZoneInfo("America/Vancouver")


def _today_label() -> str:
    override = os.environ.get("DAILY_NEWS_DATE")
    if override:
        return override
    return datetime.now(PT).strftime("%Y-%m-%d")


def _human_date(label: str) -> str:
    return datetime.strptime(label, "%Y-%m-%d").strftime("%A, %B %-d, %Y")


def run(cfg: Config | None = None, mode: str | None = None) -> dict:
    cfg = cfg or load_config()
    mode = mode or os.environ.get("DAILY_NEWS_MODE", "full")
    date_label = _today_label()
    human_label = _human_date(date_label)
    db_path = cfg.data_dir / "articles.db"

    log.info("Starting digest run for %s (mode=%s)", date_label, mode)

    # 1. Fetch
    feed_articles = fetch_feeds(cfg.feeds)
    search_articles = fetch_searches(cfg.searches)
    fetched: list[Article] = feed_articles + search_articles
    log.info("Fetched %d total items (%d feeds, %d searches)",
             len(fetched), len(feed_articles), len(search_articles))

    # 2. Persist + dedup against history
    new_articles: list[Article] = []
    with connect(db_path) as conn:
        for art in fetched:
            if has_seen_url(conn, art.url_hash):
                continue
            insert_article(conn, art)
            new_articles.append(art)
        seen_titles = recent_titles(conn, days=3)

    log.info("%d new articles after URL-dedup; %d titles in 3-day history",
             len(new_articles), len(seen_titles))

    # 3. Score + filter
    ranked = score_and_filter(new_articles, cfg, seen_titles)
    log.info("%d articles after scoring + in-run dedup", len(ranked))

    candidates = ranked[: cfg.candidate_pool_size]

    if mode == "dry":
        log.info("Dry mode: skipping LLM/TTS. Top candidates:")
        for a in candidates[:15]:
            log.info("  %.3f %s | %s", a.score, a.source, a.title)
        return {
            "date": date_label,
            "candidates": [
                {"score": a.score, "title": a.title, "source": a.source, "url": a.url}
                for a in candidates
            ],
        }

    # 4. Summarize via Claude
    digest = summarize(candidates, cfg, human_label)
    if digest is None:
        log.warning("No digest produced (no candidates)")
        return {"date": date_label, "stories": 0}

    # 5. TTS
    audio_path = cfg.data_dir / "audio" / f"{date_label}.mp3"
    synthesize(digest.audio_script, audio_path, cfg.openai_api_key)

    # 6. Render HTML, copy audio, record state, build feed + index
    audio_dest, html_dest, audio_url, html_url = write_digest_assets(
        digest, audio_path, date_label, cfg
    )

    with connect(db_path) as conn:
        mark_used_in_digest(conn, digest.chosen_url_hashes, date_label)
        record_digest(
            conn,
            date_label,
            audio_path=str(audio_dest.relative_to(cfg.public_dir)),
            html_path=str(html_dest.relative_to(cfg.public_dir)),
            story_count=sum(len(s.get("stories", [])) for s in digest.sections),
        )
        digest_rows = list_recent_digests(conn, limit=60)

    # Build episode list for feed + index
    episodes = []
    for row in digest_rows:
        d = row["digest_date"]
        ap = cfg.public_dir / row["audio_path"]
        hp = cfg.public_dir / row["html_path"]
        if not ap.exists():
            continue
        a_url = f"{cfg.base_url}/{row['audio_path']}" if cfg.base_url else f"/{row['audio_path']}"
        h_url = f"{cfg.base_url}/{row['html_path']}" if cfg.base_url else f"/{row['html_path']}"
        episodes.append({
            "digest_date": d,
            "title": f"Daily News for {_human_date(d)}",
            "description": (digest.why_this_matters[:280] + "...") if d == date_label else f"{row['story_count']} stories.",
            "audio_url": a_url,
            "html_url": h_url,
            "audio_path": ap,
            "story_count": row["story_count"],
            "published": datetime.strptime(d, "%Y-%m-%d").replace(hour=14, tzinfo=timezone.utc),
        })

    write_podcast_feed(episodes, cfg)
    write_index(episodes, cfg)
    write_app_briefing(
        digest, date_label, human_label, audio_url, audio_dest, cfg, candidates=candidates
    )

    log.info("Digest complete: %s (%d stories)", date_label, len(digest.chosen_url_hashes))
    return {
        "date": date_label,
        "stories": len(digest.chosen_url_hashes),
        "audio_url": audio_url,
        "html_url": html_url,
    }
