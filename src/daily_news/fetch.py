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

from .config import Config, FeedConfig, SearchConfig, SelfEntity, Watchlist, WatchlistOrg
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


def _author_from_entry(entry) -> str:
    """Best-effort byline from an RSS entry.

    Publishers are inconsistent here: some set `author`, some only populate
    the structured `authors` list, some use Dublin Core `dc:creator` (which
    feedparser also surfaces as `author`). Try each and take the first.
    """
    author = (entry.get("author") or "").strip()
    if author:
        return _strip_html(author)[:200]
    authors = entry.get("authors") or []
    if isinstance(authors, list):
        for a in authors:
            name = (a.get("name") if isinstance(a, dict) else str(a) or "").strip()
            if name:
                return _strip_html(name)[:200]
    return ""


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
        author=_author_from_entry(entry),
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


WATCHLIST_SEARCH_CAP = 25
# Google News default credibility — matches config/searches.yaml convention.
_WATCHLIST_CREDIBILITY = 0.70


# Institution names collide across borders — "Columbia College" is also in
# Missouri, "University of Niagara Falls" shares an acronym with North
# Florida — and their athletics departments generate far more headlines than
# their administrations do. Without these exclusions the Watchlist section
# fills with US college sports results for orgs Midya actually works with.
_SPORTS_NOISE = (
    "soccer", "basketball", "football", "athletics", "volleyball",
    "baseball", "softball", "lacrosse", "NCAA",
)
_INDUSTRY_QUERY_EXCLUSIONS: dict[str, tuple[str, ...]] = {
    "higher_ed_canada": _SPORTS_NOISE,
    "higher_ed_global": _SPORTS_NOISE,
    "intl_students_canada": _SPORTS_NOISE,
}


def _watchlist_query(org: WatchlistOrg) -> str:
    """Build a quoted-OR Google News query covering an org's primary name +
    aliases. Quoted phrases force exact match so 'Mogul' (the word) doesn't
    flood with false positives.

    Higher-ed orgs also get sports terms negated — see _SPORTS_NOISE.
    """
    names = [org.org] + [a for a in org.aliases if a]
    query = " OR ".join(f'"{n}"' for n in names)
    exclusions = _INDUSTRY_QUERY_EXCLUSIONS.get(org.industry, ())
    if exclusions:
        query = f"({query}) " + " ".join(f"-{term}" for term in exclusions)
    return query


def _watchlist_topics(org: WatchlistOrg) -> list[str]:
    """Every watchlist search is tagged `watchlist` plus the org's industry
    so a hit is eligible for both the Watchlist section and the industry
    section if Claude judges it a better fit there."""
    topics = ["watchlist"]
    if org.industry:
        topics.append(org.industry)
    return topics


def build_watchlist_searches(
    watchlist: Watchlist, cap: int = WATCHLIST_SEARCH_CAP
) -> list[SearchConfig]:
    """Convert the watchlist roster into runtime Google News searches.

    Priority order (clients > prospects > peers) — when the cap forces cuts,
    lower priority groups go first. Dedupes by canonical org name so an org
    accidentally listed in two sections only produces one search.
    """
    ordered: list[WatchlistOrg] = (
        list(watchlist.clients)
        + list(watchlist.prospects)
        + list(watchlist.peer_orgs)
    )

    seen: set[str] = set()
    unique: list[WatchlistOrg] = []
    for org in ordered:
        key = org.org.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(org)

    if len(unique) > cap:
        dropped = [o.org for o in unique[cap:]]
        log.warning(
            "watchlist exceeds cap (%d > %d); dropping lowest-priority orgs: %s",
            len(unique), cap, ", ".join(dropped),
        )
        unique = unique[:cap]

    return [
        SearchConfig(
            query=_watchlist_query(org),
            topics=_watchlist_topics(org),
            credibility=_WATCHLIST_CREDIBILITY,
        )
        for org in unique
    ]


# Self searches never count against WATCHLIST_SEARCH_CAP — there are at most
# a couple of them and they are the highest-value queries in the whole run.
_SELF_CREDIBILITY = 0.90


