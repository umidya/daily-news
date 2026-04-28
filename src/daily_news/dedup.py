from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rapidfuzz import fuzz

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "ref_url",
    "_hsenc", "_hsmi", "hsCtaTracking", "hsa_acc", "hsa_cam",
    "ICID", "icid", "cmpid", "CMPID", "ito", "yptr", "ncid",
    "via", "share", "shareadraft", "embedded-checkout",
    "cid", "campaign_id", "guccounter", "guce_referrer", "guce_referrer_sig",
}


def canonicalize_url(url: str) -> str:
    """Strip tracking params and normalize for stable hashing."""
    if not url:
        return url
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.startswith("m."):
        netloc = netloc[2:]
    path = re.sub(r"/+$", "", parsed.path) or "/"
    cleaned_query = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in {p.lower() for p in TRACKING_PARAMS}
    ]
    cleaned_query.sort()
    query = urlencode(cleaned_query)
    return urlunparse(("https", netloc, path, "", query, ""))


def url_hash(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_PUNCT_RE = re.compile(r"[^\w\s]+")
_WS_RE = re.compile(r"\s+")
_PREFIX_RE = re.compile(
    r"^(breaking|exclusive|opinion|analysis|live|update|video|watch|photos)\s*[:\-|]\s*",
    re.IGNORECASE,
)


def normalize_title(title: str) -> str:
    if not title:
        return ""
    t = _PREFIX_RE.sub("", title.strip())
    t = t.lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def title_similarity(a: str, b: str) -> float:
    """Returns similarity 0-100. Uses token_set_ratio so word reordering and
    extra wire-service tags don't break dedup."""
    if not a or not b:
        return 0.0
    return float(fuzz.token_set_ratio(a, b))


def is_duplicate_title(
    candidate: str, existing: list[str], threshold: float = 88.0
) -> bool:
    return any(title_similarity(candidate, e) >= threshold for e in existing)
