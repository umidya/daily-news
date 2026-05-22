"""Tests for the watchlist sync script.

The Notion API call is the only thing that touches the network — covered via
injected fetcher functions that the tests stub. Everything else is pure file I/O
against tmp_path fixtures."""
from pathlib import Path

import pytest
import yaml

from daily_news.config import WatchlistOrg
from daily_news.sync_watchlist import (
    build_watchlist_from_sources,
    classify_industry_from_text,
    extract_client_from_folder,
    write_watchlist_yaml,
)


# ----- extract_client_from_folder ----------------------------------------

def test_extracts_org_name_from_first_h1(tmp_path):
    folder = tmp_path / "Capilano University"
    folder.mkdir()
    (folder / "CLAUDE.md").write_text(
        "# Capilano University — Client File\n\n## Status\nSome content..."
    )
    org = extract_client_from_folder(folder)
    assert org is not None
    assert org.org == "Capilano University"


def test_strips_trailing_qualifier_from_h1():
    """An H1 like '# Mogul Realty Group (Mogul RG) — Client File' should
    extract just the primary name; aliases come from a separate pattern."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        folder = Path(td) / "Mogul RG"
        folder.mkdir()
        (folder / "CLAUDE.md").write_text(
            "# Mogul Realty Group (Mogul RG) — Client File\n\nSome content"
        )
        org = extract_client_from_folder(folder)
        assert org is not None
        assert org.org == "Mogul Realty Group"
        assert "Mogul RG" in org.aliases


def test_returns_none_when_no_claude_md(tmp_path):
    folder = tmp_path / "EmptyFolder"
    folder.mkdir()
    assert extract_client_from_folder(folder) is None


def test_returns_none_when_no_h1(tmp_path):
    """If the CLAUDE.md doesn't start with a heading, we can't reliably
    extract the org name; skip with a warning rather than guessing."""
    folder = tmp_path / "Weird"
    folder.mkdir()
    (folder / "CLAUDE.md").write_text("Just some text with no heading.")
    assert extract_client_from_folder(folder) is None


def test_nested_subfolder_with_claude_md_uses_top_folder_as_org_name(tmp_path):
    """Some client folders nest the CLAUDE.md inside an individual-contact
    subfolder (e.g., 'Cushman & Wakefield Edmonton/Ian Newman/CLAUDE.md').
    In that case the org is the company (top folder), not the person."""
    folder = tmp_path / "Cushman & Wakefield Edmonton"
    folder.mkdir()
    contact = folder / "Ian Newman"
    contact.mkdir()
    (contact / "CLAUDE.md").write_text(
        "# Ian Newman (Cushman & Wakefield Edmonton) — Client File\n\n"
        "Commercial investment sales multifamily capital markets institutional"
    )
    org = extract_client_from_folder(folder)
    assert org is not None
    assert org.org == "Cushman & Wakefield Edmonton"
    assert org.industry == "canadian_real_estate"


def test_classifies_industry_from_body_keywords(tmp_path):
    folder = tmp_path / "TestU"
    folder.mkdir()
    (folder / "CLAUDE.md").write_text(
        "# Test University — Client File\n\n"
        "Public post-secondary institution. SEM lifecycle work, enrolment "
        "planning, international students, Canadian higher education."
    )
    org = extract_client_from_folder(folder)
    assert org is not None
    assert org.industry == "higher_ed_canada"


# ----- classify_industry_from_text --------------------------------------

def test_classifies_higher_ed_canada_from_signals():
    text = "Public university enrolment SEM lifecycle Canadian post-secondary"
    assert classify_industry_from_text(text) == "higher_ed_canada"


def test_classifies_real_estate_from_signals():
    text = "Real estate brokerage Edmonton Vancouver residential agent recruitment"
    assert classify_industry_from_text(text) == "canadian_real_estate"


def test_classifies_commercial_real_estate_under_real_estate_bucket():
    text = (
        "Commercial investment sales multifamily capital markets institutional "
        "Cushman Wakefield"
    )
    assert classify_industry_from_text(text) == "canadian_real_estate"


def test_classify_returns_empty_string_when_no_signal():
    assert classify_industry_from_text("Lorem ipsum nothing here") == ""


# ----- build_watchlist_from_sources -------------------------------------

def _make_client(tmp_path: Path, folder_name: str, body: str) -> Path:
    folder = tmp_path / folder_name
    folder.mkdir()
    (folder / "CLAUDE.md").write_text(body)
    return folder


def test_build_watchlist_pulls_clients_and_handles_no_notion(tmp_path):
    clients_dir = tmp_path / "Clients"
    clients_dir.mkdir()
    _make_client(
        tmp_path / "Clients",
        "Capilano University",
        "# Capilano University — Client File\n\nPublic post-secondary university SEM enrolment",
    )
    peers_path = tmp_path / "peers.yaml"
    peers_path.write_text(yaml.safe_dump([
        {"org": "AACRAO", "relationship": "consortium_peer"},
    ]))
    themes_path = tmp_path / "themes.yaml"
    themes_path.write_text(yaml.safe_dump(["AI in marketing operations"]))

    def failing_notion_fetcher():
        raise RuntimeError("integration not granted access to Leads DB")

    wl = build_watchlist_from_sources(
        clients_dir=clients_dir,
        peers_path=peers_path,
        themes_path=themes_path,
        notion_fetcher=failing_notion_fetcher,
    )

    # Notion failed but pipeline must still produce a watchlist.
    assert wl is not None
    assert len(wl.clients) == 1
    assert wl.clients[0].org == "Capilano University"
    assert wl.prospects == []  # Notion failed; left empty, not crashed
    assert wl.peer_orgs[0].org == "AACRAO"
    assert wl.thought_leadership_themes == ["AI in marketing operations"]


def test_build_watchlist_includes_prospects_from_notion(tmp_path):
    clients_dir = tmp_path / "Clients"
    clients_dir.mkdir()
    peers_path = tmp_path / "peers.yaml"
    peers_path.write_text(yaml.safe_dump([]))
    themes_path = tmp_path / "themes.yaml"
    themes_path.write_text(yaml.safe_dump([]))

    def notion_fetcher():
        return [
            WatchlistOrg(org="Prospect U", industry="higher_ed_canada", stage="discovery"),
        ]

    wl = build_watchlist_from_sources(
        clients_dir=clients_dir,
        peers_path=peers_path,
        themes_path=themes_path,
        notion_fetcher=notion_fetcher,
    )

    assert len(wl.prospects) == 1
    assert wl.prospects[0].org == "Prospect U"
    assert wl.prospects[0].stage == "discovery"


def test_build_watchlist_handles_missing_clients_dir(tmp_path):
    """If the clients dir doesn't exist (e.g., running in CI), keep going."""
    peers_path = tmp_path / "peers.yaml"
    peers_path.write_text(yaml.safe_dump([]))
    themes_path = tmp_path / "themes.yaml"
    themes_path.write_text(yaml.safe_dump([]))

    wl = build_watchlist_from_sources(
        clients_dir=tmp_path / "does-not-exist",
        peers_path=peers_path,
        themes_path=themes_path,
        notion_fetcher=lambda: [],
    )
    assert wl is not None
    assert wl.clients == []


