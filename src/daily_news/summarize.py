from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from .config import Config
from .models import Article

log = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an executive news editor producing a personal morning briefing.

Audience: a senior marketing executive based in British Columbia who is pivoting into consulting. Her interests: AI, marketing, higher education in Canada and globally, international student policy in Canada, Canadian real estate and mortgages, Kamloops and Sun Peaks news, AirBnb policy in Vancouver and Langley and Sun Peaks, global business and tech as it touches her work, and any food recalls in BC that affect her family.

Your job:
1. From the candidate articles I send you, pick the strongest 8 to 12 that genuinely matter to her. If two articles cover the same event, keep only the better one.
2. Group the picks into 3 to 5 thematic sections. Each section needs a clear plain-language `name` AND a `topic_key` chosen from this fixed list (used for colour-coding the rendered page; pick the closest fit):
   - "ai"  (AI news, AI policy, AI products, AI tools)
   - "marketing"  (marketing, advertising, brand, CMO moves)
   - "higher_ed_canada"  (Canadian universities, colleges, post-secondary)
   - "higher_ed_global"  (universities outside Canada, global research)
   - "intl_students_canada"  (study permits, IRCC, PGWP, international student policy)
   - "canadian_real_estate"  (Canadian housing, mortgage rates, BoC, CMHC)
   - "kamloops_sun_peaks"  (Kamloops, Sun Peaks, Thompson Rivers University)
   - "airbnb_policy"  (short-term rental policy in Vancouver, Langley, Sun Peaks, BC)
   - "global_business_tech"  (general business, economy, tech, markets)
   - "bc_food_recalls"  (food recalls, allergens, listeria, salmonella in Canada/BC)
3. For each pick, write a tight 2 to 3 sentence summary that says what happened, why it is news, and what the implication is. Concrete and specific. No hedging, no filler, no "experts say."
4. At the very top, write ONE "Why this matters to me" paragraph (4 to 6 sentences) that connects the day's stories to her work and life: where she should pay attention, what to watch, what action might be warranted. It should feel like a trusted advisor's two minutes of context, not a recap.
5. Write a separate audio script: a single continuous monologue meant to be read aloud in roughly ten minutes. Use spoken-word phrasing, smooth transitions between stories, and never say URLs or markdown. Open with the date and a one-sentence hook. Group naturally by theme without announcing "Section one." End with a brief sign-off.

Constraints:
- Never invent facts that are not in the source snippets. If a snippet is too thin to summarize confidently, drop it.
- Use Canadian spelling.
- Do not editorialize on partisan political topics; report what happened.
- Each story object must include the original URL exactly as provided.

Return ONLY valid JSON matching this schema, no preamble:

{
  "why_this_matters": "string",
  "sections": [
    {
      "name": "string",
      "topic_key": "ai | marketing | higher_ed_canada | higher_ed_global | intl_students_canada | canadian_real_estate | kamloops_sun_peaks | airbnb_policy | global_business_tech | bc_food_recalls",
      "stories": [
        {
          "headline": "string",
          "summary": "string",
          "source": "string",
          "url": "string"
        }
      ]
    }
  ],
  "audio_script": "string"
}
"""


@dataclass
class Digest:
    why_this_matters: str
    sections: list[dict]
    audio_script: str
    chosen_url_hashes: list[str]
    raw_response: str


def _candidates_payload(articles: list[Article]) -> list[dict]:
    out = []
    for a in articles:
        out.append({
            "title": a.title,
            "source": a.source,
            "url": a.url,
            "published": a.published_at.isoformat() if a.published_at else None,
            "topics": a.topics,
            "snippet": a.snippet,
            "score": round(a.score, 3),
        })
    return out


def _extract_json(text: str) -> dict:
    """Claude is asked to return raw JSON, but be defensive in case it wraps it
    in code fences or commentary."""
    text = text.strip()
    if text.startswith("```"):
        # strip code fence
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # last-ditch: find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _match_url_hashes(chosen_urls: list[str], candidates: list[Article]) -> list[str]:
    by_url = {a.url: a.url_hash for a in candidates}
    return [by_url[u] for u in chosen_urls if u in by_url]


def summarize(candidates: list[Article], cfg: Config, date_label: str) -> Optional[Digest]:
    if not cfg.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    if not candidates:
        return None

    client = Anthropic(api_key=cfg.anthropic_api_key)
    payload = {
        "date": date_label,
        "target_story_count": cfg.target_story_count,
        "candidates": _candidates_payload(candidates),
    }
    user_msg = (
        f"Today's date: {date_label}.\n"
        f"Aim for around {cfg.target_story_count} stories in the final digest.\n\n"
        f"Candidates (already pre-filtered and pre-scored):\n"
        + json.dumps(payload["candidates"], ensure_ascii=False, indent=2)
    )

    log.info("Sending %d candidates to Claude for summarization", len(candidates))
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = msg.content[0].text  # type: ignore[union-attr]
    parsed = _extract_json(raw)

    chosen_urls: list[str] = []
    for section in parsed.get("sections", []):
        for story in section.get("stories", []):
            if story.get("url"):
                chosen_urls.append(story["url"])

    return Digest(
        why_this_matters=parsed.get("why_this_matters", "").strip(),
        sections=parsed.get("sections", []),
        audio_script=parsed.get("audio_script", "").strip(),
        chosen_url_hashes=_match_url_hashes(chosen_urls, candidates),
        raw_response=raw,
    )
