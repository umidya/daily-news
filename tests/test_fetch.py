"""Tests for fetch.py — focused on the deterministic, no-network bits.

The network-fetching paths (fetch_feeds, fetch_searches, fetch_og_image) are
exercised in integration; these unit tests cover the pure helpers."""
from daily_news.config import (
    Config,
    ScoringWeights,
    Watchlist,
    WatchlistOrg,
)
from daily_news.fetch import build_watchlist_searches, combined_searches


def _client(org: str, industry: str = "", aliases=None) -> WatchlistOrg:
    return WatchlistOrg(
        org=org,
        aliases=list(aliases or []),
        industry=industry,
        posture="active",
    )


def _prospect(org: str, industry: str = "") -> WatchlistOrg:
    return WatchlistOrg(org=org, industry=industry, stage="discovery")


def _peer(org: str, industry: str = "") -> WatchlistOrg:
    return WatchlistOrg(org=org, industry=industry, relationship="consortium_peer")


def test_single_client_produces_one_quoted_query():
    wl = Watchlist(clients=[_client("Capilano University", "higher_ed_canada")])
    searches = build_watchlist_searches(wl)
    assert len(searches) == 1
    s = searches[0]
    assert s.query == '"Capilano University"'
    assert "watchlist" in s.topics
    assert "higher_ed_canada" in s.topics


def test_aliases_grouped_into_single_or_query():
    wl = Watchlist(clients=[
        _client("Mogul Realty Group", "canadian_real_estate", aliases=["Mogul RG"])
    ])
    searches = build_watchlist_searches(wl)
    assert len(searches) == 1
    assert searches[0].query == '"Mogul Realty Group" OR "Mogul RG"'


def test_empty_industry_yields_watchlist_topic_only():
    wl = Watchlist(peer_orgs=[_peer("AACRAO")])
    searches = build_watchlist_searches(wl)
    assert searches[0].topics == ["watchlist"]


def test_priority_order_clients_prospects_peers():
    wl = Watchlist(
        clients=[_client("ClientA")],
        prospects=[_prospect("ProspectA")],
        peer_orgs=[_peer("PeerA")],
    )
    searches = build_watchlist_searches(wl)
    queries = [s.query for s in searches]
    assert queries == ['"ClientA"', '"ProspectA"', '"PeerA"']


def test_cap_drops_lowest_priority_first():
    """When cap forces a cut, peers go first, then prospects. Clients survive."""
    wl = Watchlist(
        clients=[_client(f"C{i}") for i in range(5)],
        prospects=[_prospect(f"P{i}") for i in range(5)],
        peer_orgs=[_peer(f"X{i}") for i in range(5)],
    )
    searches = build_watchlist_searches(wl, cap=7)
    assert len(searches) == 7
    queries = [s.query for s in searches]
    # All 5 clients survive
    for i in range(5):
        assert f'"C{i}"' in queries
    # 2 prospects survive (the first two added)
    assert '"P0"' in queries
    assert '"P1"' in queries
    # No peers — all dropped
    for i in range(5):
        assert f'"X{i}"' not in queries


def test_empty_watchlist_returns_empty_list():
    assert build_watchlist_searches(Watchlist()) == []


def test_credibility_is_google_news_default():
    """Matches the existing config/searches.yaml convention for Google News."""
    wl = Watchlist(clients=[_client("Anywhere", "ai")])
    s = build_watchlist_searches(wl)[0]
    assert s.credibility == 0.70


def test_each_org_searched_once_even_if_appears_twice():
    """If the same org accidentally lands in two lists, dedup by canonical name."""
    wl = Watchlist(
        clients=[_client("Org A", "ai")],
        prospects=[_prospect("Org A", "ai")],
    )
    searches = build_watchlist_searches(wl)
    queries = [s.query for s in searches]
    assert queries.count('"Org A"') == 1


def _minimal_cfg(searches, watchlist=None) -> Config:
    """Build the bare minimum Config for combined_searches tests."""
    return Config(
        feeds=[],
        searches=searches,
        topics={},
        scoring_weights=ScoringWeights(relevance=0.5, credibility=0.2, recency=0.15, novelty=0.15),
        recency_cutoff_hours=36,
        candidate_pool_size=40,
        target_story_count=16,
        anthropic_api_key="",
        openai_api_key="",
        base_url="",
        watchlist=watchlist,
    )


def test_combined_searches_returns_static_alone_when_no_watchlist():
    from daily_news.config import SearchConfig
    static = [SearchConfig(query="thing", topics=["ai"], credibility=0.7)]
    cfg = _minimal_cfg(searches=static, watchlist=None)
    assert combined_searches(cfg) == static


def test_combined_searches_appends_watchlist_searches():
    from daily_news.config import SearchConfig
    static = [SearchConfig(query="static", topics=["ai"], credibility=0.7)]
    wl = Watchlist(clients=[_client("Capilano University", "higher_ed_canada")])
    cfg = _minimal_cfg(searches=static, watchlist=wl)
    out = combined_searches(cfg)
    assert len(out) == 2
    queries = [s.query for s in out]
    assert "static" in queries
    assert '"Capilano University"' in queries
