# daily-news

This project has two pieces:

- **`app/`** — the React Native + Expo + TypeScript mobile app prototype (the new direction). See `app/README.md` to run it.
- **Root (`src/`, `config/`, `templates/`, etc.)** — the original Python pipeline (RSS → Claude → OpenAI TTS → podcast feed + web digest). The pipeline will eventually serve the app via a thin API; for now both run independently.

---

A personal morning news digest. It fetches from a curated list of RSS feeds and Google News searches, deduplicates, scores each story for relevance to your interests, has Claude write executive-style summaries, generates an audio digest via OpenAI TTS, and publishes both a podcast feed and a minimalist web page you can open on your iPhone.

## What you get every morning

- **A private podcast feed.** Subscribe once in Apple Podcasts; new episodes auto-download daily.
- **A web page** at `<your-base-url>/digests/<date>.html`, with a "Why this matters to me" section, sources grouped by theme, and the audio player at the top.
- **An index** at `<your-base-url>/index.html` listing every episode.
- **A SQLite history** of every article you've ever seen, so duplicates never reach you twice.

## Architecture in one paragraph

Configs live in `config/*.yaml` (feeds, search queries, topic weights). The pipeline in `src/daily_news/pipeline.py` runs end-to-end: `fetch` (concurrent HTTPX + feedparser, plus Google News RSS searches) -> `dedup` (canonical URL hashing + rapidfuzz title similarity) -> `score` (relevance + credibility + recency + novelty) -> `summarize` (Claude Sonnet, JSON output) -> `tts` (OpenAI `tts-1-hd`, `onyx` voice, chunked) -> `render` (Jinja2 HTML + feedgen RSS). State (the article DB) is committed to a `state` branch on GitHub each run so duplicates persist across runs. Public assets (HTML, MP3, RSS feed) are pushed to the `gh-pages` branch.

## Set up

### 1. Local dev

```bash
cd ~/Desktop/AI-Projects/daily-news

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pip install pytest

cp .env.example .env
# edit .env and fill in:
#   ANTHROPIC_API_KEY=...
#   OPENAI_API_KEY=...
#   DAILY_NEWS_BASE_URL=https://<your-username>.github.io/daily-news
```

### 2. Verify config and run a dry pass (no API calls)

```bash
python -m daily_news config-check
python -m daily_news run --mode dry
```

The dry mode fetches feeds, dedupes, scores, and prints the top candidates -- but does **not** call Claude or OpenAI. Use this while you tune `config/interests.yaml`.

### 3. Run the full pipeline locally

```bash
python -m daily_news run
```

This costs roughly **$0.10-0.15 per run** ($0.05 Claude + $0.05-0.10 TTS for a ten-minute digest). Output lands in:

- `data/articles.db` -- SQLite history (used for dedup)
- `data/audio/<date>.mp3` -- raw TTS output
- `public/audio/<date>.mp3` -- the published audio
- `public/digests/<date>.html` -- the web page
- `public/feed.xml` -- the podcast RSS feed
- `public/index.html` -- episode list

Open `public/digests/<date>.html` in a browser to preview.

### 4. Run the tests

```bash
pytest
```

Tests cover URL canonicalization, title fuzzy-dedup, scoring, DB roundtrips, config loading, and TTS chunking. They do not hit any external APIs.

## Deploy to GitHub Actions (daily run)

### One-time setup

1. **Create a private GitHub repo** named `daily-news` (or anything you like). Push this folder to it.

2. **Add API key secrets** at *Settings -> Secrets and variables -> Actions -> Secrets*:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`

3. **Add the public base URL as a repository variable** at *Settings -> Secrets and variables -> Actions -> Variables*:
   - `DAILY_NEWS_BASE_URL` -- the URL where GitHub Pages will serve your site, e.g. `https://umidya.github.io/daily-news`

4. **Enable GitHub Pages** at *Settings -> Pages*:
   - Source: *Deploy from a branch*
   - Branch: `gh-pages` / `(root)`
   - Save.

5. **Tighten Actions permissions** so the workflow can push to `gh-pages` and `state`:
   - *Settings -> Actions -> General -> Workflow permissions* -> Read and write permissions -> Save.

That's it. The workflow runs daily at 13:30 UTC (5:30 AM PST / 6:30 AM PDT). You can also trigger it manually from the Actions tab.

### Subscribe in Apple Podcasts

Once the first run has succeeded:

1. Open Apple Podcasts on your iPhone.
2. *Library -> ... menu -> Follow a Show by URL*.
3. Paste `https://<your-base-url>/feed.xml`.
4. Enable automatic downloads in the show settings.

You can share that URL with anyone you want subscribed. Anyone with the URL can subscribe (the feed is unlisted, not password-protected). It will not appear in any podcast directory.

### A note on URL privacy

