from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_PUBLIC_DIR = PROJECT_ROOT / "public"
DEFAULT_TEMPLATES_DIR = PROJECT_ROOT / "templates"
DEFAULT_STATIC_DIR = PROJECT_ROOT / "static"


@dataclass
class FeedConfig:
    name: str
    url: str
    credibility: float
    topics: list[str]
    enabled: bool = True


@dataclass
class SearchConfig:
    query: str
    topics: list[str]
    credibility: float


@dataclass
class TopicConfig:
    name: str
    weight: float
    keywords: list[str]
    negatives: list[str] = field(default_factory=list)


@dataclass
class ScoringWeights:
    relevance: float
    credibility: float
    recency: float
    novelty: float


@dataclass
class WatchlistOrg:
    """One org Midya wants the briefing to track — a client, prospect, or peer.

    Population by section:
      - clients   → posture set (active | wrapping | past); aliases for dedup
      - prospects → stage set (from Notion 🎯 Leads pipeline)
      - peer_orgs → relationship set (e.g. consortium_peer, competitor)
    """
    org: str
    aliases: list[str] = field(default_factory=list)
    industry: str = ""
    posture: str | None = None
    stage: str | None = None
    relationship: str | None = None
    notes: str = ""


@dataclass
class Watchlist:
    clients: list[WatchlistOrg] = field(default_factory=list)
    prospects: list[WatchlistOrg] = field(default_factory=list)
    peer_orgs: list[WatchlistOrg] = field(default_factory=list)
    thought_leadership_themes: list[str] = field(default_factory=list)
    generated_at: str | None = None


@dataclass
class Config:
    feeds: list[FeedConfig]
    searches: list[SearchConfig]
    topics: dict[str, TopicConfig]
    scoring_weights: ScoringWeights
    recency_cutoff_hours: int
    candidate_pool_size: int
    target_story_count: int

    anthropic_api_key: str
    openai_api_key: str
    base_url: str

    data_dir: Path = DEFAULT_DATA_DIR
    public_dir: Path = DEFAULT_PUBLIC_DIR
    templates_dir: Path = DEFAULT_TEMPLATES_DIR
    static_dir: Path = DEFAULT_STATIC_DIR
    watchlist: Watchlist | None = None


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_watchlist(path: Path) -> Watchlist | None:
    """Read the auto-generated watchlist file.

    Returns None (with a warning) when the file is missing or malformed so the
    pipeline runs with no watchlist enrichment rather than failing the build.
    """
    if not path.exists():
        return None
    try:
        raw = _load_yaml(path)
    except yaml.YAMLError as e:
        log.warning("watchlist YAML failed to parse at %s: %s", path, e)
        return None
    if not isinstance(raw, dict):
        log.warning("watchlist YAML at %s did not parse to a mapping", path)
        return None

    def _orgs(key: str) -> list[WatchlistOrg]:
        items = raw.get(key) or []
        out: list[WatchlistOrg] = []
        for it in items:
            if not isinstance(it, dict) or "org" not in it:
                continue
            out.append(WatchlistOrg(
                org=str(it["org"]),
                aliases=[str(a) for a in (it.get("aliases") or [])],
                industry=str(it.get("industry", "") or ""),
                posture=it.get("posture"),
                stage=it.get("stage"),
                relationship=it.get("relationship"),
                notes=str(it.get("notes", "") or ""),
            ))
        return out

    return Watchlist(
        clients=_orgs("clients"),
        prospects=_orgs("prospects"),
        peer_orgs=_orgs("peer_orgs"),
        thought_leadership_themes=[
            str(t) for t in (raw.get("thought_leadership_themes") or [])
        ],
        generated_at=raw.get("generated_at"),
    )


def load_config(config_dir: Path = DEFAULT_CONFIG_DIR) -> Config:
    load_dotenv(PROJECT_ROOT / ".env")

    feeds_raw = _load_yaml(config_dir / "feeds.yaml")["feeds"]
    searches_raw = _load_yaml(config_dir / "searches.yaml")["searches"]
    interests_raw = _load_yaml(config_dir / "interests.yaml")

    feeds = [
        FeedConfig(
            name=f["name"],
            url=f["url"],
            credibility=float(f.get("credibility", 0.75)),
            topics=list(f.get("topics", [])),
            enabled=bool(f.get("enabled", True)),
        )
        for f in feeds_raw
    ]
    searches = [
        SearchConfig(
            query=s["query"],
            topics=list(s.get("topics", [])),
            credibility=float(s.get("credibility", 0.70)),
        )
        for s in searches_raw
    ]
    topics = {
        name: TopicConfig(
            name=name,
            weight=float(t.get("weight", 1.0)),
            keywords=[k.lower() for k in t.get("keywords", [])],
            negatives=[n.lower() for n in t.get("negatives", [])],
        )
        for name, t in interests_raw["topics"].items()
    }
    sw = interests_raw["scoring_weights"]
    weights = ScoringWeights(
        relevance=float(sw["relevance"]),
        credibility=float(sw["credibility"]),
        recency=float(sw["recency"]),
        novelty=float(sw["novelty"]),
    )

    watchlist = load_watchlist(config_dir / "watchlist.yaml")

    return Config(
        feeds=feeds,
        searches=searches,
        topics=topics,
        scoring_weights=weights,
        recency_cutoff_hours=int(interests_raw.get("recency_cutoff_hours", 36)),
        candidate_pool_size=int(interests_raw.get("candidate_pool_size", 25)),
        target_story_count=int(interests_raw.get("target_story_count", 12)),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("DAILY_NEWS_BASE_URL", "").rstrip("/"),
        watchlist=watchlist,
    )
