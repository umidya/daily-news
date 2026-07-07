# daily-news-trigger (Cloudflare Worker)

Scheduled Worker that fires `workflow_dispatch` on the
[daily news GitHub Actions workflow](../.github/workflows/daily.yml) at
**11:30 UTC daily** so the briefing is ready before Midya's 06:00 PT
phone notification.

Deployed at `https://daily-news-trigger.umidya.workers.dev`.

The GH Actions workflow has 8 redundant cron entries between 10:23 and
13:47 UTC as a fallback. This Worker is the **primary** but not the
**sole** trigger.

## Why this is in the repo

Before 2026-05-26 this Worker was edited only in the Cloudflare dashboard
and had no source on disk. When it silently missed firing one morning,
there was nothing to debug. Source lives here now so failures are
investigable and changes are reviewable.

## One-time setup (already done — for reference)

1. Worker created in Cloudflare dashboard as `daily-news-trigger`.
2. PAT secret installed:
   ```bash
   cd worker && npx wrangler secret put GITHUB_PAT
   # paste fine-grained PAT with Actions: write on umidya/daily-news
   ```

## Deploy

From this directory:

```bash
npm install      # one-time
npm run deploy   # builds + pushes to Cloudflare
```

`wrangler` will use either:
- An interactive `wrangler login` browser flow (one-time), or
- A `CLOUDFLARE_API_TOKEN` env var (recommended for CI/scripts).

### Connect to GitHub for auto-deploy (recommended)

In the Cloudflare dashboard: **Workers & Pages → daily-news-trigger →
Settings → Build → Connect to Git → select `umidya/daily-news` → set
root directory to `worker/`**. After that, every push to `main` that
touches `worker/` re-deploys automatically.

## Verify after deploy

```bash
# Should return "daily-news trigger worker. Cron fires at 11:30 UTC daily..."
curl https://daily-news-trigger.umidya.workers.dev/

# Manually fire workflow (requires the same PAT)
curl -X POST https://daily-news-trigger.umidya.workers.dev/trigger \
  -H "Authorization: Bearer <your GITHUB_PAT>"
# Expect HTTP 202 and JSON body with ok: true, status: 204
```

Then watch the run start:

```bash
gh run list --limit 3 --repo umidya/daily-news
```

## Observe

Logs are visible in real time:

```bash
npm run tail
```

Or in the dashboard: **Workers & Pages → daily-news-trigger → Logs**.
Cron firings emit one of two log lines:

- `workflow_dispatch ok` — success (HTTP 204 from GitHub)
- `workflow_dispatch failed` — non-204 response, body included

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Cron didn't fire at all | Cloudflare cron outage; or worker was disabled | [Cloudflare status](https://www.cloudflarestatus.com/); dashboard → Triggers |
| HTTP 401 from GitHub | PAT expired or revoked | Re-issue fine-grained PAT; `wrangler secret put GITHUB_PAT` |
| HTTP 404 from GitHub | Workflow file renamed/moved | Confirm `daily.yml` exists on `main` |
| HTTP 422 from GitHub | `ref` doesn't exist or workflow doesn't accept `force` input | Confirm `main` branch + `inputs.force` still in workflow |

## Why not just rely on GH Actions cron?

GitHub Actions free-tier scheduled crons are historically delayed
3–7 hours under load. For a breakfast briefing that needs to be ready
by 07:00 PT, a Cloudflare Worker cron (production-grade SLA) is the
only trigger that fires reliably on time. The GH Actions cron entries
exist as fallback only.
