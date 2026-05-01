/**
 * Fetches today's briefing JSON from the GitHub Pages deploy.
 *
 * Schema mirrors src/daily_news/app_export.py on the Python side. Keep in sync.
 * Falls back to mockBriefing when EXPO_PUBLIC_DAILY_NEWS_BASE_URL is unset
 * (i.e. when running against the prototype without a real backend).
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { mockBriefing } from '@/data/mockNews';
import { config, todayJsonUrl } from '@/config';
import type { Briefing } from '@/types/news';

// v5: chapter durations are now weighted by section prose length, not story
// count, so an old cached payload will show the wrong breakdown until a
// fresh fetch.
const CACHE_KEY = 'briefing.today.v5';
// 1 hour TTL — daily-news content is freshest on the morning cron, and a
// shorter window means pull-to-refresh isn't needed as often.
const STALE_AFTER_MS = 1000 * 60 * 60 * 1;

interface CacheEntry {
  fetchedAt: number;
  briefing: Briefing;
}

export type BriefingSource = 'live' | 'cache' | 'mock';

export interface FetchResult {
  briefing: Briefing;
  source: BriefingSource;
  fetchedAt: number;
}

export async function loadTodayBriefing(force = false): Promise<FetchResult> {
  const url = todayJsonUrl();

  // No backend configured → always mock.
  if (!url) {
    return { briefing: mockBriefing, source: 'mock', fetchedAt: Date.now() };
  }

  // Try cache first when not forcing.
  if (!force) {
    const cached = await readCache();
    if (cached && Date.now() - cached.fetchedAt < STALE_AFTER_MS) {
      // Refresh in the background but return cached now.
      void refreshInBackground(url);
      return { briefing: cached.briefing, source: 'cache', fetchedAt: cached.fetchedAt };
    }
  }

  try {
    const live = await fetchLive(url);
    await writeCache(live);
    return { briefing: live, source: 'live', fetchedAt: Date.now() };
  } catch (err) {
    // Network failure or 404 (today's briefing not yet published) → use cache or mock.
    const cached = await readCache();
    if (cached) {
      return { briefing: cached.briefing, source: 'cache', fetchedAt: cached.fetchedAt };
    }
    return { briefing: mockBriefing, source: 'mock', fetchedAt: Date.now() };
  }
}

async function fetchLive(url: string): Promise<Briefing> {
  const res = await fetch(`${url}?t=${Date.now()}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = (await res.json()) as Briefing;
  return data;
}

async function refreshInBackground(url: string): Promise<void> {
  try {
    const fresh = await fetchLive(url);
    await writeCache(fresh);
  } catch {
    // swallow — background refresh only
  }
}

async function readCache(): Promise<CacheEntry | null> {
  try {
    const raw = await AsyncStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as CacheEntry;
  } catch {
    return null;
  }
}

async function writeCache(briefing: Briefing): Promise<void> {
  const entry: CacheEntry = { fetchedAt: Date.now(), briefing };
  try {
    await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(entry));
  } catch {
    /* non-fatal */
  }
}

export function isUsingBackend(): boolean {
  return config.hasBackend;
}
