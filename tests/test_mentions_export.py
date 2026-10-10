"""mentions.json feeds the cloud Mention Alert routine, which emails Midya the
moment the pipeline sees her name or firm. The file is published to the PUBLIC
gh-pages site, so it must never carry the matched alias (that can be her legal
name, which is why config/self.yaml is gitignored)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from daily_news.app_export import write_mentions
from daily_news.models import Article


def _article(**kw) -> Article:
    base = dict(
        url="https://example.com/a",
        canonical_url="https://example.com/a",
        url_hash="h1",
        title="A headline",
        title_normalized="a headline",
        source="Example",
        published_at=datetime(2026, 10, 9, 15, 0, tzinfo=timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        snippet="",
    )
    base.update(kw)
    return Article(**base)


def _cfg(tmp_path):
    return SimpleNamespace(public_dir=tmp_path)


def test_writes_only_self_matches(tmp_path):
    hit = _article(url="https://monitor.icef.com/x", url_hash="h2", title="Guest post",
                   source="ICEF Monitor", self_match="Midya U", self_match_kind="page")
    miss = _article()
    path = write_mentions([hit, miss], "2026-10-10", _cfg(tmp_path))
    data = json.loads(path.read_text())
    assert data["dateIso"] == "2026-10-10"
    assert len(data["mentions"]) == 1
    m = data["mentions"][0]
    assert m["url"] == "https://monitor.icef.com/x"
    assert m["source"] == "ICEF Monitor"
    assert m["matchedVia"] == "page"
    assert m["published"].startswith("2026-10-09")


def test_never_publishes_the_matched_alias(tmp_path):
    hit = _article(self_match="Mi Dya U", self_match_kind="text")
    path = write_mentions([hit], "2026-10-10", _cfg(tmp_path))
    assert "Mi Dya U" not in path.read_text()


def test_empty_file_written_when_no_mentions(tmp_path):
    """An empty list tells the routine 'checked, nothing found' — distinct from
    a missing or stale file, which means the pipeline did not run."""
    path = write_mentions([_article()], "2026-10-10", _cfg(tmp_path))
    assert json.loads(path.read_text()) == {"dateIso": "2026-10-10", "mentions": []}


def test_deduplicates_by_url(tmp_path):
    a = _article(self_match="Midya U", self_match_kind="search")
    b = _article(url_hash="h9", self_match="Midya U", self_match_kind="text")
    path = write_mentions([a, b], "2026-10-10", _cfg(tmp_path))
    assert len(json.loads(path.read_text())["mentions"]) == 1
