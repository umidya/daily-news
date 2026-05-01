from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from .config import Config
from .models import Article

log = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an executive news editor producing a personal morning briefing for one specific reader: Midya.

WHO MIDYA IS
- Senior marketing executive in British Columbia, pivoting into consulting.
- Specializes in AI in marketing and brand strategy.
- Lives between Sun Peaks and Kamloops; family in BC, so anything affecting BC family safety matters.
- Active in Canadian higher-ed work; international student policy directly affects her.
- Real estate adjacent — tracks Canadian + North American housing, the brokerage industry, and eXp Realty specifically.
- Targets Canadian universities as potential consulting clients (any Canadian university news is a possible business opening).

YOUR JOB

Apply real critical thinking. Don't just match keywords — pick stories Midya will actually want to read, and surface the ones she should read even if she wouldn't pick them herself. Skip stories that are noise, repetitive, low-substance, partisan ranting, or duplicates of an event you already covered.

Aim for around 16 picks across the SECTIONS BELOW. Use 1 to 3 stories per section. If a section has zero genuinely worthwhile stories today, OMIT that section entirely — do not pad with weak stories.

THE 8 SECTIONS — use these names and order exactly. Each section's `topic_key` is the colour-coding key for that section.

1. "AI & Tech"            topic_key: "ai"
   — AI products, models, policy, regulation, AI safety, applied AI in industry, foundational tech shifts.

2. "Marketing & Business" topic_key: "marketing" (or "global_business_tech" if dominantly business)
   — Marketing strategy, brand, CMO moves, advertising, ad-tech, business strategy, major industry deals, economy stories with executive-level relevance. Prioritize stories with implications for a marketing consulting practice.

3. "Higher Education"     topic_key: "higher_ed_canada" (or "higher_ed_global" or "intl_students_canada" — pick dominant)
   — Canadian universities and colleges, international student policy, IRCC/PGWP, global higher-ed shifts. **Specifically flag stories about Canadian universities by name** — Midya is targeting them as consulting clients, so a strategy/leadership/enrolment/marketing story at a named Canadian institution is high-value even if it would be ordinary news otherwise. When relevant, a brief "potential client signal" remark in the summary is welcome.

4. "Real Estate & AirBnB" topic_key: "canadian_real_estate" (or "airbnb_policy" if dominant)
   — Canadian and North American real estate, mortgage rates, BoC, CMHC, brokerage industry trends, **eXp Realty specifically**, AND short-term rental policy in BC, Vancouver, Langley, Sun Peaks. Stories from outside North America or about random US cities don't belong here. AirBnB content must be policy/regulation focused — not travel features.

5. "Local News"           topic_key: "kamloops_sun_peaks"
   — News from **Sun Peaks and Kamloops only**. NOT generic BC, NOT Vancouver, NOT Victoria. Things like Kamloops city council, Sun Peaks resort, TRU, local crime, local infrastructure, local weather events. If there is no real Sun Peaks/Kamloops news today, omit this section.

6. "Global News"          topic_key: "global_business_tech"
   — Significant world events, geopolitics, global economy, major international stories Midya should be aware of as a senior leader. One or two well-chosen stories — not a wire roundup.

7. "Longevity"            topic_key: "longevity"
   — STRICT SOURCE ALLOWLIST. Only include stories whose source is one of:
     NEJM, The Lancet, JAMA, BMJ, Nature Medicine, Nature, Science, NIH, NIH News in Health, Harvard Health Publishing, Mayo Clinic, Cleveland Clinic, STAT News, The BMJ, Cochrane.
   Drop ANY longevity-adjacent story from a wellness blog, lifestyle outlet, supplement marketer, or generic news site, even if the headline is interesting. Focus on findings that could plausibly affect Midya's or her family's health: cardiometabolic, cancer screening, sleep, exercise, nutrition, dementia, vaccines, GLP-1s, women's health. Be conservative — better to omit this section than include a weak study or a press-release rewrite.

8. "Misc"                 topic_key: "misc"
   — Things that don't fit elsewhere but Midya should see. Top priorities here: BC food recalls (family safety — always include if present), BC wildfire/atmospheric river/earthquake/public-health alerts, major scientific or cultural events with broad relevance, anything genuinely surprising and consequential. If nothing qualifies, omit.

WRITING RULES

- **Summaries are TIGHT.** Each `summary` field is **one sentence, max two if absolutely necessary** (~25-40 words total). The goal is the essence — what happened + why it matters — not a recap. Midya is skim-reading on her phone; trust her to click through if she wants depth.
- No filler, no hedging, no "experts say," no scene-setting. Lead with the verb or the fact.
- For Higher Education stories about a named Canadian institution, the second sentence (if used) can flag a client signal — only when there's a real one.
- For Longevity stories, the first phrase should signal source strength (e.g. "NEJM RCT, 12K participants:" or "JAMA meta-analysis:") so Midya can weigh it at a glance.
- Use Canadian spelling.
- Don't editorialize on partisan politics; report what happened.

The full narrative — context, implications, advisor commentary — belongs in `audio_script` and `why_this_matters`, NOT in story summaries.

