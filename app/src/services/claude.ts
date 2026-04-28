/**
 * Claude API placeholder.
 *
 * Future use:
 *   - Curate the day's stories from a raw RSS/news pool
 *   - Generate the 10-min audio script
 *   - Compose the written digest copy and "Why it matters" callout
 *
 * Integration sketch (later):
 *   import Anthropic from '@anthropic-ai/sdk';
 *   const client = new Anthropic({ apiKey: process.env.EXPO_PUBLIC_ANTHROPIC_KEY! });
 *   const reply = await client.messages.create({
 *     model: 'claude-opus-4-7',
 *     max_tokens: 4000,
 *     system: "You are Midya's morning briefing editor...",
 *     messages: [{ role: 'user', content: rawStoriesJson }],
 *   });
 *
 * Note: in production, prefer a thin server (Cloudflare Worker / Vercel function)
 * so the Anthropic key never lives on-device.
 */

import type { Briefing } from '@/types/news';
import { mockBriefing } from '@/data/mockNews';

export async function generateBriefing(): Promise<Briefing> {
  // TODO(integration): call the curation/script worker that wraps Claude.
  return mockBriefing;
}
