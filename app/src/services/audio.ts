/**
 * Audio playback wrapper around `react-native-track-player`.
 *
 * Why RN Track Player and not expo-av? Lock-screen / Control Center
 * controls. expo-av plays in the background, but it does NOT publish
 * Now Playing metadata to MPNowPlayingInfoCenter (iOS) / MediaSession
 * (Android), which is what the lock-screen widget reads. RNTP is
 * purpose-built for this and is the standard pick for podcast apps.
 *
 * The exported `audioController` keeps the same interface the rest of
 * the app already consumes (subscribe / load / toggle / seekTo / etc.)
 * so AppContext didn't need to change.
 *
 * Voice samples (Settings screen) keep using expo-av because they're
 * transient and don't need lock-screen presence.
 */

import { Audio } from 'expo-av';
import TrackPlayer, {
  AppKilledPlaybackBehavior,
  Capability,
  Event,
  RepeatMode,
  State,
} from 'react-native-track-player';

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

export interface TrackMetadata {
  title?: string;
  artist?: string;
  artworkUrl?: string;
  date?: string;
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
  private state: PlaybackState = { ...initialState };
  private listeners = new Set<Listener>();
  private setupDone = false;
  private setupPromise: Promise<void> | null = null;
  private pollHandle: ReturnType<typeof setInterval> | null = null;
  private pendingMetadata: TrackMetadata | null = null;

  async configure(): Promise<void> {
    if (this.setupDone) return;
    if (this.setupPromise) return this.setupPromise;

    this.setupPromise = (async () => {
      try {
        await TrackPlayer.setupPlayer({
          // Buffer aggressively so scrubbing in a 10–15 min file feels
          // instant rather than waiting on network round-trips.
          minBuffer: 30,
          maxBuffer: 90,
          playBuffer: 5,
          waitForBuffer: true,
        });
      } catch (e: any) {
        // setupPlayer throws "The player has already been initialized"
        // if called twice. Safe to ignore — the second call is a no-op.
        if (!String(e?.message ?? '').includes('already been initialized')) {
          throw e;
        }
      }

      await TrackPlayer.updateOptions({
        android: {
          appKilledPlaybackBehavior: AppKilledPlaybackBehavior.PausePlayback,
        },
        // Buttons that show on the lock screen / Control Center.
        capabilities: [
          Capability.Play,
          Capability.Pause,
          Capability.SeekTo,
          Capability.JumpForward,
          Capability.JumpBackward,
          Capability.Stop,
        ],
        // The compact set is what iOS Control Center can fit. JumpForward /
        // JumpBackward there map to the 30s / 15s skip buttons.
        compactCapabilities: [
          Capability.Play,
          Capability.Pause,
          Capability.JumpForward,
          Capability.JumpBackward,
        ],
        forwardJumpInterval: 30,
        backwardJumpInterval: 15,
        progressUpdateEventInterval: 1,
      });

      await TrackPlayer.setRepeatMode(RepeatMode.Off);

      // expo-av audio mode is also configured for the voice-sample sound,
      // and does no harm to also configure here in case any RNTP/expo-av
      // interaction remains.
      try {
        await Audio.setAudioModeAsync({
          staysActiveInBackground: true,
          playsInSilentModeIOS: true,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });
      } catch {
        /* ignore — RNTP owns playback now */
      }

      this.attachEvents();
      this.startPolling();
      this.setupDone = true;
    })();

    return this.setupPromise;
  }

  private attachEvents(): void {
    TrackPlayer.addEventListener(Event.PlaybackState, (data: any) => {
      const isPlaying = data.state === State.Playing;
      const isLoaded = !!this.state.url && data.state !== State.None;
      this.update({ isPlaying, isLoaded });
    });

    TrackPlayer.addEventListener(Event.PlaybackError, (e) => {
      // eslint-disable-next-line no-console
      console.warn('TrackPlayer playback error', e);
    });

    TrackPlayer.addEventListener(Event.PlaybackQueueEnded, () => {
      this.update({ isPlaying: false });
    });
  }