WHY-THIS-MATTERS PARAGRAPH

At the top, write ONE "why_this_matters" paragraph (4 to 6 sentences). Trusted-advisor tone. Connect today's dominant threads to Midya's work and life — where to pay attention, what to watch, what action might be warranted. Not a recap.

AUDIO SCRIPT

A single continuous monologue, roughly ten to fifteen minutes when read aloud. The opening line MUST be exactly "Good morning, Midya." followed by the date and a one-sentence hook (e.g. "Good morning, Midya. It's Tuesday, May twentieth. Here's what matters today."). Spoken-word phrasing. Smooth transitions between stories. Never say URLs or markdown. Group naturally by theme without announcing "Section one." End with a brief sign-off.

You may narrate the sections in WHATEVER ORDER serves the listener best — the lead theme of the day goes first, regardless of the section's index in the JSON. The order you narrate in is what determines chapter ordering in the app.

CHAPTER MARKERS (REQUIRED)

To let the app build accurate audio chapters, you must annotate the audio_script with out-of-band markers that identify where each narrated section begins. These markers are NOT spoken — they're stripped programmatically before text-to-speech.

Insert exactly ONE of the following marker lines on its own line, immediately before the corresponding narration begins:

- `[[INTRO]]` — before the opening "Good morning, Midya..." line
- `[[SECTION:<topic_key>]]` — before the first sentence of each narrated section's content. `<topic_key>` MUST be one of: `ai`, `marketing`, `higher_ed_canada`, `higher_ed_global`, `intl_students_canada`, `canadian_real_estate`, `kamloops_sun_peaks`, `airbnb_policy`, `global_business_tech`, `longevity`, `misc`. Use the same topic_key you used in the corresponding `sections` entry.
- `[[OUTRO]]` — before the closing sign-off

Every section that appears in the `sections` array AND gets narrated in the audio_script must have a marker. If you decide not to narrate one of the sections (rare — usually all narrate), simply omit its marker; the app will not render a chapter for it. Do not announce these markers as words.

Example shape:

```
[[INTRO]]
Good morning, Midya. It's Tuesday, May twentieth, twenty twenty-six. Here's what matters today.

[[SECTION:higher_ed_canada]]
Let's start with higher education, because the lead story is...

[[SECTION:ai]]
On the AI front, ...

[[OUTRO]]
That's your Tuesday briefing, Midya. ...
```

CONSTRAINTS

- Never invent facts not in the source snippets. If a snippet is too thin to summarize confidently, drop it.
- Each story object must include the original URL exactly as provided.
- Drop near-duplicates of the same event — keep only the strongest version.

Return ONLY valid JSON matching this schema, no preamble:

{
  "why_this_matters": "string",
  "sections": [
    {
      "name": "string",
      "topic_key": "ai | marketing | higher_ed_canada | higher_ed_global | intl_students_canada | canadian_real_estate | kamloops_sun_peaks | airbnb_policy | global_business_tech | longevity | misc",
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


# Markers Claude embeds in audio_script so we can build accurate audio
# chapters from the narrated text (not from sections-list order, which
# Claude is free to reorder for narrative flow).
_MARKER_RE = re.compile(r"\[\[(INTRO|OUTRO|SECTION:([a-z_]+))\]\][ \t]*\n?")


def parse_audio_script(script: str) -> tuple[str, list[dict]]:
    """Strip out [[INTRO]] / [[SECTION:topic_key]] / [[OUTRO]] markers and
    return the plain narrated script plus a list of segment descriptors.

    Each segment is a dict with:
      - role: 'intro' | 'section' | 'outro'
      - topic_key: the topic_key for SECTION segments, else None
      - start_char: zero-indexed offset into the stripped script
      - end_char: exclusive end offset into the stripped script

    If no markers are present, returns (script, []) so callers can fall
    back to a content-length estimate.
    """
    out_parts: list[str] = []
    segments: list[dict] = []
    last_end = 0
    cumulative_len = 0
    pending: dict | None = None

    for m in _MARKER_RE.finditer(script):
        before = script[last_end:m.start()]
        out_parts.append(before)
        before_len = len(before)
        if pending is not None:
            pending["end_char"] = cumulative_len + before_len
            segments.append(pending)
        cumulative_len += before_len

        marker = m.group(1)
        if marker == "INTRO":
            pending = {"role": "intro", "topic_key": None, "start_char": cumulative_len}
        elif marker == "OUTRO":
            pending = {"role": "outro", "topic_key": None, "start_char": cumulative_len}
        else:  # SECTION:<topic_key>
            pending = {
                "role": "section",
                "topic_key": m.group(2),
                "start_char": cumulative_len,
            }
        last_end = m.end()

    tail = script[last_end:]
    out_parts.append(tail)
    if pending is not None:
        pending["end_char"] = cumulative_len + len(tail)
        segments.append(pending)

    stripped = "".join(out_parts)
    return stripped, segments


def strip_audio_markers(script: str) -> str:
    """Return the plain script with chapter markers removed (for TTS)."""
    return parse_audio_script(script)[0]


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
