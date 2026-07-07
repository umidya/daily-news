from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from .models import Article


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url_hash TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL,
    original_url TEXT NOT NULL,
    title TEXT NOT NULL,
    title_normalized TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    snippet TEXT,
    topics TEXT,
    credibility REAL,
    score REAL,
    digest_date TEXT,
    used INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_articles_fetched_at ON articles(fetched_at);
CREATE INDEX IF NOT EXISTS idx_articles_digest_date ON articles(digest_date);
CREATE INDEX IF NOT EXISTS idx_articles_title_norm ON articles(title_normalized);

CREATE TABLE IF NOT EXISTS digests (
    digest_date TEXT PRIMARY KEY,
    audio_path TEXT,
    html_path TEXT,
    story_count INTEGER,
    run_at TEXT NOT NULL,
    duration_seconds INTEGER
);
"""


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def has_seen_url(conn: sqlite3.Connection, url_hash: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM articles WHERE url_hash = ?", (url_hash,)
    ).fetchone()
    return row is not None


def recent_titles(conn: sqlite3.Connection, days: int = 3) -> list[str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT title_normalized FROM articles WHERE fetched_at >= ?",
        (cutoff,),
    ).fetchall()
    return [r["title_normalized"] for r in rows]


def insert_article(conn: sqlite3.Connection, art: Article) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO articles (
            url_hash, canonical_url, original_url, title, title_normalized,
            source, published_at, fetched_at, snippet, topics, credibility, score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            art.url_hash,
            art.canonical_url,
            art.url,
            art.title,
            art.title_normalized,
            art.source,
            art.published_at.isoformat() if art.published_at else None,
            art.fetched_at.isoformat(),
            art.snippet,
            ",".join(art.topics),
            art.credibility,
            art.score,
        ),
    )


def mark_used_in_digest(
    conn: sqlite3.Connection, url_hashes: list[str], digest_date: str
) -> None:
    conn.executemany(
        "UPDATE articles SET digest_date = ?, used = 1 WHERE url_hash = ?",
        [(digest_date, h) for h in url_hashes],
    )


def record_digest(
    conn: sqlite3.Connection,
    digest_date: str,
    audio_path: str,
    html_path: str,
    story_count: int,
    duration_seconds: int = 0,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO digests
            (digest_date, audio_path, html_path, story_count, run_at, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            digest_date,
            audio_path,
            html_path,
            story_count,
            datetime.now(timezone.utc).isoformat(),
            duration_seconds,
        ),
    )


def list_recent_digests(conn: sqlite3.Connection, limit: int = 30) -> list[dict]:
    rows = conn.execute(
        "SELECT digest_date, audio_path, html_path, story_count, run_at, duration_seconds "
        "FROM digests ORDER BY digest_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
