/**
 * daily-news-trigger
 *
 * Scheduled Cloudflare Worker that fires `workflow_dispatch` on the
 * umidya/daily-news GitHub Actions workflow every morning so the briefing
 * is generated and published before Midya's 06:00 PT phone notification.
 *
 * The GH Actions workflow has its own redundant cron schedule (8 entries
 * between 10:23 and 13:47 UTC) as a fallback if this Worker misses, so
 * this Worker is the PRIMARY but not the SOLE trigger.
 */

export interface Env {
	// Fine-grained GitHub PAT with Actions: write on umidya/daily-news.
	// Set with: wrangler secret put GITHUB_PAT
	GITHUB_PAT: string;

	// Defaults provided in wrangler.jsonc; override via vars/secrets if needed.
	GITHUB_OWNER: string;
	GITHUB_REPO: string;
	GITHUB_WORKFLOW: string;
	GITHUB_REF: string;
}

export default {
	async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
		ctx.waitUntil(dispatch(env));
	},

	async fetch(req: Request, env: Env): Promise<Response> {
		const url = new URL(req.url);

		// Manual trigger for debugging: POST /trigger with header
		// `Authorization: Bearer <GITHUB_PAT>` re-fires the workflow.
		if (req.method === "POST" && url.pathname === "/trigger") {
			const auth = req.headers.get("authorization") ?? "";
			if (auth !== `Bearer ${env.GITHUB_PAT}`) {
				return new Response("unauthorized", { status: 401 });
			}
			const result = await dispatch(env);
			return new Response(JSON.stringify(result, null, 2), {
				status: result.ok ? 202 : 502,
				headers: { "content-type": "application/json" },
			});
		}

		return new Response(
			"daily-news trigger worker. Cron fires at 11:30 UTC daily.\n" +
				"POST /trigger with bearer GITHUB_PAT to fire manually.\n",
			{ headers: { "content-type": "text/plain; charset=utf-8" } }
		);
	},
};

interface DispatchResult {
	ok: boolean;
	status: number;
	owner: string;
	repo: string;
	workflow: string;
	ref: string;
	body?: string;
	error?: string;
}

async function dispatch(env: Env): Promise<DispatchResult> {
	const owner = env.GITHUB_OWNER;
	const repo = env.GITHUB_REPO;
	const workflow = env.GITHUB_WORKFLOW;
	const ref = env.GITHUB_REF;
	const endpoint = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

	const summary = { ok: false, status: 0, owner, repo, workflow, ref } as DispatchResult;

	if (!env.GITHUB_PAT) {
		summary.error = "GITHUB_PAT secret is not set on the Worker";
		console.error(summary.error);
		return summary;
	}

	try {
		const r = await fetch(endpoint, {
			method: "POST",
			headers: {
				accept: "application/vnd.github+json",
				authorization: `Bearer ${env.GITHUB_PAT}`,
				"user-agent": "daily-news-trigger/1.0 (+https://github.com/umidya/daily-news)",
				"x-github-api-version": "2022-11-28",
				"content-type": "application/json",
			},
			body: JSON.stringify({ ref, inputs: { force: "false" } }),
		});

		summary.status = r.status;
		summary.ok = r.status === 204;

		if (!summary.ok) {
			summary.body = await r.text();
			console.error("workflow_dispatch failed", summary);
		} else {
			console.log("workflow_dispatch ok", { owner, repo, workflow, ref });
		}
	} catch (err) {
		summary.error = err instanceof Error ? err.message : String(err);
		console.error("workflow_dispatch threw", summary);
	}

	return summary;
}
