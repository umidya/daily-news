from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .config import Config, SelfEntity, TopicConfig
from .dedup import is_duplicate_title, title_similarity
from .models import Article


# --- Self-coverage detection --------------------------------------------

# Midya's own coverage is never allowed to lose the cut. A guest byline in a
# trade publication scores badly on every ordinary axis — it is commentary,
# not breaking news, so relevance keywords miss it and recency decay hits it
# like anything else. On 2026-08-26 her ICEF Monitor article was fetched (the
# feed was subscribed) and then scored out of the briefing. This floor is the
# fix: a self match is pinned above any normal story's reachable score.
SELF_SCORE_FLOOR = 10.0


def _name_pattern(name: str) -> re.Pattern:
    """Word-boundary matcher for a name, tolerant of internal whitespace runs."""
    parts = [re.escape(p) for p in name.split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\b", re.IGNORECASE)


def _host_matches(url: str, domains: list[str]) -> str:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    for d in domains:
        d = d.lower().removeprefix("www.")
        if host == d or host.endswith("." + d):
            return d
    return ""


# How a self match was established. The summarizer needs this: "ran under
# your byline" and "mentions your firm" are different claims, and a model
# given only a matched name will confidently assert the stronger one.
MATCH_BYLINE = "byline"
MATCH_DOMAIN = "domain"
MATCH_TEXT = "text"
MATCH_SEARCH = "search"
MATCH_PAGE = "page"

# Set by fetch.build_self_searches on every result of a name-targeted Google
# News query. Those entries are otherwise unidentifiable — see detect_self_match.
SELF_SEARCH_TOPIC = "self"

# The same piece often arrives twice: once from the publisher's own feed and
# once via the Google News query on her name. Both are self matches, and the
# in-run title dedup keeps whichever scores higher. Prefer the direct copy —
# the search copy's URL is a news.google.com redirect, so the briefing would
# otherwise hand her an opaque link to her own article. Too small to reorder
# self hits on any other axis.
_DIRECT_MATCH_BONUS = 1.0


def detect_self_match(article: Article, entity: SelfEntity | None) -> tuple[str, str]:
    """Identify an article as Midya's own. Returns (matched_value, how).

    ("", "") when it isn't hers. Four legs, cheapest first:

      1. byline  — her name in the RSS author field.
      2. domain  — the story links to a site she owns.
      3. text    — her name in the title or snippet.
      4. search  — the item came back from a Google News query built from her
                   own names. This leg exists because those entries are opaque
                   by construction: Google rewrites `link` to a
                   news.google.com redirect, drops `author`, and replaces the
                   summary with an anchor tag. Legs 1-3 all miss, and the
                   host is news.google.com so the page-scan tier never fires
                   either. Verified live: the query returns her ICEF article
                   and exactly nothing else, so trusting the search engine's
                   own phrase index here is both necessary and precise.

    Word-boundary anchored so "Midya U" doesn't fire on a longer surname that
    merely starts the same way.
    """
    if entity is None or not entity.is_configured():
        return "", ""

    author = article.author or ""
    for byline in entity.bylines:
        if byline and _name_pattern(byline).search(author):
            return byline, MATCH_BYLINE

    hit = _host_matches(article.url, entity.domains) or _host_matches(
        article.canonical_url, entity.domains
    )
    if hit:
        return hit, MATCH_DOMAIN

    text = f"{article.title} {article.snippet}"
    for name in entity.names:
        if _name_pattern(name).search(text):
            return name, MATCH_TEXT

    if SELF_SEARCH_TOPIC in article.topics:
        return entity.org or (entity.names[0] if entity.names else "self"), MATCH_SEARCH

    return "", ""


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
    # Respect a match already set by the page-scan tier in fetch.py — it saw
    # the article body, which is strictly more than this function can see from
    # the feed metadata. Recomputing here would silently discard it.
    if article.self_match:
        self_match = article.self_match
    else:
        self_match, how = detect_self_match(
            article, cfg.watchlist.self_entity if cfg.watchlist else None
        )
        if self_match:
            article.self_match_kind = how
    if self_match:
        article.self_match = self_match
        # Pin above every ordinary score rather than adding a bonus, so no
        # combination of recency decay and weak keyword relevance can bury it.
        final = SELF_SCORE_FLOOR + final
        if article.self_match_kind and article.self_match_kind != MATCH_SEARCH:
            final += _DIRECT_MATCH_BONUS
        topic = "watchlist"

    breakdown = {
        "relevance": round(relevance, 3),
        "credibility": round(credibility, 3),
        "recency": round(recency, 3),
        "novelty": round(novelty, 3),
        "topic": topic,
        "final": round(final, 3),
    }
    if self_match:
        breakdown["self_match"] = self_match
        breakdown["self_match_kind"] = article.self_match_kind
    return final, breakdown, topic


def score_and_filter(
    articles: list[Article], cfg: Config, recent_titles: list[str]
) -> list[Article]:
    """Scores all articles, drops irrelevant ones, deduplicates near-duplicate
    titles within this run, returns sorted descending by score."""
    now = datetime.now(timezone.utc)
    # Drop articles older than recency cutoff up front.
    self_entity = cfg.watchlist.self_entity if cfg.watchlist else None
    fresh: list[Article] = []
    for a in articles:
        # Midya's own coverage bypasses the recency cutoff. A guest article
        # can sit in a publisher's feed for a day before it surfaces, and
        # "we found it late" is not a reason to never tell her about it.
        if a.self_match or detect_self_match(a, self_entity)[0]:
            fresh.append(a)
            continue
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
        if breakdown["relevance"] <= 0.0 and not a.topics and not a.self_match:
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
