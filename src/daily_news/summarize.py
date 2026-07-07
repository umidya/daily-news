from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import anthropic
from anthropic import Anthropic

from .config import Config, Watchlist
from .models import Article

log = logging.getLogger(__name__)

# Opus for editorial judgment — curation quality is the product. ~2-3x Sonnet
# token cost but still cents per run; see CLAUDE.md cost guardrails.
CLAUDE_MODEL = "claude-opus-4-8"

_TOPIC_KEYS = [
    "watchlist",  # section 1 — orgs from config/watchlist.yaml (clients, prospects, peers)
    "ai",
    "marketing",
    "higher_ed_canada",
    "higher_ed_global",
    "intl_students_canada",
    "canadian_real_estate",
    "kamloops_sun_peaks",
    "airbnb_policy",
    "global_business_tech",
    "longevity",
    "misc",
]

# JSON Schema passed to the API via output_config.format. The API guarantees
# the response is valid JSON matching this shape — eliminates the class of
# JSONDecodeError failures we saw on 2026-05-12 when Claude's free-form JSON
# had a subtle quoting bug deep in audio_script.
_DIGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "why_this_matters": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "topic_key": {"type": "string", "enum": _TOPIC_KEYS},
                    "stories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "headline": {"type": "string"},
                                "summary": {"type": "string"},
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "content_angle": {"type": ["string", "null"]},
                            },
                            "required": ["headline", "summary", "source", "url", "content_angle"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "topic_key", "stories"],
                "additionalProperties": False,
            },
        },
        "audio_script": {"type": "string"},
    },
    "required": ["why_this_matters", "sections", "audio_script"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are an executive news editor producing a personal morning briefing for one specific reader: Midya.

WHO MIDYA IS

- Founder of Midya U Advisory (BC sole-proprietorship) — a marketing and AI-in-marketing consulting practice. Two industry lanes she actively sells into: Canadian higher education (especially enrollment, recruitment, brand) and real estate (residential brokerage + commercial investment sales, Western Canada focus).
- Senior marketing executive by background; pivoting fully into consulting through 2026–2027.
- Lives in Sun Peaks, BC; frequently in Kamloops, the nearest city (so both Sun Peaks and Kamloops local news matter). Owns property in Sun Peaks, Langley, and Vancouver — BC short-term-rental and housing policy in those areas is personally relevant. Family in BC, so anything affecting BC family safety matters.
- Signature methodologies she's productizing: (1) AI Search Readiness — auditing how brands appear in Google AI Mode, AI Overviews, ChatGPT, Perplexity; (2) Public-Institution Governance Lens — FIPPA, BC data residency, public-sector AI policy applied to client recommendations.
- Her husband owns a residential real estate brokerage (Edmonton + Vancouver). Real estate news enters this briefing for genuine professional reasons (a real-estate industry lane in her practice), not personal interest.
- 2026–2027 goal: establish herself as a recognized thought leader in AI — specifically AI applied to marketing, higher-ed enrollment, real estate operations, and public-institution governance. News she sees should feed BOTH her client work AND her thought-leadership content pipeline.

YOUR JOB

Apply real critical thinking. Don't just match keywords — pick stories Midya will actually want to read, and surface the ones she should read even if she wouldn't pick them herself. Skip stories that are noise, repetitive, low-substance, partisan ranting, or duplicates of an event you already covered.

Aim for around 16 picks across the SECTIONS BELOW. Use 1 to 3 stories per section (the Watchlist section may include up to 4). If a section has zero genuinely worthwhile stories today, OMIT that section entirely — do not pad with weak stories.

THE 9 SECTIONS — use these names and order exactly. Each section's `topic_key` is the colour-coding key for that section.

1. "Watchlist"            topic_key: "watchlist"
   — Stories that materially involve any organization on Midya's watchlist (provided in the user message under WATCHLIST_ORGS). Watchlist orgs include current clients, active prospects, and peer/competitor consultancies in her market.

   FRAMING RULE — CRITICAL, NON-NEGOTIABLE:
     - NEVER describe any watchlist org as "your client," "your prospect," "your engagement," or "your peer."
     - NEVER imply Midya has any relationship to the org.
     - Write strictly as a sharp news editor who happens to cover these orgs closely for industry-coverage reasons.
     - This applies to story summaries, the why_this_matters paragraph, AND the audio script.

   Include 1–4 stories. Omit the section if no qualifying stories today. Do NOT pad with weak hits — a watchlist org being mentioned in a passing roundup doesn't qualify. The story should genuinely be about them or materially affect them.

2. "AI & Tech"            topic_key: "ai"

   Filter ruthlessly through MIDYA'S TWO LENSES:

   (a) PROFESSIONAL LENS — AI news that materially affects her consulting work: AI tools/practices being adopted by marketing teams, higher-ed enrollment offices, real estate brokerages, public-sector institutions. New AI features in martech, CRM, search (especially generative search — Google AI Mode, AI Overviews, ChatGPT search, Perplexity), and AI policy/regulation hitting Canadian public institutions or commerce. SKIP: AI consumer gadgets, generic model benchmarks, and AI culture-war commentary unless it intersects her work.

   (b) THOUGHT-LEADERSHIP LENS — stories she could plausibly comment on publicly within her POV (AI in marketing / higher-ed / RE / public-institution governance). Specifically prize: contrarian findings, real adoption case studies (not hype), regulatory shifts, and stories where senior leaders are taking defensible positions. These are commentary fuel, not just "AI happened."

   Aim for 2–3 stories here, weighted toward the professional lens. The lead AI story of the day should make her think "I should post about this" OR "this changes how I advise clients."

3. "Marketing & Business" topic_key: "marketing" (or "global_business_tech" if dominantly business)
   — Marketing strategy, brand, CMO moves, advertising, ad-tech, business strategy, major industry deals, economy stories with executive-level relevance. Prioritize stories with implications for a marketing consulting practice.

4. "Higher Education"     topic_key: "higher_ed_canada" (or "higher_ed_global" or "intl_students_canada" — pick dominant)
   — Canadian universities and colleges, international student policy, IRCC/PGWP, global higher-ed shifts. Stories about named Canadian institutions are high-value — Midya works in this market. When a story names a watchlist org, it belongs in section 1 (Watchlist), not here.

5. "Real Estate & AirBnB" topic_key: "canadian_real_estate" (or "airbnb_policy" if dominant)
   — Canadian and North American real estate, mortgage rates, BoC, CMHC, brokerage industry trends, residential AND commercial real estate (Western Canada matters most), AND short-term rental policy in BC, Vancouver, Langley, Sun Peaks. Stories from outside North America or about random US cities don't belong here. AirBnB content must be policy/regulation focused — not travel features.

6. "Local News"           topic_key: "kamloops_sun_peaks"
   — News from **Sun Peaks and Kamloops only**. NOT generic BC, NOT Vancouver, NOT Victoria. Things like Kamloops city council, Sun Peaks resort, TRU, local crime, local infrastructure, local weather events. If there is no real Sun Peaks/Kamloops news today, omit this section.

7. "Global News"          topic_key: "global_business_tech"
   — Significant world events, geopolitics, global economy, major international stories Midya should be aware of as a senior leader. One or two well-chosen stories — not a wire roundup.

8. "Longevity"            topic_key: "longevity"
   — STRICT SOURCE ALLOWLIST. Only include stories whose source is one of:
     NEJM, The Lancet, JAMA, BMJ, Nature Medicine, Nature, Science, NIH, NIH News in Health, Harvard Health Publishing, Mayo Clinic, Cleveland Clinic, STAT News, The BMJ, Cochrane.
   Drop ANY longevity-adjacent story from a wellness blog, lifestyle outlet, supplement marketer, or generic news site, even if the headline is interesting. Focus on findings that could plausibly affect Midya's or her family's health: cardiometabolic, cancer screening, sleep, exercise, nutrition, dementia, vaccines, GLP-1s, women's health. Be conservative — better to omit this section than include a weak study or a press-release rewrite.

9. "Misc"                 topic_key: "misc"
   — Things that don't fit elsewhere but Midya should see. Top priorities here: BC food recalls (family safety — always include if present), BC wildfire/atmospheric river/earthquake/public-health alerts, major scientific or cultural events with broad relevance, anything genuinely surprising and consequential. If nothing qualifies, omit.

WRITING RULES

- **Summaries are TIGHT.** Each `summary` field is **one sentence, max two if absolutely necessary** (~25-40 words total). The goal is the essence — what happened + why it matters — not a recap. Midya is skim-reading on her phone; trust her to click through if she wants depth.
- No filler, no hedging, no "experts say," no scene-setting. Lead with the verb or the fact.
- For Higher Education stories about a named Canadian institution, the second sentence (if used) can flag a client signal — only when there's a real one.
- For Longevity stories, the first phrase should signal source strength (e.g. "NEJM RCT, 12K participants:" or "JAMA meta-analysis:") so Midya can weigh it at a glance.
- Use Canadian spelling.
- Don't editorialize on partisan politics; report what happened.

CONTENT ANGLE (`content_angle` field — required on every story)

For AT MOST 2 stories per day — only the ones with genuine thought-leadership potential for Midya — set `content_angle` to a single sentence naming the content lane it feeds (AI in marketing, AI in higher-ed enrollment, AI in real estate operations, public-institution AI governance, or AI Search Readiness) plus the specific take she could publish. Example: "AI in higher-ed enrollment: universities buying AI chatbots without governance frameworks — the audit checklist angle." For every other story, set `content_angle` to null. Be selective: a day with zero content angles is fine; a day with 5 is a failure of judgment.

RECENT COVERAGE (memory across days)

The user message may include a RECENT_COVERAGE list — stories that already appeared in the last few briefings. Rules:
- Do NOT re-cover a story from that list unless there is a genuine NEW development in today's candidates.
- When today's story IS a development of a recently covered one, explicitly frame it as an update in both the summary and the narration (e.g. "An update on the Kamloops council story from Friday: ..."). Continuity is a feature — Midya should feel the briefing remembers what it told her.
- Candidates that merely re-report a recently covered story with no new substance are duplicates — drop them.

The full narrative — context, implications, advisor commentary — belongs in `audio_script` and `why_this_matters`, NOT in story summaries.

WHY-THIS-MATTERS PARAGRAPH

At the top, write ONE "why_this_matters" paragraph (4 to 6 sentences). Trusted-advisor tone. Connect today's dominant threads to Midya's work and life — where to pay attention, what to watch, what action might be warranted. Not a recap.

AUDIO SCRIPT

A single continuous monologue. **Target length: 2400 to 3200 words (≈15 to 20 minutes when read aloud at standard TTS speed). Treat 2400 words as a hard floor — do not under-deliver.**

If the news cycle is light, do NOT shorten the briefing. Instead, deepen: expand commentary, advisor framing, why-it-matters context, implications for Midya's specific work (consulting pivot, AI thesis, BC family, Canadian higher-ed pipeline). The "do not pad with weak stories" rule still applies — the path to length is depth on the chosen stories, not adding more stories. A short briefing fails the assignment; weak stories fail the assignment. The way through is fewer-but-richer.

The opening line MUST be exactly "Good morning, Midya." followed by the date and a one-sentence hook (e.g. "Good morning, Midya. It's Tuesday, May twentieth. Here's what matters today."). Spoken-word phrasing. Smooth transitions between stories. Never say URLs or markdown. Group naturally by theme without announcing "Section one." End with a substantive sign-off (2-3 sentences, advisor tone) — not a perfunctory "have a good day."

You may narrate the sections in WHATEVER ORDER serves the listener best — the lead theme of the day goes first, regardless of the section's index in the JSON. The order you narrate in is what determines chapter ordering in the app.

CHAPTER MARKERS (REQUIRED)

To let the app build accurate audio chapters, you must annotate the audio_script with out-of-band markers that identify where each narrated section begins. These markers are NOT spoken — they're stripped programmatically before text-to-speech.

Insert exactly ONE of the following marker lines on its own line, immediately before the corresponding narration begins:

- `[[INTRO]]` — before the opening "Good morning, Midya..." line
- `[[SECTION:<topic_key>]]` — before the first sentence of each narrated section's content. `<topic_key>` MUST be one of: `watchlist`, `ai`, `marketing`, `higher_ed_canada`, `higher_ed_global`, `intl_students_canada`, `canadian_real_estate`, `kamloops_sun_peaks`, `airbnb_policy`, `global_business_tech`, `longevity`, `misc`. Use the same topic_key you used in the corresponding `sections` entry.
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
      "topic_key": "watchlist | ai | marketing | higher_ed_canada | higher_ed_global | intl_students_canada | canadian_real_estate | kamloops_sun_peaks | airbnb_policy | global_business_tech | longevity | misc",
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


# Publish floor for the narration. The system prompt targets 2400-3200 words
# (~15-20 min) and treats 2400 as a hard floor even on light news days. We set
# the *publish* floor well below that so a genuinely-shorter-but-complete
# briefing is never rejected, yet far above the ~750-word fragments we have
# shipped when the narration was truncated. Anything under this is treated as a
# truncation, not a short day.
AUDIO_SCRIPT_MIN_WORDS = 1500

# A complete narration always ends on its [[OUTRO]] sign-off, i.e. on
# sentence-final punctuation. A fragment ends mid-word/clause (e.g. the
# 2026-06-17 briefing ended on "...moving from").
_TERMINAL_PUNCT = (".", "!", "?", '"', "”", "…")


class TruncatedDigestError(Exception):
    """Raised when Claude returns a digest whose narration is incomplete.

    Treated as a retryable failure inside summarize(): a fresh generation
    usually completes. If every attempt is truncated we fail loud rather than
    publish a partial briefing (the app then keeps yesterday's good one)."""


def validate_digest(digest: "Digest") -> list[str]:
    """Return a list of completeness problems that must block publishing.

    An empty list means the digest is publishable. This is the guard that
    prevents a truncated briefing from reaching the app. The audio_script is
    generated as the FINAL field of a single schema-constrained Claude call;
    when generation is cut short the JSON still parses (the constrained decoder
    closes it) but the narration is a fragment. We reject that fragment here
    instead of synthesizing a 4-minute stub from it."""
    problems: list[str] = []

    if not (digest.why_this_matters or "").strip():
        problems.append("why_this_matters is empty")
    if not digest.sections:
        problems.append("no sections produced")

    script = (digest.audio_script or "").strip()
    if not script:
        problems.append("audio_script is empty")
        return problems  # nothing further to check

    stripped, segments = parse_audio_script(script)
    stripped = stripped.strip()

    words = len(stripped.split())
    if words < AUDIO_SCRIPT_MIN_WORDS:
        problems.append(
            f"audio_script is only {words} words (floor {AUDIO_SCRIPT_MIN_WORDS}); "
            "narration was likely truncated"
        )

    roles = {seg["role"] for seg in segments}
    if "outro" not in roles:
        problems.append(
            "audio_script has no [[OUTRO]] sign-off; narration was likely truncated"
        )

    if stripped and stripped[-1] not in _TERMINAL_PUNCT:
        tail = stripped[-40:]
        problems.append(
            f"audio_script ends without sentence-final punctuation (...{tail!r}); "
            "narration was likely truncated"
        )

    return problems


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


def build_watchlist_context_block(watchlist: Watchlist | None) -> str:
    """Render the volatile watchlist context for injection into the user message.

    Empty string when no watchlist is configured (or all sections are empty) —
    the pipeline then runs as it did before the watchlist feature existed.

    The block restates the framing rule from the system prompt because LLMs
    drift on multi-step framing constraints over long contexts; putting the
    rule right next to the org list is cheap insurance.
    """
    if watchlist is None:
        return ""
    if not (watchlist.clients or watchlist.prospects or watchlist.peer_orgs):
        return ""

    lines: list[str] = []
    lines.append("WATCHLIST_ORGS — orgs Midya tracks for industry-coverage reasons.")
    lines.append("")
    lines.append(
        "FRAMING REMINDER: do NOT describe any of these orgs as Midya's client, "
        "prospect, peer, or relationship in any output field. Cover them strictly "
        "as a sharp industry editor who happens to track them closely. Never "
        "imply Midya has any relationship to these orgs."
    )
    lines.append("")

    if watchlist.clients:
        lines.append("Clients (surface stories materially affecting them):")
        for c in watchlist.clients:
            alias_bit = f" (aliases: {', '.join(c.aliases)})" if c.aliases else ""
            industry_bit = f" — {c.industry}" if c.industry else ""
            lines.append(f"  - {c.org}{alias_bit}{industry_bit}")
        lines.append("")

    if watchlist.prospects:
        lines.append("Prospects (surface notable strategic news):")
        for p in watchlist.prospects:
            industry_bit = f" — {p.industry}" if p.industry else ""
            lines.append(f"  - {p.org}{industry_bit}")
        lines.append("")

    if watchlist.peer_orgs:
        lines.append("Peer/competitor orgs (industry coverage):")
        for org in watchlist.peer_orgs:
            lines.append(f"  - {org.org}")
        lines.append("")

    if watchlist.thought_leadership_themes:
        lines.append(
            "Thought-leadership themes (especially weight in AI-section picks):"
        )
        for theme in watchlist.thought_leadership_themes:
            lines.append(f"  - {theme}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


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


def _match_url_hashes(chosen_urls: list[str], candidates: list[Article]) -> list[str]:
    by_url = {a.url: a.url_hash for a in candidates}
    return [by_url[u] for u in chosen_urls if u in by_url]


def _call_claude(client: Anthropic, user_msg: str) -> tuple[dict, str, "str | None"]:
    """Single Claude call with schema-enforced JSON output.
    Returns (parsed, raw_text, stop_reason).

    Streams with adaptive thinking: max_tokens must hold thinking + the full
    briefing JSON, and non-streaming requests this large risk SDK HTTP
    timeouts. Thinking blocks are skipped when extracting the text block."""
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        output_config={"format": {"type": "json_schema", "schema": _DIGEST_SCHEMA}},
    ) as stream:
        msg = stream.get_final_message()
    raw = next(b.text for b in msg.content if b.type == "text")
    return json.loads(raw), raw, msg.stop_reason


def _build_digest(parsed: dict, raw: str, candidates: list[Article]) -> Digest:
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


def build_recent_coverage_block(recent: "list[dict] | None") -> str:
    """Render the last few briefings' chosen stories so today's call can do
    continuity ("an update on...") and avoid re-covering. Empty string when
    there's no history (first run, or fresh state)."""
    if not recent:
        return ""
    lines = ["RECENT_COVERAGE (stories already in the last briefings — see system rules):"]
    for r in recent:
        lines.append(f"  - [{r['date']}] {r['title']} ({r['source']})")
    return "\n".join(lines) + "\n"


def summarize(
    candidates: list[Article],
    cfg: Config,
    date_label: str,
    recent_coverage: "list[dict] | None" = None,
) -> Optional[Digest]:
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
    watchlist_block = build_watchlist_context_block(cfg.watchlist)
    coverage_block = build_recent_coverage_block(recent_coverage)
    user_msg = (
        f"Today's date: {date_label}.\n"
        f"Aim for around {cfg.target_story_count} stories in the final digest.\n\n"
        + (watchlist_block + "\n" if watchlist_block else "")
        + (coverage_block + "\n" if coverage_block else "")
        + "Candidates (already pre-filtered and pre-scored):\n"
        + json.dumps(payload["candidates"], ensure_ascii=False, indent=2)
    )

    log.info("Sending %d candidates to Claude for summarization", len(candidates))

    # Up to 3 attempts. We retry on transient API errors (overload, 5xx), on the
    # off chance the SDK returns malformed JSON, AND — critically — when the
    # returned digest is incomplete. A schema-constrained response can be cut
    # short mid-narration yet still parse as valid JSON (the decoder closes the
    # braces), so json.loads succeeding is NOT proof the briefing is whole.
    # validate_digest() is the real gate; a truncated result is retried, and if
    # every attempt is truncated we raise rather than publish a partial briefing
    # (the pipeline then leaves yesterday's good briefing in place).
    last_err: Exception | None = None
    digest: Digest | None = None
    for attempt in range(3):
        try:
            parsed, raw, stop_reason = _call_claude(client, user_msg)
            if stop_reason == "max_tokens":
                raise TruncatedDigestError(
                    "response hit max_tokens — narration cut off at the token ceiling"
                )
            candidate = _build_digest(parsed, raw, candidates)
            problems = validate_digest(candidate)
            if problems:
                raise TruncatedDigestError("; ".join(problems))
            digest = candidate
            break
        except (
            anthropic.APIStatusError,
            anthropic.APIConnectionError,
            json.JSONDecodeError,
            TruncatedDigestError,
        ) as e:
            last_err = e
            wait = 2 ** attempt
            log.warning(
                "Claude summarize attempt %d/3 failed (%s: %s); retrying in %ds",
                attempt + 1, type(e).__name__, e, wait,
            )
            time.sleep(wait)
    if digest is None:
        raise RuntimeError(
            f"Claude summarize failed after 3 attempts: {last_err}"
        ) from last_err

    # Soft signal: surface (but don't block on) sections that were not narrated.
    # Hard truncation is already caught above; this catches the subtler case of
    # a complete-looking script that quietly skipped a section's content.
    narrated = {
        s["topic_key"]
        for s in parse_audio_script(digest.audio_script)[1]
        if s["role"] == "section" and s.get("topic_key")
    }
    unnarrated = [
        s.get("topic_key") for s in digest.sections
        if s.get("topic_key") and s.get("topic_key") not in narrated
    ]
    if unnarrated:
        log.warning(
            "Digest has %d section(s) present but not narrated in the audio: %s",
            len(unnarrated), unnarrated,
        )

    return digest
