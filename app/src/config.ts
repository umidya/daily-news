/**
 * App-wide configuration.
 *
 * EXPO_PUBLIC_DAILY_NEWS_BASE_URL — root URL of the GitHub Pages deploy that
 * hosts today.json + audio/<date>.mp3. When unset, the app falls back to mock
 * data so the prototype still works without a backend.
 *
 * Set it by creating app/.env with:
 *   EXPO_PUBLIC_DAILY_NEWS_BASE_URL=https://your-username.github.io/daily-news
 *
 * Then `npx expo start --clear` to re-bake env vars.
 */

const RAW_BASE_URL = process.env.EXPO_PUBLIC_DAILY_NEWS_BASE_URL ?? '';

export const config = {
  baseUrl: RAW_BASE_URL.replace(/\/$/, ''),
  hasBackend: RAW_BASE_URL.length > 0,
  todayJsonPath: '/today.json',
} as const;

export function todayJsonUrl(): string | null {
  if (!config.hasBackend) return null;
  return `${config.baseUrl}${config.todayJsonPath}`;
}
