import textwrap

from daily_news.config import load_config, load_watchlist


def test_load_config_succeeds():
    cfg = load_config()
    assert len(cfg.feeds) > 0
    assert len(cfg.searches) > 0
    assert "ai" in cfg.topics
    assert "kamloops_sun_peaks" in cfg.topics
    assert "misc" in cfg.topics
    assert cfg.scoring_weights.relevance > 0
    assert cfg.target_story_count > 0


def test_topic_keywords_lowercased():
    cfg = load_config()
    for topic in cfg.topics.values():
        for kw in topic.keywords:
            assert kw == kw.lower()


def test_watchlist_topic_present_and_boosted():
    """The watchlist topic ensures stories about Midya's clients/prospects/peers
    clear the candidate pool. Weight must exceed 1.0 to beat baseline topics."""
    cfg = load_config()
    assert "watchlist" in cfg.topics
    assert cfg.topics["watchlist"].weight > 1.0


def test_load_watchlist_parses_clients_prospects_peers_and_themes(tmp_path):
    path = tmp_path / "watchlist.yaml"
    path.write_text(textwrap.dedent("""
        generated_at: "2026-05-21T18:00:00-07:00"
        clients:
          - org: "Capilano University"
            aliases: ["CapU"]
            industry: higher_ed_canada
            posture: active
            notes: "SEM pilot"
          - org: "Mogul Realty Group"
            aliases: ["Mogul RG"]
            industry: canadian_real_estate
            posture: active
        prospects:
          - org: "Some Prospect U"
            industry: higher_ed_canada
            stage: discovery
        peer_orgs:
          - org: "AACRAO"
            relationship: consortium_peer
        thought_leadership_themes:
          - "AI in marketing operations"
          - "Public-institution AI governance"
    """))
    wl = load_watchlist(path)
    assert wl is not None
    assert wl.generated_at == "2026-05-21T18:00:00-07:00"
    assert [c.org for c in wl.clients] == ["Capilano University", "Mogul Realty Group"]
    assert wl.clients[0].aliases == ["CapU"]
    assert wl.clients[0].industry == "higher_ed_canada"
    assert wl.clients[0].posture == "active"
    assert wl.prospects[0].stage == "discovery"
    assert wl.peer_orgs[0].relationship == "consortium_peer"
    assert "AI in marketing operations" in wl.thought_leadership_themes


def test_load_watchlist_returns_none_when_file_missing(tmp_path):
    """Pipeline must still run when watchlist.yaml hasn't been generated yet."""
    assert load_watchlist(tmp_path / "does-not-exist.yaml") is None


def test_load_watchlist_returns_none_when_yaml_is_garbage(tmp_path):
    """Malformed YAML must not crash the pipeline — log + treat as absent."""
    path = tmp_path / "watchlist.yaml"
    path.write_text("this is :: not :: valid :: yaml: [[[")
    assert load_watchlist(path) is None


def test_load_watchlist_tolerates_empty_sections(tmp_path):
    """A freshly-synced watchlist with no leads yet must still parse."""
    path = tmp_path / "watchlist.yaml"
    path.write_text(textwrap.dedent("""
        clients: []
        prospects: []
        peer_orgs: []
        thought_leadership_themes: []
    """))
    wl = load_watchlist(path)
    assert wl is not None
    assert wl.clients == []
    assert wl.prospects == []


def test_load_config_includes_watchlist_field():
    """load_config exposes cfg.watchlist (may be None if file doesn't exist)."""
    cfg = load_config()
    # We don't assert it's populated — the watchlist file may not exist yet.
    # Just that the attribute is on the Config object.
    assert hasattr(cfg, "watchlist")
