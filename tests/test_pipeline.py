"""Pipeline orchestration tests. No network: fetchers are monkeypatched."""
from __future__ import annotations

from datetime import datetime, timezone

from daily_news import pipeline
from daily_news.config import load_config
from daily_news.db import connect, insert_article
from daily_news.dedup import normalize_title
from daily_news.models import Article


def _article(title: str, url: str) -> Article:
    return Article(
        url=url,
        canonical_url=url,
        url_hash=url,  # tests use the URL itself as a stand-in hash
        title=title,
        title_normalized=normalize_title(title),
        source="test-source",
        published_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        snippet="snippet",
        topics=["ai"],
        credibility=0.8,
    )


def test_novelty_history_excludes_current_run(tmp_path, monkeypatch):
    """Regression: seen_titles must be read before this run's inserts.

    When the history query ran after the insert loop, every new article's own
    title (fetched_at=now) was in seen_titles, so title_similarity(x, x) == 100
    and the novelty score was 0.0 for every article on every run.
    """
    cfg = load_config()
    cfg.data_dir = tmp_path
    cfg.base_url = ""  # disables the same-day skip guard's network call

    # Simulate yesterday's run having stored an article.
    old = _article("Canada announces sweeping AI regulation framework", "https://old.example/a")
    with connect(tmp_path / "articles.db") as conn:
        insert_article(conn, old)

    fresh = _article("Entirely unrelated quantum breakthrough at UBC", "https://new.example/b")
    monkeypatch.setattr(pipeline, "fetch_feeds", lambda feeds: [fresh])
    monkeypatch.setattr(pipeline, "fetch_searches", lambda searches: [])

    captured: dict = {}
    real_score_and_filter = pipeline.score_and_filter

    def capture(articles, cfg_, seen_titles):
        captured["seen_titles"] = list(seen_titles)
        return real_score_and_filter(articles, cfg_, seen_titles)

    monkeypatch.setattr(pipeline, "score_and_filter", capture)

    pipeline.run(cfg, mode="dry")

    assert old.title_normalized in captured["seen_titles"]
    assert fresh.title_normalized not in captured["seen_titles"]
