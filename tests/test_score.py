from datetime import datetime, timedelta, timezone

from daily_news.config import Config, ScoringWeights, TopicConfig
from daily_news.dedup import normalize_title, url_hash, canonicalize_url
from daily_news.models import Article
from daily_news.score import score_article, score_and_filter


def _make_article(
    title: str,
    snippet: str = "",
    source: str = "Test Source",
    topics=None,
    credibility: float = 0.85,
    age_hours: float = 2.0,
) -> Article:
    url = f"https://example.com/{title[:30].replace(' ', '-')}"
    canonical = canonicalize_url(url)
    return Article(
        url=url,
        canonical_url=canonical,
        url_hash=url_hash(canonical),
        title=title,
        title_normalized=normalize_title(title),
        source=source,
        published_at=datetime.now(timezone.utc) - timedelta(hours=age_hours),
        fetched_at=datetime.now(timezone.utc),
        snippet=snippet,
        topics=list(topics or []),
        credibility=credibility,
    )


def _config() -> Config:
    return Config(
        feeds=[],
        searches=[],
        topics={
            "ai": TopicConfig(
                name="ai",
                weight=1.0,
                keywords=["artificial intelligence", "ai", "claude", "openai"],
                negatives=[],
            ),
            "kamloops_sun_peaks": TopicConfig(
                name="kamloops_sun_peaks",
                weight=1.0,
                keywords=["kamloops", "sun peaks"],
                negatives=[],
            ),
        },
        scoring_weights=ScoringWeights(
            relevance=0.5, credibility=0.2, recency=0.15, novelty=0.15
        ),
        recency_cutoff_hours=36,
        candidate_pool_size=25,
        target_story_count=12,
        anthropic_api_key="",
        openai_api_key="",
        base_url="",
    )


def test_score_recent_relevant_article_scores_high():
    cfg = _config()
    art = _make_article(
        "Anthropic launches new Claude model",
        snippet="The AI company Anthropic released Claude with new agentic capabilities.",
        topics=["ai"],
        age_hours=1.0,
    )
    score, breakdown, topic = score_article(art, cfg, recent_titles=[])
    assert score > 0.6
    assert topic == "ai"
    assert breakdown["relevance"] > 0.4


def test_score_old_article_recency_drops():
    cfg = _config()
    art = _make_article(
        "Kamloops council debates new bylaw",
        topics=["kamloops_sun_peaks"],
        age_hours=30.0,
    )
    _, breakdown, _ = score_article(art, cfg, recent_titles=[])
    assert breakdown["recency"] < 0.2


def test_novelty_penalty_for_seen_titles():
    cfg = _config()
    art = _make_article("Kamloops council debates new bylaw", topics=["kamloops_sun_peaks"])
    seen = [normalize_title("Kamloops council debates new bylaw")]
    _, breakdown, _ = score_article(art, cfg, recent_titles=seen)
    assert breakdown["novelty"] < 0.2


def test_score_and_filter_drops_in_run_duplicates():
    cfg = _config()
    arts = [
        _make_article("Anthropic launches new Claude model", topics=["ai"], credibility=0.95),
        _make_article("Anthropic launches new Claude model AI", topics=["ai"], credibility=0.7),
        _make_article("Kamloops council debates new bylaw", topics=["kamloops_sun_peaks"]),
    ]
    kept = score_and_filter(arts, cfg, recent_titles=[])
    titles = [a.title for a in kept]
    assert sum(1 for t in titles if "Anthropic" in t) == 1
    assert any("Kamloops" in t for t in titles)


def test_score_and_filter_drops_irrelevant():
    cfg = _config()
    arts = [
        _make_article("Local sports team wins game", topics=[]),  # no topic match
        _make_article("Anthropic launches new Claude model", topics=["ai"]),
    ]
    kept = score_and_filter(arts, cfg, recent_titles=[])
    assert all("sports" not in a.title.lower() for a in kept)