  // RNTP doesn't push position updates as a JS event; we poll while playing.
  private startPolling(): void {
    if (this.pollHandle) return;
    this.pollHandle = setInterval(async () => {
      try {
        const progress = await TrackPlayer.getProgress();
        this.update({
          positionMs: Math.round((progress.position ?? 0) * 1000),
          durationMs: Math.round((progress.duration ?? 0) * 1000),
        });
      } catch {
        /* ignore — controller torn down */
      }
    }, 500);
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

  /**
   * Load a remote audio URL into the player queue. If `metadata` is provided,
   * it populates the lock-screen / Control Center widget. Safe to call
   * repeatedly — re-loading the same URL is a no-op.
   */
  async load(url: string, metadata?: TrackMetadata): Promise<void> {
    await this.configure();

    if (metadata) this.pendingMetadata = metadata;

    if (this.state.url === url) {
      // Same URL already loaded — just refresh metadata if it changed.
      if (metadata) await this.applyMetadata(url, metadata);
      return;
    }

    await TrackPlayer.reset();
    const meta = metadata ?? this.pendingMetadata ?? {};

    await TrackPlayer.add({
      id: url,
      url,
      title: meta.title ?? "Today's Briefing",
      artist: meta.artist ?? 'Daily News',
      ...(meta.artworkUrl ? { artwork: meta.artworkUrl } : {}),
      ...(meta.date ? { album: meta.date } : {}),
    });

    if (this.state.speed !== 1.0) {
      await TrackPlayer.setRate(this.state.speed);
    }

    this.update({
      url,
      isLoaded: true,
      positionMs: 0,
      durationMs: 0,
    });
  }

  private async applyMetadata(url: string, metadata: TrackMetadata): Promise<void> {
    try {
      await TrackPlayer.updateMetadataForTrack(0, {
        title: metadata.title ?? "Today's Briefing",
        artist: metadata.artist ?? 'Daily News',
        ...(metadata.artworkUrl ? { artwork: metadata.artworkUrl } : {}),
        ...(metadata.date ? { album: metadata.date } : {}),
      });
    } catch {
      /* ignore — track may have been removed */
    }
  }

  async unload(): Promise<void> {
    await TrackPlayer.reset();
    this.update({ ...initialState, speed: this.state.speed });
  }

  async play(url?: string, metadata?: TrackMetadata): Promise<void> {
    await this.configure();
    if (url && url !== this.state.url) {
      await this.load(url, metadata);
    }
    await TrackPlayer.play();
  }

  async pause(): Promise<void> {
    await TrackPlayer.pause();
  }

  async toggle(url?: string, metadata?: TrackMetadata): Promise<void> {
    await this.configure();
    if (this.state.isPlaying) {
      await this.pause();
    } else {
      await this.play(url, metadata);
    }
  }

  async seekRelative(deltaMs: number): Promise<void> {
    await this.configure();
    const progress = await TrackPlayer.getProgress();
    const next = Math.max(
      0,
      Math.min(progress.duration ?? 0, (progress.position ?? 0) + deltaMs / 1000),
    );
    await TrackPlayer.seekTo(next);
  }

  async seekTo(positionMs: number): Promise<void> {
    await this.configure();
    const progress = await TrackPlayer.getProgress();
    const next = Math.max(0, Math.min(progress.duration ?? 0, positionMs / 1000));
    await TrackPlayer.seekTo(next);
  }

  async setSpeed(rate: number): Promise<void> {
    await this.configure();
    this.update({ speed: rate });
    await TrackPlayer.setRate(rate);
  }

  private update(patch: Partial<PlaybackState>): void {
    const next = { ...this.state, ...patch };
    // Avoid spamming listeners with identical states (the polling loop
    // would otherwise re-broadcast every 500 ms even when nothing changed).
    const same =
      next.url === this.state.url &&
      next.isLoaded === this.state.isLoaded &&
      next.isPlaying === this.state.isPlaying &&
      next.positionMs === this.state.positionMs &&
      next.durationMs === this.state.durationMs &&
      next.speed === this.state.speed;
    this.state = next;
    if (!same) {
      for (const fn of this.listeners) fn(this.state);
    }
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
 * Voice samples on the Settings screen play through expo-av on a separate
 * Sound. They're short, transient, and don't need a lock-screen presence,
 * so there's no reason to push them through RNTP.
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
  if (samplePlayingId === voiceId) {
    await stopVoiceSample();
    return;
  }
  await stopVoiceSample();
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
