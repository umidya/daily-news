from daily_news.dedup import (
    canonicalize_url,
    is_duplicate_title,
    normalize_title,
    title_similarity,
    url_hash,
)


def test_canonicalize_strips_tracking_params():
    a = "https://example.com/article?utm_source=newsletter&utm_campaign=daily&id=42"
    b = "https://example.com/article?id=42&fbclid=junk"
    assert canonicalize_url(a) == canonicalize_url(b)


def test_canonicalize_normalizes_host():
    assert canonicalize_url("https://www.cbc.ca/news/foo") == \
           canonicalize_url("https://cbc.ca/news/foo/")


def test_canonicalize_drops_trailing_slash():
    assert canonicalize_url("https://example.com/a/") == "https://example.com/a"


def test_url_hash_stable():
    assert url_hash("https://example.com/x") == url_hash("https://example.com/x")
    assert url_hash("https://example.com/x") != url_hash("https://example.com/y")


def test_normalize_title_strips_prefix():
    assert normalize_title("BREAKING: Major news here!") == "major news here"
    assert normalize_title("Opinion | Why X is Y") == "why x is y"


def test_normalize_title_lowercases_and_strips_punct():
    assert normalize_title("U.S. & Canada agree on AI policy.") == \
           "u s canada agree on ai policy"


def test_title_similarity_catches_wire_repeats():
    a = normalize_title("Bank of Canada holds rate steady at 4.25%")
    b = normalize_title("Bank of Canada keeps rate at 4.25 percent")
    assert title_similarity(a, b) >= 70


def test_title_similarity_distinguishes_different_stories():
    a = normalize_title("Anthropic releases new Claude model")
    b = normalize_title("Stock market closes lower on rate fears")
    assert title_similarity(a, b) < 50


def test_is_duplicate_title():
    existing = [
        normalize_title("Vancouver introduces new short-term rental rules"),
        normalize_title("Bank of Canada holds rate at 4.25%"),
    ]
    assert is_duplicate_title(
        normalize_title("Vancouver introduces new short term rental rules"),
        existing,
    )
    assert not is_duplicate_title(
        normalize_title("Toronto considers new bike lane plan"),
        existing,
    )
