/**
 * Text-to-speech placeholder (ElevenLabs).
 *
 * Future use:
 *   - Convert the Claude-generated audio script into MP3
 *   - Map the in-app voice (Aria / Mason / Sage) to ElevenLabs voice IDs
 *   - Cache the MP3 for the day so the player can load it instantly
 */

export interface TtsRequest {
  text: string;
  voiceId: 'aria' | 'mason' | 'sage';
  speed?: number;
}

export interface TtsResult {
  audioUrl: string;
  durationSeconds: number;
}

export async function synthesize(_req: TtsRequest): Promise<TtsResult> {
  // TODO(integration): POST script to ElevenLabs, persist MP3 to CDN/storage,
  // return durable URL + metadata.
  return { audioUrl: 'https://example.com/today.mp3', durationSeconds: 600 };
}
