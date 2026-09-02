"""Tests for the monthly watchlist refresh: posture, exclusions, diffing.

Both bugs guarded here were live on 2026-09-01: the roster still listed a
client who had been archived in May, and the posture heuristic would have
tagged the most active client on the list `past`.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from daily_news.config import SelfEntity, Watchlist, WatchlistOrg, load_watchlist, watchlist_staleness_warning
from daily_news.sync_watchlist import (
    EXCLUDED_CLIENT_FOLDERS,
    detect_posture,
    iter_client_folders,
    write_watchlist_yaml,
)
from daily_news.watchlist_diff import diff_watchlists


# --- posture ------------------------------------------------------------

def test_posture_reads_only_the_current_stage_bullet():
    """The Columbia College bug.

    Its Status block opens with an active Phase 2 and, further down, still
    carries 'PHASE 1 COMPLETE — PAST CLIENT' from July. Scanning the whole
    block let the July line win.
    """
    text = textwrap.dedent("""
        # Columbia College — Client File

        ## Status
        - **Stage (current, 2026-09-01):** PHASE 2 — IN PREP. Agreement executed.
        - **Stage (2026-07-16):** PHASE 1 COMPLETE — PAST CLIENT (first paid client).
          Moved to Past Clients in Notion.
    """)
    assert detect_posture(text) == "active"


def test_posture_detects_a_genuinely_past_client():
    text = "# X\n\n## Status\n- **Stage:** PAST CLIENT — engagement closed 2026-03-01.\n"
    assert detect_posture(text) == "past"


def test_posture_detects_an_unsigned_prospect():
    text = "# UNF\n\n## Status\n- **Stage:** LEAD — Proposal Sent 2026-07-23 ($14,500).\n"
    assert detect_posture(text) == "prospect"


def test_posture_defaults_to_active_without_a_status_block():
    assert detect_posture("# Some Client\n\nNo status here.\n") == "active"


def test_explicit_marker_overrides_the_heuristic():
    text = (
        "# X\n<!-- watchlist: posture=past -->\n\n"
        "## Status\n- **Stage:** ACTIVE — everything is fine.\n"
    )
    assert detect_posture(text) == "past"


# --- folder exclusions --------------------------------------------------

def test_container_folders_are_skipped(tmp_path: Path):
    """The 'Lost Leads' bug.

    Lost Leads holds archived prospects and has no CLAUDE.md of its own, so
    the nested-folder branch would adopt the container name as an org and
    resurrect the dead prospect inside it as its industry signal.
    """
    (tmp_path / "Real Client").mkdir()
    (tmp_path / "Real Client" / "CLAUDE.md").write_text("# Real Client — Client File\n")
    archived = tmp_path / "Lost Leads" / "Cushman & Wakefield Edmonton"
    archived.mkdir(parents=True)
    (archived / "CLAUDE.md").write_text("# Ian Newman\n\nCommercial real estate brokerage.\n")

    names = {p.name for p in iter_client_folders(tmp_path)}
    assert names == {"Real Client"}
    assert "lost leads" in EXCLUDED_CLIENT_FOLDERS


def test_missing_clients_dir_is_not_an_error(tmp_path: Path):
    assert list(iter_client_folders(tmp_path / "nope")) == []


# --- round-trip ---------------------------------------------------------

def test_self_block_survives_a_write_read_round_trip(tmp_path: Path):
    wl = Watchlist(
        clients=[WatchlistOrg(org="Capilano University", industry="higher_ed_canada", posture="active")],
        self_entity=SelfEntity(
            org="Midya U Advisory",
            aliases=["Midya U"],
            bylines=["Midya U"],
            domains=["midyau.com"],
            byline_outlets=["monitor.icef.com"],
        ),
        generated_at="2026-09-01T00:00:00+00:00",
    )
    out = tmp_path / "watchlist.yaml"
    write_watchlist_yaml(wl, out)

    reloaded = load_watchlist(out)
    assert reloaded is not None
    assert reloaded.self_entity is not None
    assert reloaded.self_entity.org == "Midya U Advisory"
    assert reloaded.self_entity.domains == ["midyau.com"]
    assert reloaded.self_entity.byline_outlets == ["monitor.icef.com"]
    assert [c.org for c in reloaded.clients] == ["Capilano University"]


def test_watchlist_without_a_self_block_loads_as_none(tmp_path: Path):
    out = tmp_path / "watchlist.yaml"
    out.write_text(yaml.safe_dump({"clients": [], "prospects": [], "peer_orgs": []}))
    wl = load_watchlist(out)
    assert wl is not None and wl.self_entity is None


# --- staleness ----------------------------------------------------------

def test_stale_watchlist_is_flagged():
    wl = Watchlist(generated_at="2026-05-22T05:47:43+00:00")
    from datetime import datetime, timezone
    msg = watchlist_staleness_warning(wl, now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert "101 days old" in msg


def test_fresh_watchlist_is_silent():
    from datetime import datetime, timezone
    wl = Watchlist(generated_at="2026-09-01T00:00:00+00:00")
    assert watchlist_staleness_warning(wl, now=datetime(2026, 9, 10, tzinfo=timezone.utc)) == ""


def test_unparseable_timestamp_does_not_raise():
    assert watchlist_staleness_warning(Watchlist(generated_at="whenever")) == ""


# --- diff ---------------------------------------------------------------

def test_diff_reports_adds_removes_and_posture_changes():
    old = Watchlist(clients=[
        WatchlistOrg(org="Cushman & Wakefield Edmonton", posture="active"),
        WatchlistOrg(org="Capilano University", posture="active"),
    ])
    new = Watchlist(clients=[
        WatchlistOrg(org="Capilano University", posture="past"),
        WatchlistOrg(org="Columbia College", posture="active"),
    ])
    lines = diff_watchlists(old, new)
    joined = "\n".join(lines)
    assert "ADDED   clients: Columbia College" in joined
    assert "REMOVED clients: Cushman & Wakefield Edmonton" in joined
    assert "CHANGED clients: Capilano University: active → past" in joined


def test_diff_is_empty_when_nothing_moved():
    wl = Watchlist(clients=[WatchlistOrg(org="X", posture="active")])
    assert diff_watchlists(wl, wl) == []


def test_diff_flags_a_lost_self_block():
    old = Watchlist(self_entity=SelfEntity(org="Midya U Advisory"))
    new = Watchlist()
    assert any("REMOVED self block" in ln for ln in diff_watchlists(old, new))


def test_diff_handles_a_first_ever_sync():
    assert diff_watchlists(None, Watchlist()) == [
        "First sync — no previous watchlist to compare against."
    ]


# --- search query construction ------------------------------------------

def test_higher_ed_queries_exclude_sports_noise():
    """Adding Columbia College and UNF to the roster pulled US college soccer
    into the top 10 candidates — both names collide with American schools."""
    from daily_news.fetch import _watchlist_query
    q = _watchlist_query(WatchlistOrg(org="Columbia College", industry="higher_ed_canada"))
    assert '"Columbia College"' in q
    assert "-soccer" in q and "-NCAA" in q


def test_non_higher_ed_queries_are_left_alone():
    from daily_news.fetch import _watchlist_query
    q = _watchlist_query(
        WatchlistOrg(org="Mogul Realty Group", aliases=["Mogul RG"], industry="canadian_real_estate")
    )
    assert q == '"Mogul Realty Group" OR "Mogul RG"'
