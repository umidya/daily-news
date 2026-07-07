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


def test_recent_digest_stories_returns_marked_articles(tmp_path: Path):
    from datetime import date, timedelta

    from daily_news.db import mark_used_in_digest, recent_digest_stories

    with connect(tmp_path / "t.db") as conn:
        used = _article("Chosen for the briefing")
        skipped = _article("Fetched but never chosen")
        insert_article(conn, used)
        insert_article(conn, skipped)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        mark_used_in_digest(conn, [used.url_hash], yesterday)

        recent = recent_digest_stories(conn, days=3)
        assert recent == [
            {"date": yesterday, "title": used.title, "source": used.source}
        ]

        # Outside the window → excluded.
        old = (date.today() - timedelta(days=10)).isoformat()
        mark_used_in_digest(conn, [used.url_hash], old)
        assert recent_digest_stories(conn, days=3) == []


def test_recent_digest_stories_excludes_today_on_rerun(tmp_path: Path):
    from datetime import date

    from daily_news.db import mark_used_in_digest, recent_digest_stories

    today = date.today().isoformat()
    with connect(tmp_path / "t.db") as conn:
        art = _article("Published earlier today")
        insert_article(conn, art)
        mark_used_in_digest(conn, [art.url_hash], today)
        # A same-day force re-run must not see today's own briefing.
        assert recent_digest_stories(conn, days=3, before_date=today) == []
        # Without the bound it IS visible (tomorrow's run sees it).
        assert len(recent_digest_stories(conn, days=3)) == 1
