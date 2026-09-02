from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    url: str
    canonical_url: str
    url_hash: str
    title: str
    title_normalized: str
    source: str
    published_at: Optional[datetime]
    fetched_at: datetime
    snippet: str
    topics: list[str] = field(default_factory=list)
    credibility: float = 0.75
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    # In-memory only — not persisted to the articles DB.
    image_url: Optional[str] = None
    # RSS author field, when the publisher sets one. Carried so a guest byline
    # on someone else's outlet can be recognised as Midya's own work.
    author: str = ""
    # Set by score.py when the article matches Midya's `self` block. Populated
    # with the name/domain that matched, for the summarizer to cite.
    self_match: str = ""