# ----- write_watchlist_yaml ---------------------------------------------

def test_write_watchlist_yaml_roundtrips(tmp_path):
    """Writing then reading must produce equivalent data."""
    from daily_news.config import Watchlist, load_watchlist

    wl = Watchlist(
        clients=[WatchlistOrg(org="A", industry="ai", posture="active", aliases=["Alpha"])],
        prospects=[WatchlistOrg(org="B", industry="marketing", stage="discovery")],
        peer_orgs=[WatchlistOrg(org="C", relationship="consortium_peer")],
        thought_leadership_themes=["theme one"],
        generated_at="2026-05-21T10:00:00-07:00",
    )
    path = tmp_path / "watchlist.yaml"
    write_watchlist_yaml(wl, path)

    loaded = load_watchlist(path)
    assert loaded is not None
    assert loaded.clients[0].org == "A"
    assert loaded.clients[0].aliases == ["Alpha"]
    assert loaded.prospects[0].stage == "discovery"
    assert loaded.peer_orgs[0].relationship == "consortium_peer"
    assert loaded.thought_leadership_themes == ["theme one"]
    assert loaded.generated_at == "2026-05-21T10:00:00-07:00"


def test_write_watchlist_yaml_includes_header_comment(tmp_path):
    """The file is auto-generated — a header comment warns hand-editors."""
    from daily_news.config import Watchlist

    wl = Watchlist()
    path = tmp_path / "watchlist.yaml"
    write_watchlist_yaml(wl, path)
    content = path.read_text()
    assert content.startswith("#")
    assert "auto-generated" in content.lower() or "sync_watchlist" in content.lower()
