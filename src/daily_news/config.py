from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

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


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    )
