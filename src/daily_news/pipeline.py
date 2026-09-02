from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config, load_config, watchlist_staleness_warning
from .db import (
    connect,
    has_seen_url,
    was_used_in_digest,
    insert_article,
    list_recent_digests,
    mark_used_in_digest,
    recent_digest_stories,
    record_digest,
    recent_titles,
)
from .fetch import (
    annotate_self_bylines,
    is_byline_outlet,
    combined_searches,
    fetch_feeds,
    fetch_searches,
)
from .app_export import write_app_briefing
from .render import write_digest_assets, write_index, write_podcast_feed
from .score import detect_self_match, score_and_filter
from .summarize import summarize, parse_audio_script, strip_audio_markers
from .tts import synthesize, synthesize_segments
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


# How far back to reconsider an already-seen article that might be Midya's.
# Bounded so an unpicked piece stops returning rather than nagging forever.
SELF_RESURFACE_WINDOW_DAYS = 21


def partition_for_self_resurface(
    seen: list[Article], conn, entity, now: "datetime | None" = None
) -> list[Article]:
    """Pick already-seen articles worth re-examining as possible self-coverage.

    The URL-dedup gate is normally exactly right: an article recorded once
    should never be reconsidered. But it records everything the pipeline
    *fetched*, not everything Midya was *told about*, and self-detection did
    not exist when those rows were written. Her ICEF Monitor article sits in
    the production DB fetched 2026-08-27 with used=0 — permanently invisible
    to every improvement made downstream of dedup.

    Deliberately narrow. Only articles that are (a) on a byline outlet,
    (b) never published in a digest, and (c) recent, are returned; the caller
    then page-scans them and keeps only genuine matches. Nothing else the
    pipeline has ever seen comes back.
    """
    if entity is None or not entity.is_configured():
        return []
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=SELF_RESURFACE_WINDOW_DAYS)

    out: list[Article] = []
    for art in seen:
        if not is_byline_outlet(art.url, entity):
            continue
        if art.published_at is not None and art.published_at < cutoff:
            continue
        if was_used_in_digest(conn, art.url_hash):
            continue
        out.append(art)
    return out


