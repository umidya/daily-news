"""Tests for self-coverage detection — the ICEF Monitor miss of 2026-08-26.

The regression these guard against is specific and worth stating: her guest
article was fetched (the feed was subscribed) and then scored out of the
briefing, because nothing told the pipeline that a piece written BY her was
worth more than a piece about anyone else.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from daily_news.config import Config, SelfEntity, Watchlist, ScoringWeights, TopicConfig
from daily_news.fetch import (
    build_self_searches,
    is_byline_outlet,
    match_self_in_page,
)
from daily_news.models import Article
from daily_news.score import (
    MATCH_BYLINE, MATCH_DOMAIN, MATCH_SEARCH, MATCH_TEXT,
    SELF_SCORE_FLOOR, detect_self_match, score_and_filter,
)


ENTITY = SelfEntity(
    org="Midya U Advisory",
    aliases=["Midya U", "Mi Dya U"],
    bylines=["Midya U"],
    domains=["midyau.com"],
    byline_outlets=["monitor.icef.com", "linkedin.com"],
)


def _article(**kw) -> Article:
    base = dict(
        url="https://example.com/a",
        canonical_url="https://example.com/a",
        url_hash="h1",
        title="A headline",
        title_normalized="a headline",
        source="Example",
        published_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        snippet="",
    )
    base.update(kw)
    return Article(**base)


# --- detection legs -----------------------------------------------------

def test_matches_firm_name_in_title():
    a = _article(title="Midya U Advisory launches AI readiness practice")
    assert detect_self_match(a, ENTITY) == ("Midya U Advisory", MATCH_TEXT)


def test_matches_byline_in_author_field():
    a = _article(title="Six enrolment gaps", author="Midya U")
    assert detect_self_match(a, ENTITY) == ("Midya U", MATCH_BYLINE)


def test_matches_owned_domain_in_url():
    a = _article(url="https://midyau.com/insights/ai-search", canonical_url="https://midyau.com/insights/ai-search")
    assert detect_self_match(a, ENTITY) == ("midyau.com", MATCH_DOMAIN)


def test_ignores_unrelated_article():
    a = _article(title="Taiwan's international enrolment up 17%", snippet="Records broken.")
    assert detect_self_match(a, ENTITY) == ("", "")


def test_name_match_is_word_boundary_anchored():
    """'Midya U' must not fire on a longer name that merely starts the same."""
    a = _article(title="Profile of Midya Underwood, registrar")
    assert detect_self_match(a, ENTITY) == ("", "")


def test_no_entity_configured_never_matches():
    a = _article(title="Midya U Advisory does a thing")
    assert detect_self_match(a, None) == ("", "")
    assert detect_self_match(a, SelfEntity()) == ("", "")


# --- the real ICEF shape ------------------------------------------------

# Verbatim shape of the 2026-08-26 RSS entry: ICEF stamps author='editor' on
# every item and truncates the summary above the byline.
ICEF_TITLE = (
    "Recruiting under Canada's international student cap: "
    "Six strategic enrolment gaps that matter"
)
ICEF_SNIPPET = (
    "Recruitment teams across Canada are working harder than they have in "
    "years and still missing their targets. The cap is not the reason."
)


def test_icef_rss_entry_alone_does_not_match():
    """Documents WHY the page-fetch tier has to exist.

    If this ever starts passing, the feed got richer and the page scan could
    in principle be narrowed — but do not remove it on this test alone.
    """
    a = _article(
        url="https://monitor.icef.com/2026/08/recruiting-under-canadas-international-student-cap-six-strategic-enrolment-gaps-that-matter/",
        title=ICEF_TITLE,
        snippet=ICEF_SNIPPET,
        source="ICEF Monitor",
        author="editor",
    )
    assert detect_self_match(a, ENTITY) == ("", "")
    assert is_byline_outlet(a.url, ENTITY) is True


def test_page_scan_catches_the_guest_byline():
    """The real attribution markup from the published article."""
    html = (
        '<div class="post_keypoints"><span class="keypoints_title">The following '
        "is a guest post contributed by Midya U of Midya U Advisory, a consultancy "
        "for post-secondary institutions.</span></div>"
    )
    assert match_self_in_page(html, ENTITY) == "Midya U Advisory"


def test_page_scan_catches_the_site_link_in_href():
    """Domains live in href attributes — tag-stripping would lose them."""
    html = '<p><em>Midya runs <a href="https://midyau.com">her firm</a>.</em></p>'
    assert match_self_in_page(html, ENTITY) == "midyau.com"


def test_page_scan_ignores_an_ordinary_article():
    html = "<p>Taiwan's international enrolment hit an all-time high of 140,420.</p>"
    assert match_self_in_page(html, ENTITY) == ""


def test_byline_outlet_gate_is_host_scoped():
    assert is_byline_outlet("https://monitor.icef.com/2026/08/x/", ENTITY) is True
    assert is_byline_outlet("https://www.monitor.icef.com/x/", ENTITY) is True
    assert is_byline_outlet("https://thepienews.com/x/", ENTITY) is False  # not listed here
    assert is_byline_outlet("https://evil.com/?monitor.icef.com", ENTITY) is False


# --- scoring ------------------------------------------------------------

def _cfg(entity: SelfEntity | None) -> Config:
    return Config(
        feeds=[],
        searches=[],
        topics={"higher_ed_canada": TopicConfig(name="higher_ed_canada", keywords=["enrolment"], negatives=[], weight=1.0)},
        scoring_weights=ScoringWeights(relevance=0.5, credibility=0.2, recency=0.2, novelty=0.1),
        recency_cutoff_hours=36,
        candidate_pool_size=60,
        target_story_count=15,
        anthropic_api_key="x",
        openai_api_key="x",
        base_url="https://example.invalid",
        watchlist=Watchlist(self_entity=entity),
    )


def test_self_article_outranks_a_perfect_ordinary_story():
    """The regression test. A stale, low-relevance self piece must still beat
    a fresh, highly-relevant ordinary one."""
    stale_self = _article(
        url_hash="self", title=ICEF_TITLE, snippet=ICEF_SNIPPET, source="ICEF Monitor",
        credibility=0.9, published_at=datetime.now(timezone.utc) - timedelta(hours=30),
    )
    stale_self.self_match = "Midya U Advisory"  # set by the page-scan tier
    perfect = _article(
        url_hash="other", title="Enrolment enrolment enrolment", snippet="enrolment",
        source="Wire", credibility=1.0, published_at=datetime.now(timezone.utc),
    )
    ranked = score_and_filter([perfect, stale_self], _cfg(ENTITY), [])
    assert ranked[0].url_hash == "self"
    assert ranked[0].score >= SELF_SCORE_FLOOR


def test_self_article_survives_the_recency_cutoff():
    """A guest piece can surface days late; 'we found it slowly' is not a
    reason to never mention it."""
    old = _article(
        url_hash="self", title="Midya U Advisory on AI readiness",
        published_at=datetime.now(timezone.utc) - timedelta(hours=200),
    )
    ranked = score_and_filter([old], _cfg(ENTITY), [])
    assert [a.url_hash for a in ranked] == ["self"]


def test_self_article_survives_the_zero_relevance_filter():
    a = _article(url_hash="self", title="Midya U Advisory", snippet="", topics=[])
    ranked = score_and_filter([a], _cfg(ENTITY), [])
    assert len(ranked) == 1
    assert ranked[0].score_breakdown["self_match"] == "Midya U Advisory"


def test_self_article_is_routed_to_the_watchlist_section():
    a = _article(url_hash="self", title="Midya U Advisory launches practice")
    ranked = score_and_filter([a], _cfg(ENTITY), [])
    assert "watchlist" in ranked[0].topics


def test_ordinary_scoring_is_untouched_when_no_self_entity():
    a = _article(url_hash="x", title="Enrolment rises", snippet="enrolment")
    ranked = score_and_filter([a], _cfg(None), [])
    assert ranked and ranked[0].score < SELF_SCORE_FLOOR
    assert "self_match" not in ranked[0].score_breakdown


# --- search construction ------------------------------------------------

def test_self_searches_cover_names_and_domains():
    searches = build_self_searches(ENTITY)
    queries = [s.query for s in searches]
    assert any('"Midya U Advisory"' in q and '"Midya U"' in q for q in queries)
    assert '"midyau.com"' in queries
    assert all("self" in s.topics and "watchlist" in s.topics for s in searches)


def test_self_searches_empty_without_entity():
    assert build_self_searches(None) == []
    assert build_self_searches(SelfEntity()) == []


# --- resurfacing already-seen coverage ----------------------------------

def test_seen_but_unused_self_article_is_resurfaced():
    """The bug that would have shipped.

    Her ICEF article was fetched on 2026-08-27 and recorded in articles.db
    with used=0. `has_seen_url` therefore skips it before scoring runs, so
    every fix downstream of dedup is dead code for the one article that
    motivated them. Verified against the production DB on the `state` branch:
    the row is there, digest_date NULL, used 0.
    """
    from daily_news.db import connect, insert_article, was_used_in_digest
    from daily_news.pipeline import partition_for_self_resurface
    import tempfile
    from pathlib import Path

    a = _article(
        url="https://monitor.icef.com/2026/08/six-gaps/",
        canonical_url="https://monitor.icef.com/2026/08/six-gaps",
        url_hash="icef1", title=ICEF_TITLE, snippet=ICEF_SNIPPET,
        source="ICEF Monitor", author="editor",
        published_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    with tempfile.TemporaryDirectory() as d:
        with connect(Path(d) / "t.db") as conn:
            insert_article(conn, a)
            assert was_used_in_digest(conn, "icef1") is False
            eligible = partition_for_self_resurface([a], conn, ENTITY)
            assert [x.url_hash for x in eligible] == ["icef1"]


def test_already_published_self_article_is_not_resurfaced():
    """Once she has been told, stop telling her."""
    from daily_news.db import connect, insert_article, mark_used_in_digest
    from daily_news.pipeline import partition_for_self_resurface
    import tempfile
    from pathlib import Path

    a = _article(
        url="https://monitor.icef.com/2026/08/six-gaps/",
        canonical_url="https://monitor.icef.com/2026/08/six-gaps",
        url_hash="icef1", title=ICEF_TITLE, source="ICEF Monitor",
        published_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    with tempfile.TemporaryDirectory() as d:
        with connect(Path(d) / "t.db") as conn:
            insert_article(conn, a)
            mark_used_in_digest(conn, ["icef1"], "2026-08-27")
            assert partition_for_self_resurface([a], conn, ENTITY) == []


def test_resurface_window_expires():
    """An old piece stops coming back rather than nagging forever."""
    from daily_news.db import connect, insert_article
    from daily_news.pipeline import partition_for_self_resurface
    import tempfile
    from pathlib import Path

    a = _article(
        url="https://monitor.icef.com/2020/01/ancient/",
        canonical_url="https://monitor.icef.com/2020/01/ancient",
        url_hash="old1", title="An old piece", source="ICEF Monitor",
        published_at=datetime.now(timezone.utc) - timedelta(days=400),
    )
    with tempfile.TemporaryDirectory() as d:
        with connect(Path(d) / "t.db") as conn:
            insert_article(conn, a)
            assert partition_for_self_resurface([a], conn, ENTITY) == []


def test_ordinary_seen_articles_are_never_resurfaced():
    """Only byline outlets are reconsidered — this is not a general re-run of
    everything the pipeline has ever seen."""
    from daily_news.db import connect, insert_article
    from daily_news.pipeline import partition_for_self_resurface
    import tempfile
    from pathlib import Path

    a = _article(
        url="https://www.bbc.co.uk/news/x", canonical_url="https://www.bbc.co.uk/news/x",
        url_hash="bbc1", title="Something else entirely", source="BBC",
        published_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    with tempfile.TemporaryDirectory() as d:
        with connect(Path(d) / "t.db") as conn:
            insert_article(conn, a)
            assert partition_for_self_resurface([a], conn, ENTITY) == []


# --- the Google News search leg -----------------------------------------

def test_google_news_self_search_result_is_matched_by_topic_tag():
    """Verified live: the query '"Midya U Advisory" OR "Midya U" OR "Mi Dya U"'
    returns her ICEF article and nothing else — but Google rewrites the link
    to a news.google.com redirect, drops the author, and replaces the summary
    with an anchor tag. Every content-based leg misses, and the host is not a
    byline outlet so the page-scan tier never fires either. The search topic
    tag is the only surviving signal.
    """
    a = _article(
        url="https://news.google.com/rss/articles/CBMiwwFBVV95cUxNMlB5",
        canonical_url="https://news.google.com/rss/articles/CBMiwwFBVV95cUxNMlB5",
        title=ICEF_TITLE,
        snippet='<a href="https://news.google.com/rss/articles/CBMi">Read</a>',
        source='Google News: "Midya U Advisory"',
        topics=["self", "watchlist"],
    )
    value, how = detect_self_match(a, ENTITY)
    assert how == MATCH_SEARCH
    assert value == "Midya U Advisory"
    assert not is_byline_outlet(a.url, ENTITY)


def test_search_topic_tag_alone_does_nothing_without_an_entity():
    a = _article(topics=["self"])
    assert detect_self_match(a, None) == ("", "")


def test_ordinary_watchlist_result_is_not_a_self_match():
    """The `watchlist` tag is on every org search; only `self` counts."""
    a = _article(title="Capilano University names new dean", topics=["watchlist", "higher_ed_canada"])
    assert detect_self_match(a, ENTITY) == ("", "")


# --- page-fetch failures are retryable, not negative ---------------------

def test_unreachable_page_is_reported_not_silently_cleared():
    """A 503 on publication morning must not become a permanent miss."""
    from unittest.mock import patch
    from daily_news.fetch import annotate_self_bylines

    a = _article(
        url="https://monitor.icef.com/2026/09/new-piece/",
        canonical_url="https://monitor.icef.com/2026/09/new-piece",
        url_hash="unreach", title="Some piece", source="ICEF Monitor",
    )
    with patch("daily_news.fetch._fetch_page_text", return_value=None):
        hits, unresolved = annotate_self_bylines([a], ENTITY)
    assert hits == 0
    assert [x.url_hash for x in unresolved] == ["unreach"]
    assert a.self_match == ""


def test_successfully_fetched_non_matching_page_is_not_unresolved():
    from unittest.mock import patch
    from daily_news.fetch import annotate_self_bylines

    a = _article(
        url="https://monitor.icef.com/2026/09/other/",
        canonical_url="https://monitor.icef.com/2026/09/other",
        url_hash="ok1", title="Taiwan enrolment", source="ICEF Monitor",
    )
    with patch("daily_news.fetch._fetch_page_text", return_value="<article>" + "x" * 600 + "Taiwan news</article>"):
        hits, unresolved = annotate_self_bylines([a], ENTITY)
    assert hits == 0 and unresolved == []


def test_forget_urls_clears_only_unused_rows():
    from daily_news.db import connect, insert_article, forget_urls, has_seen_url, mark_used_in_digest
    import tempfile
    from pathlib import Path

    unused = _article(url_hash="u1", url="https://monitor.icef.com/a", canonical_url="https://monitor.icef.com/a")
    used = _article(url_hash="u2", url="https://monitor.icef.com/b", canonical_url="https://monitor.icef.com/b")
    with tempfile.TemporaryDirectory() as d:
        with connect(Path(d) / "t.db") as conn:
            insert_article(conn, unused)
            insert_article(conn, used)
            mark_used_in_digest(conn, ["u2"], "2026-09-01")
            forget_urls(conn, ["u1", "u2"])
            assert has_seen_url(conn, "u1") is False  # re-fetched tomorrow
            assert has_seen_url(conn, "u2") is True   # already published; leave it


# --- page-scan region bounding ------------------------------------------

def test_page_scan_prefers_the_article_body_over_sidebars():
    """If an outlet ever adds a 'recent contributors' sidebar naming her,
    an unbounded scan would pin every article on that site as 'your article'."""
    from daily_news.fetch import match_self_in_page
    html = (
        "<html><aside>Recent contributors: Midya U Advisory</aside>"
        "<article>" + ("Taiwan enrolment news. " * 40) + "</article></html>"
    )
    assert match_self_in_page(html, ENTITY) == ""


def test_direct_copy_beats_the_google_news_redirect_copy():
    """The same piece arrives twice — from ICEF's feed and from the name
    search. Keep the one whose URL points at the publisher, not at a
    news.google.com redirect."""
    direct = _article(
        url="https://monitor.icef.com/2026/08/six-gaps/",
        canonical_url="https://monitor.icef.com/2026/08/six-gaps",
        url_hash="direct", title=ICEF_TITLE, source="ICEF Monitor",
    )
    direct.self_match, direct.self_match_kind = "midyau.com", "page"
    viasearch = _article(
        url="https://news.google.com/rss/articles/CBMiwwF",
        canonical_url="https://news.google.com/rss/articles/CBMiwwF",
        url_hash="search", title=ICEF_TITLE, source='Google News: "Midya U"',
        topics=["self", "watchlist"], credibility=1.0,
    )
    ranked = score_and_filter([viasearch, direct], _cfg(ENTITY), [])
    assert ranked[0].url_hash == "direct"
    assert "monitor.icef.com" in ranked[0].url
    # The redirect copy is dropped as a near-duplicate of the direct one.
    assert [a.url_hash for a in ranked] == ["direct"]
