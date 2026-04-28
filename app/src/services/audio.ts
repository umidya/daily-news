/**
 * Audio playback singleton.
 *
 * Wraps expo-av's Audio.Sound so the rest of the app stays declarative.
 * One sound at a time; loading a new url unloads the previous.
 */

import { Audio } from 'expo-av';

interface Listener {
  (state: PlaybackState): void;
}

export interface PlaybackState {
  url: string | null;
  isLoaded: boolean;
  isPlaying: boolean;
  positionMs: number;
  durationMs: number;
  speed: number;
}

const initialState: PlaybackState = {
  url: null,
  isLoaded: false,
  isPlaying: false,
  positionMs: 0,
  durationMs: 0,
  speed: 1.0,
};

class AudioController {
  private sound: Audio.Sound | null = null;
  private state: PlaybackState = { ...initialState };
  private listeners = new Set<Listener>();

  async configure(): Promise<void> {
    await Audio.setAudioModeAsync({
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
      shouldDuckAndroid: true,
    });
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    fn(this.state);
    return () => {
      this.listeners.delete(fn);
    };
  }

  getState(): PlaybackState {
    return this.state;
  }

  async load(url: string): Promise<void> {
    if (this.state.url === url && this.sound) return;
    await this.unload();
    const { sound, status } = await Audio.Sound.createAsync(
      { uri: url },
      { shouldPlay: false, rate: this.state.speed, shouldCorrectPitch: true },
      (s) => this.onStatus(s),
    );
    this.sound = sound;
    if (status.isLoaded) {
      this.update({
        url,
        isLoaded: true,
        durationMs: status.durationMillis ?? 0,
        positionMs: status.positionMillis ?? 0,
      });
    } else {
      this.update({ url, isLoaded: false });
    }
  }

  async unload(): Promise<void> {
    if (this.sound) {
      try {
        await this.sound.unloadAsync();
      } catch {
        /* ignore */
      }
      this.sound = null;
    }
    this.update({ ...initialState, speed: this.state.speed });
  }

  async play(url?: string): Promise<void> {
    if (url && url !== this.state.url) {
      await this.load(url);
    }
    if (!this.sound) return;
    await this.sound.playAsync();
  }

  async pause(): Promise<void> {
    if (this.sound) await this.sound.pauseAsync();
  }

  async toggle(url?: string): Promise<void> {
    if (this.state.isPlaying) {
      await this.pause();
    } else {
      await this.play(url);
    }
  }

  async seekRelative(deltaMs: number): Promise<void> {
    if (!this.sound) return;
    const next = Math.max(0, Math.min(this.state.durationMs, this.state.positionMs + deltaMs));
    await this.sound.setPositionAsync(next);
  }

  async seekTo(positionMs: number): Promise<void> {
    if (!this.sound) return;
    const next = Math.max(0, Math.min(this.state.durationMs, positionMs));
    await this.sound.setPositionAsync(next);
  }

  async setSpeed(rate: number): Promise<void> {
    this.update({ speed: rate });
    if (this.sound) {
      await this.sound.setRateAsync(rate, true);
    }
  }

  private onStatus(status: any): void {
    if (!status.isLoaded) return;
    this.update({
      isLoaded: true,
      isPlaying: !!status.isPlaying,
      positionMs: status.positionMillis ?? 0,
      durationMs: status.durationMillis ?? this.state.durationMs,
    });
  }

  private update(patch: Partial<PlaybackState>): void {
    this.state = { ...this.state, ...patch };
    for (const fn of this.listeners) fn(this.state);
  }
}

export const audioController = new AudioController();

export function formatMs(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Play a short voice sample on a separate Audio.Sound so the main briefing
 * playback isn't disturbed beyond a pause. The sample auto-unloads when done.
 */
let sampleSound: Audio.Sound | null = null;
let samplePlayingId: string | null = null;
const sampleListeners = new Set<(playingId: string | null) => void>();

function emitSampleState(): void {
  for (const fn of sampleListeners) fn(samplePlayingId);
}

export function subscribeSamplePlaying(fn: (playingId: string | null) => void): () => void {
  sampleListeners.add(fn);
  fn(samplePlayingId);
  return () => {
    sampleListeners.delete(fn);
  };
}

export async function stopVoiceSample(): Promise<void> {
  if (sampleSound) {
    try {
      await sampleSound.stopAsync();
      await sampleSound.unloadAsync();
    } catch {
      /* ignore */
    }
    sampleSound = null;
  }
  samplePlayingId = null;
  emitSampleState();
}

export async function playVoiceSample(voiceId: string, sampleUrl: string): Promise<void> {
  // If the same sample is already playing, treat tap as stop.
  if (samplePlayingId === voiceId) {
    await stopVoiceSample();
    return;
  }
  // Stop any previous sample.
  await stopVoiceSample();
  // Pause main briefing so audio doesn't overlap.
  try {
    if (audioController.getState().isPlaying) {
      await audioController.pause();
    }
  } catch {
    /* ignore */
  }
  try {
    const { sound } = await Audio.Sound.createAsync(
      { uri: sampleUrl },
      { shouldPlay: true },
    );
    sampleSound = sound;
    samplePlayingId = voiceId;
    emitSampleState();
    sound.setOnPlaybackStatusUpdate((status: any) => {
      if (status.isLoaded && status.didJustFinish) {
        sound.unloadAsync().catch(() => {});
        if (sampleSound === sound) {
          sampleSound = null;
          samplePlayingId = null;
          emitSampleState();
        }
      }
    });
  } catch {
    samplePlayingId = null;
    emitSampleState();
  }
}
