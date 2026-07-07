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
