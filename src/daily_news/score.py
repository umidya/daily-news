from __future__ import annotations

import math
from datetime import datetime, timezone

from .config import Config, TopicConfig
from .dedup import is_duplicate_title, title_similarity
from .models import Article


def _topic_match(text: str, topic: TopicConfig) -> float:
    """Returns 0-1: fraction of unique keywords found, capped at 1.0.
    Negatives subtract."""
    if not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in topic.keywords if kw in text_lower)
    if hits == 0:
        return 0.0
    misses = sum(1 for neg in topic.negatives if neg in text_lower)
    raw = hits / max(3, len(topic.keywords) // 3)  # 3 hits = saturated
    raw = min(raw, 1.0)
    raw -= 0.5 * (misses / max(1, len(topic.negatives) or 1)) if topic.negatives else 0
    return max(0.0, raw)


def _relevance(article: Article, topics: dict[str, TopicConfig]) -> tuple[float, str]:
    text = f"{article.title} {article.snippet}"
    best_score = 0.0
    best_topic = ""
    # Articles tagged by their feed get a baseline match for those tags.
    seeded = {t for t in article.topics if t in topics}
    for name, topic in topics.items():
        match = _topic_match(text, topic)
        if name in seeded:
            match = max(match, 0.5)
        weighted = match * topic.weight
        if weighted > best_score:
            best_score = weighted
            best_topic = name
    return min(1.0, best_score), best_topic


def _recency(article: Article, cutoff_hours: int, now: datetime) -> float:
    if article.published_at is None:
        return 0.5  # unknown date - middle of the road
    age_hours = (now - article.published_at).total_seconds() / 3600.0
    if age_hours <= 0:
        return 1.0
    if age_hours >= cutoff_hours:
        return 0.0
    # Exponential decay with half-life of cutoff_hours/3 (typical: 12h half-life
    # for a 36h cutoff). Front-loads scoring on the most recent stories.
    half_life = cutoff_hours / 3.0
    return math.exp(-age_hours * math.log(2) / half_life)


def _novelty(article: Article, recent_titles: list[str]) -> float:
    if not recent_titles:
        return 1.0
    sims = [title_similarity(article.title_normalized, t) for t in recent_titles]
    max_sim = max(sims) if sims else 0.0
    return max(0.0, 1.0 - max_sim / 100.0)


def score_article(
    article: Article, cfg: Config, recent_titles: list[str], now: datetime | None = None
) -> tuple[float, dict, str]:
    now = now or datetime.now(timezone.utc)
    relevance, topic = _relevance(article, cfg.topics)
    credibility = max(0.0, min(1.0, article.credibility))
    recency = _recency(article, cfg.recency_cutoff_hours, now)
    novelty = _novelty(article, recent_titles)
    w = cfg.scoring_weights
    final = (
        w.relevance * relevance
        + w.credibility * credibility
        + w.recency * recency
        + w.novelty * novelty
    )
    breakdown = {
        "relevance": round(relevance, 3),
        "credibility": round(credibility, 3),
        "recency": round(recency, 3),
        "novelty": round(novelty, 3),
        "topic": topic,
        "final": round(final, 3),
    }
    return final, breakdown, topic


def score_and_filter(
    articles: list[Article], cfg: Config, recent_titles: list[str]
) -> list[Article]:
    """Scores all articles, drops irrelevant ones, deduplicates near-duplicate
    titles within this run, returns sorted descending by score."""
    now = datetime.now(timezone.utc)
    # Drop articles older than recency cutoff up front.
    fresh: list[Article] = []
    for a in articles:
        if a.published_at is None:
            fresh.append(a)
            continue
        age_h = (now - a.published_at).total_seconds() / 3600.0
        if age_h <= cfg.recency_cutoff_hours:
            fresh.append(a)

    scored: list[Article] = []
    for a in fresh:
        s, breakdown, topic = score_article(a, cfg, recent_titles, now)
        a.score = s
        a.score_breakdown = breakdown
        if topic and topic not in a.topics:
            a.topics.append(topic)
        # Drop irrelevant: a story with zero relevance is noise even if recent.
        if breakdown["relevance"] <= 0.0 and not a.topics:
            continue
        scored.append(a)

    scored.sort(key=lambda x: x.score, reverse=True)

    # In-run title dedup: walk descending; skip any that look like a higher-ranked story.
    kept: list[Article] = []
    kept_titles: list[str] = []
    for a in scored:
        if is_duplicate_title(a.title_normalized, kept_titles, threshold=88.0):
            continue
        kept.append(a)
        kept_titles.append(a.title_normalized)
    return kept
