from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import httpx
from dateutil import parser as dateparser

from .config import FeedConfig, SearchConfig
from .dedup import canonicalize_url, normalize_title, url_hash
from .models import Article

log = logging.getLogger(__name__)

USER_AGENT = (
    "daily-news/0.1 (+https://github.com/) "
    "Mozilla/5.0 (compatible; DailyNewsBot/1.0)"
)
REQUEST_TIMEOUT = 20.0
MAX_PER_SOURCE = 25  # cap to keep the candidate pool sane

_TAG_RE = re.compile(r"<[^>]+>")
# Match og:image meta tag tolerantly across attribute orderings + quote styles.
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']'
    r"|"
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:image["\']',
    re.IGNORECASE,
)
_TWITTER_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return _TAG_RE.sub("", text).strip()


def _image_from_entry(entry) -> str | None:
    """Pull an image URL from an RSS entry without an extra HTTP request.

    Order of preference matches what feed publishers actually use:
    media:thumbnail → media:content (image-typed) → enclosure → links.
    """
    thumbs = entry.get("media_thumbnail") or []
    if thumbs and isinstance(thumbs, list):
        url = thumbs[0].get("url") if isinstance(thumbs[0], dict) else None
        if url:
            return url

    media = entry.get("media_content") or []
    if media and isinstance(media, list):
        for m in media:
            if not isinstance(m, dict):
                continue
            if m.get("medium") == "image" or (m.get("type") or "").startswith("image/") or m.get("url"):
                if m.get("url"):
                    return m["url"]

    encs = entry.get("enclosures") or []
    if encs and isinstance(encs, list):
        for e in encs:
            if not isinstance(e, dict):
                continue
            if (e.get("type") or "").startswith("image/") and e.get("href"):
                return e["href"]

    links = entry.get("links") or []
    if links and isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            if link.get("rel") == "enclosure" and (link.get("type") or "").startswith("image/"):
                if link.get("href"):
                    return link["href"]

    img = entry.get("image")
    if isinstance(img, dict) and img.get("href"):
        return img["href"]
    return None


def fetch_og_image(url: str, timeout: float = 8.0) -> str | None:
    """Best-effort scrape of og:image / twitter:image from an article URL.

    Used as a fallback for articles whose RSS entry didn't include an image.
    Only ever called for stories that survived scoring + Claude's pick — so
    at most ~12 fetches per pipeline run, not every candidate.
    """
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            if not r.is_success:
                return None
            html = r.text[:200_000]  # cap so we don't parse a 10MB page
        m = _OG_IMAGE_RE.search(html)
        if m:
            return (m.group(1) or m.group(2) or "").strip() or None
        m = _TWITTER_IMAGE_RE.search(html)
        if m:
            return m.group(1).strip() or None
    except Exception as e:
        log.debug("og:image fetch failed for %s: %s", url, e)
    return None


def _parse_published(entry) -> datetime | None:
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


def _entry_to_article(entry, source: str, topics: list[str], credibility: float) -> Article | None:
    link = entry.get("link") or ""
    title = _strip_html(entry.get("title") or "").strip()
    if not link or not title:
        return None
    canonical = canonicalize_url(link)
    snippet = _strip_html(entry.get("summary") or entry.get("description") or "")[:600]
    return Article(
        url=link,
        canonical_url=canonical,
        url_hash=url_hash(canonical),
        title=title,
        title_normalized=normalize_title(title),
        source=source,
        published_at=_parse_published(entry),
        fetched_at=datetime.now(timezone.utc),
        snippet=snippet,
        topics=list(topics),
        credibility=credibility,
        image_url=_image_from_entry(entry),
    )


def _fetch_one(url: str) -> bytes | None:
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            return r.content
    except Exception as e:
        log.warning("Feed fetch failed for %s: %s", url, e)
        return None


def _parse_feed(content: bytes, source: str, topics: list[str], credibility: float) -> list[Article]:
    parsed = feedparser.parse(content)
    articles: list[Article] = []
    for entry in parsed.entries[:MAX_PER_SOURCE]:
        art = _entry_to_article(entry, source, topics, credibility)
        if art is not None:
            articles.append(art)
    return articles


def fetch_feeds(feeds: Iterable[FeedConfig], max_workers: int = 8) -> list[Article]:
    enabled = [f for f in feeds if f.enabled]
    results: list[Article] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_feed = {ex.submit(_fetch_one, f.url): f for f in enabled}
        for fut in as_completed(future_to_feed):
            feed = future_to_feed[fut]
            content = fut.result()
            if content is None:
                continue
            try:
                arts = _parse_feed(content, feed.name, feed.topics, feed.credibility)
                results.extend(arts)
                log.info("Fetched %d items from %s", len(arts), feed.name)
            except Exception as e:
                log.warning("Parse failed for %s: %s", feed.name, e)
    return results


def _google_news_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-CA&gl=CA&ceid=CA:en"
    )


def fetch_searches(searches: Iterable[SearchConfig], max_workers: int = 6) -> list[Article]:
    items = list(searches)
    results: list[Article] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_search = {
            ex.submit(_fetch_one, _google_news_url(s.query)): s for s in items
        }
        for fut in as_completed(future_to_search):
            search = future_to_search[fut]
            content = fut.result()
            if content is None:
                continue
            try:
                source = f"Google News: {search.query}"
                arts = _parse_feed(content, source, search.topics, search.credibility)
                results.extend(arts)
                log.info("Fetched %d items from search %s", len(arts), search.query)
            except Exception as e:
                log.warning("Search parse failed for %s: %s", search.query, e)
    return results
