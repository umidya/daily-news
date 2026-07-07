from datetime import datetime, timezone
from pathlib import Path

from daily_news.db import (
    connect,
    has_seen_url,
    insert_article,
    list_recent_digests,
    record_digest,
    recent_titles,
)
from daily_news.dedup import canonicalize_url, normalize_title, url_hash
from daily_news.models import Article


def _article(title: str = "Test article") -> Article:
    url = f"https://example.com/{title.replace(' ', '-')}"
    canonical = canonicalize_url(url)
    return Article(
        url=url,
        canonical_url=canonical,
        url_hash=url_hash(canonical),
        title=title,
        title_normalized=normalize_title(title),
        source="Test",
        published_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        snippet="",
        topics=["ai"],
        credibility=0.9,
        score=0.5,
    )


def test_insert_and_dedup_url(tmp_path: Path):
    db = tmp_path / "test.db"
    art = _article()
    with connect(db) as conn:
        assert not has_seen_url(conn, art.url_hash)
        insert_article(conn, art)
        assert has_seen_url(conn, art.url_hash)
        # Insert again - should be a no-op
        insert_article(conn, art)
    with connect(db) as conn:
        rows = conn.execute("SELECT COUNT(*) AS n FROM articles").fetchone()
        assert rows["n"] == 1


def test_recent_titles_filters_by_window(tmp_path: Path):
    db = tmp_path / "test.db"
    art = _article("Bank of Canada holds rate")
    with connect(db) as conn:
        insert_article(conn, art)
        titles = recent_titles(conn, days=3)
    assert normalize_title("Bank of Canada holds rate") in titles


def test_record_digest_and_list(tmp_path: Path):
    db = tmp_path / "test.db"
    with connect(db) as conn:
        record_digest(conn, "2026-04-27", "audio/2026-04-27.mp3",
                      "digests/2026-04-27.html", 10)
        record_digest(conn, "2026-04-26", "audio/2026-04-26.mp3",
                      "digests/2026-04-26.html", 8)
    with connect(db) as conn:
        rows = list_recent_digests(conn)
    assert [r["digest_date"] for r in rows] == ["2026-04-27", "2026-04-26"]
    assert rows[0]["story_count"] == 10
