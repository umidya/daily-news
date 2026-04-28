# daily-news -- context for future Claude sessions

## Project layout (April 2026 onward)

This folder lives at `~/Desktop/AI-Projects/daily-news/` and contains two sibling projects:

- **`app/`** — React Native + Expo + TypeScript mobile prototype. This is the new front door for Midya's morning briefing experience and is currently UI-only with mock data.
- **Root (`src/`, `config/`, `templates/`, etc.)** — the existing Python pipeline (this CLAUDE.md is about that piece). The plan is for the pipeline to eventually expose a thin API that the app consumes.

## What this is

A personal morning news digest for Midya. Fetches from curated RSS feeds and Google News, deduplicates, scores for relevance to her interests, has Claude write executive-style summaries, generates audio with OpenAI TTS, and publishes a podcast feed + minimalist web page on GitHub Pages.

Runs daily on GitHub Actions at 13:30 UTC.

## Her interests (drives scoring + summarization tone)

- AI news
- Marketing
- Higher education in Canada and globally (her work)
- International student policy in Canada (her work)
- Canadian real estate and mortgages
- Kamloops, Sun Peaks (where she lives / spends time)
- AirBnb policies in Vancouver, Langley, Sun Peaks
- Global business / economy / tech as it relates to her work
- Food recalls in BC (family safety)

She is a senior marketing exec pivoting into consulting. The digest tone should feel like a trusted advisor's executive briefing, not a news ticker.

## Where decisions live

| Decision | File |
|----------|------|
| Which sources to fetch | `config/feeds.yaml` |
| Which search queries to run | `config/searches.yaml` |
| Topic weights, keywords, scoring formula coefficients, story count, recency cutoff | `config/interests.yaml` |
| Voice, TTS model, chunking | `src/daily_news/tts.py` (top-level constants) |
| Claude model, system prompt | `src/daily_news/summarize.py` |
| HTML template / visual design | `templates/digest.html`, `static/style.css` |
| Schedule | `.github/workflows/daily.yml` (cron line) |

Default to editing config files before touching code.

## Conventions

- Python 3.9+ (forward-compat with `from __future__ import annotations`)
- No external database; SQLite in `data/articles.db`, persisted across runs via the `state` branch
- Public assets to `public/` -> deployed to `gh-pages` via peaceiris/actions-gh-pages
- Two-layer dedup: canonical URL hash, then rapidfuzz token_set_ratio on normalized titles (threshold 88)
- Scoring: `0.5*relevance + 0.2*credibility + 0.15*recency + 0.15*novelty`. Recency is exponential decay with a 12h half-life over a 36h cutoff.

## When changing things

- **Adding a feed:** add an entry to `config/feeds.yaml`; the fetcher logs and skips dead feeds, so a broken URL won't break the run.
- **Tuning relevance:** start with topic weights, then keyword lists. Run `python -m daily_news run --mode dry` and read the printed candidate list to check.
- **Changing the audio voice:** edit `OPENAI_TTS_VOICE` in `src/daily_news/tts.py`.
- **Reducing cost:** lower `candidate_pool_size` (sends fewer tokens to Claude) or `target_story_count` (shorter audio).

## Testing

`pytest` covers dedup, scoring, DB roundtrips, config loading, and TTS chunking. None of the tests hit external APIs. New behavioural changes (especially scoring or dedup) should add a test.

## Cost guardrails

Each daily run is ~$0.10-0.15 (Claude Sonnet + OpenAI TTS HD). Monthly: ~$3-5. If costs balloon, check that recency cutoff is dropping old articles and that `candidate_pool_size` hasn't been increased.
