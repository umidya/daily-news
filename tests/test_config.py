from daily_news.config import load_config


def test_load_config_succeeds():
    cfg = load_config()
    assert len(cfg.feeds) > 0
    assert len(cfg.searches) > 0
    assert "ai" in cfg.topics
    assert "kamloops_sun_peaks" in cfg.topics
    assert "bc_food_recalls" in cfg.topics
    assert cfg.scoring_weights.relevance > 0
    assert cfg.target_story_count > 0


def test_topic_keywords_lowercased():
    cfg = load_config()
    for topic in cfg.topics.values():
        for kw in topic.keywords:
            assert kw == kw.lower()