def run(cfg: Config | None = None, mode: str | None = None) -> dict:
    cfg = cfg or load_config()
    mode = mode or os.environ.get("DAILY_NEWS_MODE", "full")
    date_label = _today_label()
    human_label = _human_date(date_label)
    db_path = cfg.data_dir / "articles.db"

    log.info("Starting digest run for %s (mode=%s)", date_label, mode)

    # Loud on every run: a stale watchlist is silent otherwise, and silence is
    # exactly how a departed client sat on the roster from May to September.
    stale = watchlist_staleness_warning(cfg.watchlist)
    if stale:
        log.warning("STALE WATCHLIST: %s", stale)

    # Same-day skip guard: if today's briefing is already live on Pages with a
    # full-strength digest, skip this run entirely. This lets us run the cron
    # multiple times per morning (defensive against GH Actions cron flakiness)
    # without duplicate Claude+TTS calls or thinned-out re-publishes.
    if mode != "dry" and os.environ.get("DAILY_NEWS_FORCE") != "1" and cfg.base_url:
        try:
            import httpx
            r = httpx.get(f"{cfg.base_url}/today.json", timeout=10.0)
            if r.status_code == 200:
                existing = r.json()
                already_today = existing.get("dateIso") == date_label
                story_count = len(existing.get("digestStories", []) or [])
                if already_today and story_count >= 6:
                    log.info(
                        "today.json already published for %s with %d stories; skipping run. "
                        "Set DAILY_NEWS_FORCE=1 to override.",
                        date_label, story_count,
                    )
                    return {
                        "date": date_label,
                        "stories": story_count,
                        "skipped": True,
                        "reason": "already_published",
                    }
        except Exception as e:  # network blip, malformed JSON, etc — proceed with the run.
            log.info("Same-day skip guard could not verify Pages (%s); proceeding.", e)

    # 1. Fetch
    feed_articles = fetch_feeds(cfg.feeds)
    all_searches = combined_searches(cfg)
    search_articles = fetch_searches(all_searches)
    fetched: list[Article] = feed_articles + search_articles
    static_count = len(cfg.searches)
    watchlist_count = len(all_searches) - static_count
    log.info(
        "Fetched %d total items (%d feeds, %d static searches, %d watchlist searches)",
        len(fetched), len(feed_articles), static_count, watchlist_count,
    )

    # 2. Persist + dedup against history
    # Title history must be read BEFORE this run's articles are inserted:
    # every inserted row has fetched_at=now, so reading afterwards makes each
    # new article match its own title and zeroes the novelty term for the
    # entire run. In-run duplicates are still handled by score_and_filter.
    new_articles: list[Article] = []
    self_entity = cfg.watchlist.self_entity if cfg.watchlist else None
    with connect(db_path) as conn:
        seen_titles = recent_titles(conn, days=3)
        recent_coverage = recent_digest_stories(conn, days=3, before_date=date_label)
        already_seen: list[Article] = []
        for art in fetched:
            if has_seen_url(conn, art.url_hash):
                already_seen.append(art)
                continue
            insert_article(conn, art)
            new_articles.append(art)

        # Reconsider a narrow slice of already-seen articles as possible
        # self-coverage — see partition_for_self_resurface.
        revisit = partition_for_self_resurface(already_seen, conn, self_entity)
    if revisit:
        log.info("Re-examining %d already-seen article(s) for self-coverage", len(revisit))
        annotate_self_bylines(revisit, self_entity)
        resurfaced = [a for a in revisit if a.self_match]
        for a in resurfaced:
            log.info("Resurfacing previously-missed self-coverage: %s (%s)", a.title, a.self_match)
        new_articles.extend(resurfaced)

    log.info("%d new articles after URL-dedup; %d titles in 3-day history",
             len(new_articles), len(seen_titles))

    # 2b. Flag Midya's own coverage before scoring, so the score floor and the
    # recency bypass in score_and_filter can both see it. Page-level, because
    # feed metadata does not carry a guest byline.
    for art in new_articles:
        if not art.self_match:
            art.self_match = detect_self_match(art, self_entity)
    page_hits = annotate_self_bylines(new_articles, self_entity)
    if page_hits:
        log.info("%d self-coverage article(s) found via page scan", page_hits)

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

    # 4. Summarize via Claude — recent_coverage gives the model memory of the
    # last 3 briefings so it frames follow-ups as updates and skips re-covers.
    digest = summarize(candidates, cfg, human_label, recent_coverage=recent_coverage)
    if digest is None:
        log.warning("No digest produced (no candidates)")
        return {"date": date_label, "stories": 0}

    # 5. TTS — synthesize each marker-delimited segment as its own call so
    # we can measure each section's actual narrated duration. Markers are
    # stripped (per-segment, by virtue of how we slice). If the script has
    # no markers (older Claude response shape), fall back to single-pass
    # synthesis with no per-segment timings.
    audio_path = cfg.data_dir / "audio" / f"{date_label}.mp3"
    segment_timings: list[dict] | None = None
    stripped, segments = parse_audio_script(digest.audio_script)
    if segments:
        for seg in segments:
            seg["text"] = stripped[seg["start_char"]:seg["end_char"]]
        segment_timings = synthesize_segments(
            segments, audio_path, cfg.openai_api_key
        )
    else:
        log.warning(
            "audio_script has no chapter markers; falling back to single-pass TTS "
            "without measured per-segment timings."
        )
        synthesize(stripped, audio_path, cfg.openai_api_key)

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
        digest,
        date_label,
        human_label,
        audio_url,
        audio_dest,
        cfg,
        candidates=candidates,
        segment_timings=segment_timings,
    )

    log.info("Digest complete: %s (%d stories)", date_label, len(digest.chosen_url_hashes))
    return {
        "date": date_label,
        "stories": len(digest.chosen_url_hashes),
        "audio_url": audio_url,
        "html_url": html_url,
    }
