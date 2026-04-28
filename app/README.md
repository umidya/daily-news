# Daily News — Mobile App Prototype

A minimal, premium mobile-first prototype that gives Midya a curated 10-minute audio news briefing each morning, plus a written digest to read when she can't listen.

This folder is the **app prototype only** (React Native + Expo + TypeScript with mock data). The original Python news pipeline lives at the project root (RSS pull → Claude curation → OpenAI TTS → static feed). The two will be wired together once the prototype's UI is locked.

## Run locally

You'll need Node 18+ installed. If you don't have it:

```bash
# macOS
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install node
```

Then from this folder:

```bash
cd ~/Desktop/AI-Projects/daily-news/app
npm install
npx expo start
```

Press `i` for the iOS simulator, `a` for Android, or `w` for web. On a real phone, scan the QR code with the Expo Go app.

## Structure

```
app/
├── App.tsx                      # Entry — provides AppContext + tab switcher
├── src/
│   ├── theme/                   # colors, typography, spacing, radii, shadows
│   ├── types/news.ts            # Story / Briefing / Voice / TabKey
│   ├── data/mockNews.ts         # All sample copy + briefing payload
│   ├── components/              # Reusable UI (15 components)
│   ├── screens/                 # Home / Audio / Digest / Saved / Settings
│   ├── services/                # Placeholder integrations:
│   │   ├── claude.ts            #   curation + script generation
│   │   ├── news.ts              #   RSS / NewsAPI client
│   │   ├── tts.ts               #   ElevenLabs voice synthesis
│   │   └── email.ts             #   morning delivery
│   └── state/AppContext.tsx     # Single context for all UI state
```

## Mock data lives here

`src/data/mockNews.ts` — change the headlines, summaries, categories, voices, default topics, and muted topics. The four screens read straight from this file.

## Topics & visual settings

- **Topics list** → `defaultTopics` and `ALL_TOPICS` (in `screens/SettingsScreen.tsx`)
- **Muted topics** → `defaultMutedTopics`
- **Voices** → `voices`
- **Categories + colors** → `theme/colors.ts` (`CategoryName` and `categoryStyles`)
- **All other tokens** → individual files in `theme/`

To add a new topic that should also appear as a story category, add it to `CategoryName` in `theme/colors.ts`, give it an entry in `categoryStyles`, and you're done — `CategoryPill` will pick it up.

## How future API integration will work

Each `src/services/*.ts` file is a thin async function with a TODO. Replace the mock return value with a real call (e.g. via `fetch` to a thin server that wraps Anthropic / ElevenLabs / your news pool) and the rest of the app shouldn't need to change.

Recommended flow:

1. **Cron at 5:30 AM PT** (server) — fetch news → call Claude → write JSON briefing + MP3 to storage.
2. **App opens** — `services/news.ts → fetchStories()` and `services/claude.ts → generateBriefing()` pull today's payload.
3. **Audio player** — points at the MP3 URL from `services/tts.ts → synthesize()`.
4. **6:30 AM email** — `services/email.ts → deliverMorning()` sends digest HTML + MP3 link.

For now, all four return mock data so the UI is fully driveable.

## Suggested next steps

1. Lock the visual prototype with Midya — adjust copy, illustration tone, anything that doesn't feel right.
2. Stand up a tiny backend (Cloudflare Worker / Vercel function) that wraps the existing Python pipeline and exposes `/api/briefing/today`.
3. Wire `services/claude.ts` and `services/news.ts` to that endpoint; remove `mockBriefing` fallback.
4. Add `expo-av` for actual audio playback; load the MP3 URL.
5. Add `expo-notifications` + a cron-triggered push for the 6:30 AM ping.
6. Build the email template that mirrors the Digest screen's layout for the "can't listen" case.

## Why structure looks like this

- **No React Navigation** — for this prototype, a single AppContext + a tab switcher in `App.tsx` is simpler and avoids a big dependency. Easy to swap to `@react-navigation/bottom-tabs` later if deeper navigation is needed.
- **SVG illustrations, not images** — the sunrise/mountain/city art and story thumbnails are pure SVG so the bundle stays small and everything stays crisp at any size. Replace with stock images later if desired.
- **System fonts** — uses `Georgia` (iOS) / `serif` (Android) for the editorial feel without loading custom fonts. Swap to Lora / Playfair Display via `@expo-google-fonts` if you want exact match.
