# daily-news -- context for future Claude sessions

## Project layout (April 2026 onward)

This folder lives at `~/Desktop/AI-Apps/daily-news/` and contains two sibling projects:

- **`app/`** — React Native + Expo + TypeScript mobile app. This is the front door for Midya's morning briefing experience; it fetches the real `today.json` + MP3 that the pipeline publishes to GitHub Pages (no longer mock data).
- **Root (`src/`, `config/`, `templates/`, etc.)** — the existing Python pipeline (this CLAUDE.md is about that piece). The plan is for the pipeline to eventually expose a thin API that the app consumes.

## What this is

A personal morning news digest for Midya. Fetches from curated RSS feeds and Google News, deduplicates, scores for relevance to her interests, has Claude write executive-style summaries, generates audio with OpenAI TTS, and publishes a podcast feed + minimalist web page on GitHub Pages.

Runs daily on GitHub Actions. Trigger chain: a Cloudflare Worker cron fires `workflow_dispatch` at 11:30 UTC (primary); 8 schedule crons between 10:23–13:47 UTC are independent fallbacks (a same-day skip guard makes duplicate fires ~free); an Anthropic cloud watchdog routine at 14:30 UTC auto-recovers a stale `today.json` and emails only when stuck. gh-pages audio is pruned to the last 30 days in CI (GitHub Pages has a 1 GB site limit).

## Briefing structure (locked April 2026; Watchlist added July 2026)

Every digest is organized into up to nine named sections (in this order). Sections with no qualifying news are omitted, not padded.

0. **Watchlist** — `watchlist`. Stories materially involving orgs on Midya's client/prospect/peer watchlist. Config lives in `config/watchlist.yaml` + `config/peer_orgs.yaml` — **gitignored** (public repo; they name clients). CI materializes them from the `DAILY_NEWS_WATCHLIST_YAML` / `DAILY_NEWS_PEER_ORGS_YAML` repo secrets; update the secret when the local file changes (`gh secret set DAILY_NEWS_WATCHLIST_YAML < config/watchlist.yaml`). Published output must never frame these orgs as relationships.
1. **AI & Tech** — `ai`
2. **Marketing & Business** — `marketing` (or `global_business_tech` when dominantly business)
3. **Higher Education** — `higher_ed_canada` / `higher_ed_global` / `intl_students_canada`. Specifically flag stories about named Canadian universities (potential consulting clients).
4. **Real Estate & AirBnB** — `canadian_real_estate` / `airbnb_policy`. Real estate scope: Canada + North America + **eXp Realty**. AirBnB scope: BC, Vancouver, Langley, Sun Peaks policy only.
5. **Local News** — `kamloops_sun_peaks`. Sun Peaks and Kamloops only — NOT Vancouver, NOT generic BC.
6. **Global News** — `global_business_tech`. World events and geopolitics relevant to a senior leader.
7. **Longevity** — `longevity`. **Strict source allowlist**: NEJM, Lancet, JAMA, BMJ, Nature Medicine, Nature, Science, NIH, Harvard Health, Mayo Clinic, Cleveland Clinic, STAT News, Cochrane. Drop anything from wellness blogs or supplement marketers.
8. **Misc** — `misc`. Catch-all for things Midya should see: BC food recalls (always include if present), wildfire/atmospheric river/earthquake alerts, surprising cross-cutting items.

Target ~16 stories total, 1–3 per active section.

Audience: Midya — senior marketing exec in BC, pivoting into consulting, lives in Sun Peaks, BC (frequently in Kamloops). Tone: trusted advisor's executive briefing, not a news ticker.

Two intelligence features (July 2026):
- **Cross-day memory** — the summarizer receives the last 3 days' chosen stories (`recent_digest_stories` in `db.py`) and is instructed to frame follow-ups as updates and drop no-news re-covers.
- **Content angles** — every story carries a required `content_angle` field (null for most; a one-line thought-leadership hook on ≤2 stories/day). Exported as `contentAngle` in `today.json` so Sloane's content pipeline can read it from the public URL.

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

The summarizer runs Claude Opus 4.8 ($5/$25 per MTok) with adaptive thinking — curation quality is the product, and the delta over Sonnet is cents. Expect ~$0.30-0.60 per run (Claude ~$0.25-0.45 incl. thinking tokens + OpenAI TTS HD ~$0.05-0.10); truncation-guard retries can multiply the Claude portion up to 3x on a bad day. Monthly: roughly $10-20. If costs balloon, check that the recency cutoff is dropping old articles, that `candidate_pool_size` hasn't been increased, and how often the truncation guard is retrying (visible in Actions logs).