GitHub Pages serves all files publicly. To reduce the chance someone stumbles onto your feed:

- Keep the **source repo private** (the repo settings, not the published site).
- Use an **obscure path**, e.g. host at `https://umidya.github.io/daily-news-a7k2m9q3` rather than `daily-news`. Set this when you create the repo and as `DAILY_NEWS_BASE_URL`.
- Don't submit the feed to Apple Podcasts Connect or any directory.

If you ever need true privacy (HTTP basic auth, signed URLs), the audio + HTML are portable -- migrate to a host like Transistor's private feeds without rewriting any code.

## Customizing

- **Add or remove feeds:** edit `config/feeds.yaml`. Each entry takes a name, URL, credibility (0-1), and topic tags.
- **Change topic weights or keywords:** edit `config/interests.yaml`. The `weight` field controls relative importance; topics with higher weights surface more.
- **Change voice:** edit `OPENAI_TTS_VOICE` at the top of `src/daily_news/tts.py`. Options: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`.
- **Change digest length:** edit `target_story_count` in `config/interests.yaml` (currently 12).
- **Change delivery time:** edit the `cron:` line in `.github/workflows/daily.yml`. GitHub cron is UTC only.
- **Change visual style:** edit `static/style.css`. The aesthetic is editorial / NYT-mobile (warm cream, serif headlines, sans body, terracotta accent).

## Project layout

```
daily-news/
  config/                  feeds, search queries, topic weights (YAML; no code change to add sources)
  src/daily_news/
    config.py              YAML + .env loader
    db.py                  SQLite schema + queries (article history, digest history)
    dedup.py               URL canonicalization, title normalization, fuzzy match
    fetch.py               concurrent RSS + Google News fetch
    score.py               relevance/credibility/recency/novelty
    summarize.py           Claude Sonnet client + JSON output schema
    tts.py                 OpenAI TTS client with chunking
    render.py              Jinja2 HTML + feedgen podcast RSS
    pipeline.py            orchestrator
    __main__.py            CLI: `python -m daily_news run [--mode dry]`
  templates/digest.html    per-day digest template
  templates/index.html     episode index
  static/style.css         minimalist editorial theme, mobile-first, dark mode aware
  tests/                   pytest covering dedup, scoring, db, config, tts chunking
  .github/workflows/daily.yml   the scheduled job
  data/                    runtime SQLite DB and intermediate audio (gitignored)
  public/                  what gets published to GitHub Pages
```

## Cost

| Component | Per run | Per month (30 runs) |
|-----------|---------|---------------------|
| Claude Sonnet (~25 candidates in, ~12 stories out) | ~$0.05 | ~$1.50 |
| OpenAI TTS HD (~10 min audio) | ~$0.05-0.10 | ~$1.50-3.00 |
| GitHub Actions (~5 min/run on free tier) | $0 | $0 |
| **Total** | **~$0.10-0.15** | **~$3-5** |

## Troubleshooting

- **A feed is dead.** The fetcher logs a warning and skips it. Edit `config/feeds.yaml` to remove or replace.
- **Stories repeat day-to-day.** Check that the `state` branch has `articles.db`. If the branch is missing or empty, the dedup history is starting fresh each run. Re-run after the first successful run; subsequent runs will dedupe.
- **Audio cuts off mid-sentence.** OpenAI TTS has a 4096-char input cap; we chunk at 3500. If chunking still produces a cut, lower `CHUNK_CHAR_LIMIT` in `src/daily_news/tts.py`.
- **The "Why this matters" feels generic.** Sharpen the system prompt in `src/daily_news/summarize.py` -- add concrete details about your work, current projects, and upcoming decisions.
- **Score thresholds need tuning.** Run `python -m daily_news run --mode dry` for several days, watch the top candidates, and adjust topic weights or keywords in `config/interests.yaml`.

## Design choices worth knowing

- **No paid news API.** Curated RSS plus Google News RSS searches gives reliable global coverage and lets us hit niche local stories (Kamloops, Sun Peaks, BC food recalls) without a $449/mo NewsAPI subscription.
- **Pre-filter then LLM.** Articles are filtered, scored, and reduced to ~25 candidates *before* hitting Claude. This makes the LLM step cheap, fast, and predictable.
- **Two layers of dedup.** Canonical URL hashing catches outright duplicates; rapidfuzz title similarity (token_set_ratio, threshold 88) catches the wire-service case where the same Reuters story shows up at five outlets with cosmetic title differences.
- **State in a branch, not a service.** No external database. The SQLite file rides along on a `state` branch. Trivial to debug locally (`git checkout state` and inspect `articles.db`).
- **Visual design is mobile-first and restrained.** No cards, no shadows, no gradient banners. One column, generous whitespace, system serif for headlines, system sans for body, one terracotta accent, dark-mode aware.
