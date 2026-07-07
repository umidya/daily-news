"""Build config/watchlist.yaml from local client folders + Notion 🎯 Leads.

Run locally when the roster changes:

    python -m daily_news.sync_watchlist

The Notion fetch is the only network call. If the integration token can't see
the Leads database, the script logs a clear warning + instructions and writes
a watchlist with clients/peers/themes only (prospects left empty). The
pipeline then runs as today — no client-aware enrichment lost on the things
we *can* read.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib import request as urlreq, error as urlerror

import yaml

from .config import (
    DEFAULT_CONFIG_DIR,
    PROJECT_ROOT,
    Watchlist,
    WatchlistOrg,
)

log = logging.getLogger(__name__)

DEFAULT_CLIENTS_DIR = Path.home() / "Desktop" / "Clients"
DEFAULT_PEERS_PATH = DEFAULT_CONFIG_DIR / "peer_orgs.yaml"
DEFAULT_THEMES_PATH = DEFAULT_CONFIG_DIR / "thought_leadership_themes.yaml"
DEFAULT_WATCHLIST_PATH = DEFAULT_CONFIG_DIR / "watchlist.yaml"

NOTION_TOKEN_PATH = Path.home() / ".claude" / ".notion-token"
NOTION_VERSION = "2022-06-28"


# --- Industry classification --------------------------------------------

# Keyword signal sets. The classifier counts hits per bucket; highest wins
# (with ties broken by declaration order below). Keywords are matched
# case-insensitively against the full body of a client CLAUDE.md.
_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "higher_ed_canada": [
        "university", "post-secondary", "enrolment", "enrollment",
        "sem ", "irc c", "ircc", "pgwp", "college", "faculty",
        "dean", "avp ", "academic", "registrar", "student recruitment",
        "international student",
    ],
    "canadian_real_estate": [
        "real estate", "brokerage", "realtor", "realty", "listing",
        "mls", "multifamily", "commercial real estate", "investment sales",
        "capital markets", "residential", "buyer", "seller", "mortgage",
        "agent recruitment", "cushman", "wakefield",
    ],
}


def classify_industry_from_text(text: str) -> str:
    """Pick the best-matching industry tag for a free-form text body.

    Returns one of the topic_keys (currently `higher_ed_canada` or
    `canadian_real_estate`) or "" when no signal is detected. Future-proof:
    add buckets to `_INDUSTRY_KEYWORDS` to extend.
    """
    if not text:
        return ""
    lower = text.lower()
    scores: dict[str, int] = {}
    for industry, kws in _INDUSTRY_KEYWORDS.items():
        scores[industry] = sum(1 for kw in kws if kw in lower)
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else ""


# --- Client folder parsing ----------------------------------------------

_H1_RE = re.compile(r"^#\s+(?P<rest>.+?)\s*$", re.MULTILINE)
_ALIAS_PAREN_RE = re.compile(r"\(([^)]+)\)")
_TRAILING_QUALIFIER_RE = re.compile(r"\s*[—–\-]\s*.*$")  # — or – or -


def _parse_h1_org_and_aliases(h1_line: str) -> tuple[str, list[str]]:
    """Pull primary org name + aliases out of an H1 like:

      'Capilano University — Client File'
      'Mogul Realty Group (Mogul RG) — Client File'
      'Cushman & Wakefield Edmonton'
    """
    # First strip the trailing "— Client File" / "- Notes" qualifier.
    stripped = _TRAILING_QUALIFIER_RE.sub("", h1_line).strip()

    aliases: list[str] = []
    alias_match = _ALIAS_PAREN_RE.search(stripped)
    if alias_match:
        alias_text = alias_match.group(1)
        aliases = [a.strip() for a in alias_text.split(",") if a.strip()]
        stripped = _ALIAS_PAREN_RE.sub("", stripped).strip()

    return stripped, aliases


def _find_nested_claude_md(folder: Path) -> Optional[Path]:
    """Look one level deep for a CLAUDE.md (e.g., company/contact/CLAUDE.md)."""
    for child in folder.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue
        nested = child / "CLAUDE.md"
        if nested.is_file():
            return nested
    return None


def extract_client_from_folder(folder: Path) -> Optional[WatchlistOrg]:
    """Read folder/CLAUDE.md (or a one-level-nested CLAUDE.md) and turn it
    into a WatchlistOrg.

    Two folder shapes are supported:

      1. Flat (Capilano, Mogul): `<org>/CLAUDE.md`. H1 supplies the org name.
      2. Nested (Cushman & Wakefield Edmonton/Ian Newman/CLAUDE.md). The
         H1 typically names the person; the top folder is the company. We
         use the top folder name as the canonical org and still classify
         industry from the nested CLAUDE.md content.

    Returns None when no CLAUDE.md can be found at either depth, or when
    the flat-style CLAUDE.md lacks an H1 (we won't guess).
    """
    claude_path = folder / "CLAUDE.md"
    nested = False
    if not claude_path.is_file():
        found = _find_nested_claude_md(folder)
        if found is None:
            return None
        claude_path = found
        nested = True

    try:
        text = claude_path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("failed to read %s: %s", claude_path, e)
        return None

    if nested:
        # Top folder is authoritative — H1 is about an individual contact.
        org_name = folder.name
        aliases: list[str] = []
    else:
        h1_match = _H1_RE.search(text)
        if not h1_match:
            log.warning("%s has no H1 — skipping", claude_path)
            return None
        org_name, aliases = _parse_h1_org_and_aliases(h1_match.group("rest"))

    industry = classify_industry_from_text(text)

    # Posture — look for the Status block and guess.
    posture = "active"
    status_match = re.search(r"##\s+Status\b(.+?)(?=\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE)
    if status_match:
        status_body = status_match.group(1).lower()
        if "wrapped" in status_body or "completed engagement" in status_body:
            posture = "wrapping"
        elif "past client" in status_body:
            posture = "past"

    return WatchlistOrg(
        org=org_name,
        aliases=aliases,
        industry=industry,
        posture=posture,
    )


def iter_client_folders(clients_dir: Path) -> Iterable[Path]:
    """Yield each immediate subdirectory of clients_dir.

    Silently returns empty when clients_dir doesn't exist (e.g., running in
    CI where ~/Desktop/Clients isn't present)."""
    if not clients_dir.is_dir():
        return []
    return [p for p in clients_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]


# --- Notion Leads fetch -------------------------------------------------

def _read_notion_token() -> Optional[str]:
    if not NOTION_TOKEN_PATH.exists():
        return None
    try:
        return NOTION_TOKEN_PATH.read_text().strip() or None
    except OSError:
        return None


def _notion_request(token: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"https://api.notion.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urlreq.Request(url, data=data, headers=headers, method=method)
    with urlreq.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _find_leads_database_id(token: str) -> Optional[str]:
    """Search Notion for an accessible database whose title contains 'Leads'."""
    resp = _notion_request(token, "POST", "/v1/search", {
        "query": "Leads",
        "filter": {"property": "object", "value": "database"},
    })
    for result in resp.get("results", []):
        title_parts = result.get("title") or []
        title = "".join(t.get("plain_text", "") for t in title_parts)
        if "lead" in title.lower():
            return result.get("id")
    return None


def _extract_lead_org(page: dict) -> Optional[WatchlistOrg]:
    """Pull org + stage from a Notion page row in the Leads DB.

    The Leads database schema is owned by Midya — this function defensively
    looks for any title property and any select/status property containing
    'stage'. Adjust here if the schema turns out to use different names.
    """
    props = page.get("properties", {})
    title_text = ""
    stage = None
    for prop_name, prop in props.items():
        ptype = prop.get("type")
        if ptype == "title":
            parts = prop.get("title") or []
            title_text = "".join(t.get("plain_text", "") for t in parts).strip()
        elif "stage" in prop_name.lower() or "status" in prop_name.lower():
            if ptype == "select":
                sel = prop.get("select")
                stage = sel.get("name") if sel else None
            elif ptype == "status":
                st = prop.get("status")
                stage = st.get("name") if st else None
    if not title_text:
        return None
    if stage and stage.lower() == "lost":
        return None  # filter out lost leads per spec
    return WatchlistOrg(org=title_text, stage=stage)


def fetch_notion_leads() -> list[WatchlistOrg]:
    """Fetch all leads from the Notion 🎯 Leads database.

    Raises RuntimeError with an actionable message when access fails so the
    caller can decide whether to swallow (sync script) or bubble (other use).
    """
    token = _read_notion_token()
    if not token:
        raise RuntimeError(
            f"Notion token not found at {NOTION_TOKEN_PATH}. "
            f"See ~/.claude/bin/notion --help for setup."
        )

    db_id = _find_leads_database_id(token)
    if not db_id:
        raise RuntimeError(
            "Could not find an accessible 'Leads' database in Notion. "
            "Share the 🎯 Leads database with the 'Claude Code (Midya AI)' "
            "integration: open the database in Notion → '...' → "
            "'Connections' → add 'Claude Code (Midya AI)'."
        )

    leads: list[WatchlistOrg] = []
    cursor: Optional[str] = None
    while True:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = _notion_request(token, "POST", f"/v1/databases/{db_id}/query", body)
        for page in resp.get("results", []):
            org = _extract_lead_org(page)
            if org is not None:
                leads.append(org)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return leads


# --- Curated YAML files -------------------------------------------------

def _load_yaml_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        log.warning("YAML parse failed for %s: %s", path, e)
        return []
    return list(raw or [])


def _load_peer_orgs(path: Path) -> list[WatchlistOrg]:
    out: list[WatchlistOrg] = []
    for item in _load_yaml_list(path):
        if not isinstance(item, dict) or "org" not in item:
            continue
        out.append(WatchlistOrg(
            org=str(item["org"]),
            industry=str(item.get("industry", "") or ""),
            relationship=item.get("relationship"),
        ))
    return out


def _load_themes(path: Path) -> list[str]:
    return [str(x) for x in _load_yaml_list(path)]


# --- Orchestration ------------------------------------------------------

def build_watchlist_from_sources(
    *,
    clients_dir: Path,
    peers_path: Path,
    themes_path: Path,
    notion_fetcher: Callable[[], list[WatchlistOrg]] = fetch_notion_leads,
) -> Watchlist:
    """Read all four sources and assemble a Watchlist.

    Notion failures are caught here and logged — the rest of the watchlist
    still gets produced.
    """
    clients: list[WatchlistOrg] = []
    for folder in iter_client_folders(clients_dir):
        org = extract_client_from_folder(folder)
        if org is not None:
            clients.append(org)

    prospects: list[WatchlistOrg] = []
    try:
        prospects = list(notion_fetcher())
    except Exception as e:
        log.warning(
            "Notion leads fetch failed (%s); watchlist will have no prospects. "
            "Resolve the cause and re-run the sync.",
            e,
        )

    return Watchlist(
        clients=clients,
        prospects=prospects,
        peer_orgs=_load_peer_orgs(peers_path),
        thought_leadership_themes=_load_themes(themes_path),
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


# --- Serialization ------------------------------------------------------

def _org_to_dict(org: WatchlistOrg) -> dict:
    out: dict = {"org": org.org}
    if org.aliases:
        out["aliases"] = list(org.aliases)
    if org.industry:
        out["industry"] = org.industry
    if org.posture:
        out["posture"] = org.posture
    if org.stage:
        out["stage"] = org.stage
    if org.relationship:
        out["relationship"] = org.relationship
    if org.notes:
        out["notes"] = org.notes
    return out


def write_watchlist_yaml(wl: Watchlist, path: Path) -> None:
    """Serialize a Watchlist to YAML with a clear auto-generated header."""
    body = {
        "generated_at": wl.generated_at,
        "clients": [_org_to_dict(c) for c in wl.clients],
        "prospects": [_org_to_dict(p) for p in wl.prospects],
        "peer_orgs": [_org_to_dict(o) for o in wl.peer_orgs],
        "thought_leadership_themes": list(wl.thought_leadership_themes),
    }
    header = (
        "# AUTO-GENERATED by daily_news.sync_watchlist — do not hand-edit.\n"
        "# Re-run `python -m daily_news.sync_watchlist` after roster changes.\n"
        "# Sources: ~/Desktop/Clients/*/CLAUDE.md, Notion 🎯 Leads, peer_orgs.yaml,\n"
        "# thought_leadership_themes.yaml.\n\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True))


# --- CLI ----------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync the daily-news watchlist.")
    parser.add_argument(
        "--clients-dir",
        type=Path,
        default=DEFAULT_CLIENTS_DIR,
        help="Directory of client subfolders (default: ~/Desktop/Clients).",
    )
    parser.add_argument(
        "--peers",
        type=Path,
        default=DEFAULT_PEERS_PATH,
        help="Path to peer_orgs.yaml (curated).",
    )
    parser.add_argument(
        "--themes",
        type=Path,
        default=DEFAULT_THEMES_PATH,
        help="Path to thought_leadership_themes.yaml (curated).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Output path for watchlist.yaml.",
    )
    parser.add_argument(
        "--no-notion",
        action="store_true",
        help="Skip the Notion fetch entirely; prospects will be empty.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    fetcher: Callable[[], list[WatchlistOrg]] = (
        (lambda: []) if args.no_notion else fetch_notion_leads
    )

    wl = build_watchlist_from_sources(
        clients_dir=args.clients_dir,
        peers_path=args.peers,
        themes_path=args.themes,
        notion_fetcher=fetcher,
    )
    write_watchlist_yaml(wl, args.out)
    log.info(
        "Wrote %s: %d clients, %d prospects, %d peer orgs, %d themes",
        args.out, len(wl.clients), len(wl.prospects),
        len(wl.peer_orgs), len(wl.thought_leadership_themes),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