def build_self_searches(entity: SelfEntity | None) -> list[SearchConfig]:
    """Google News queries that hunt for coverage of Midya herself.

    Two shapes, because they fail differently. The name query catches pieces
    that say who she is; the bare-domain query catches pieces that link to her
    site without naming the firm — a citation in someone else's article, which
    is exactly how thought-leadership coverage tends to look before anyone
    bothers to name the consultancy.
    """
    if entity is None or not entity.is_configured():
        return []

    searches: list[SearchConfig] = []
    names = entity.names
    if names:
        searches.append(SearchConfig(
            query=" OR ".join(f'"{n}"' for n in names),
            topics=["self", "watchlist"],
            credibility=_SELF_CREDIBILITY,
        ))
    for domain in entity.domains:
        searches.append(SearchConfig(
            query=f'"{domain}"',
            topics=["self", "watchlist"],
            credibility=_SELF_CREDIBILITY,
        ))
    return searches


def combined_searches(cfg: Config) -> list[SearchConfig]:
    """Static (config/searches.yaml) + self + dynamic (watchlist) searches.

    Pipeline calls this once per run so the fetch step sees all sources as
    a single search list. When the watchlist is absent, returns only the
    static list.
    """
    static = list(cfg.searches)
    if cfg.watchlist is None:
        return static
    return (
        build_self_searches(cfg.watchlist.self_entity)
        + static
        + build_watchlist_searches(cfg.watchlist)
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


# --- Self-byline verification (page-level) -------------------------------

# Cap on page fetches per run, so a badly-scoped byline_outlets list can never
# turn the fetch step into a crawl.
SELF_PAGE_FETCH_CAP = 60
SELF_PAGE_TIMEOUT = 12.0
_SELF_PAGE_BYTES = 300_000


def _host_of(url: str) -> str:
    from urllib.parse import urlsplit
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def is_byline_outlet(url: str, entity: SelfEntity | None) -> bool:
    """True when this URL is on an outlet that publishes Midya's work."""
    if entity is None or not entity.byline_outlets:
        return False
    host = _host_of(url)
    return any(
        host == o.removeprefix("www.") or host.endswith("." + o.removeprefix("www."))
        for o in entity.byline_outlets
    )


def _fetch_page_text(url: str, timeout: float = SELF_PAGE_TIMEOUT) -> str:
    """Fetch a page and return its tag-stripped text, capped and best-effort."""
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            if not r.is_success:
                return ""
            return r.text[:_SELF_PAGE_BYTES]
    except Exception as e:
        log.debug("self-byline page fetch failed for %s: %s", url, e)
        return ""


def annotate_self_bylines(
    articles: list[Article], entity: SelfEntity | None, max_workers: int = 6
) -> int:
    """Second-tier self detection: scan page bodies on byline outlets.

    Necessary because feed metadata is not enough. ICEF Monitor — the outlet
    that ran Midya's first guest piece — stamps author='editor' on every item
    and truncates the RSS summary above the byline, so her 2026-08-26 article
    was indistinguishable from wire copy until you opened the page. Only the
    body says "guest post contributed by Midya U of Midya U Advisory".

    Restricted to `byline_outlets` hosts and hard-capped, so this costs a
    handful of requests per run rather than a crawl. Sets `article.self_match`
    in place and returns how many it flagged.
    """
    if entity is None or not entity.is_configured():
        return 0

    targets = [
        a for a in articles
        if not a.self_match and is_byline_outlet(a.url, entity)
    ][:SELF_PAGE_FETCH_CAP]
    if not targets:
        return 0

    log.info("Scanning %d page(s) on byline outlets for Midya's own coverage", len(targets))
    hits = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_art = {ex.submit(_fetch_page_text, a.url): a for a in targets}
        for fut in as_completed(future_to_art):
            art = future_to_art[fut]
            html = fut.result()
            if not html:
                continue
            match = match_self_in_page(html, entity)
            if match:
                art.self_match = match
                hits += 1
                log.info("Self-coverage match on %s (%s): %s", art.source, match, art.title)
    return hits


def match_self_in_page(html: str, entity: SelfEntity) -> str:
    """Return the name/domain found in a page body, or ''.

    Checks raw HTML for owned domains (they live in href attributes, which
    tag-stripping would throw away) and stripped text for names.
    """
    lowered = html.lower()
    for domain in entity.domains:
        d = domain.lower().removeprefix("www.")
        if d and d in lowered:
            return d
    text = _strip_html(html)
    for name in entity.names:
        pattern = re.compile(r"\b" + r"\s+".join(re.escape(p) for p in name.split()) + r"\b", re.IGNORECASE)
        if pattern.search(text):
            return name
    return ""
