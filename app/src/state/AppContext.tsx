import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { defaultMutedTopics, defaultTopics, mockBriefing } from '@/data/mockNews';
import { loadPrefs, savePrefs, type PersistedPrefs } from '@/services/storage';
import { loadTodayBriefing, type BriefingSource } from '@/services/news';
import { audioController, type PlaybackState } from '@/services/audio';
import { cancelDailyBriefing, scheduleDailyBriefing } from '@/services/notifications';
import type { Briefing, Story, TabKey, Voice } from '@/types/news';

interface AppState {
  // Navigation
  activeTab: TabKey;
  setActiveTab: (t: TabKey) => void;

  // Briefing
  briefing: Briefing;
  briefingSource: BriefingSource;
  briefingLoading: boolean;
  refreshBriefing: () => Promise<void>;

  // Audio
  playback: PlaybackState;
  togglePlay: () => Promise<void>;
  skipForward: () => Promise<void>;
  skipBack: () => Promise<void>;
  seekTo: (positionMs: number) => Promise<void>;

  // Saved
  savedStories: Story[];
  savedStoryIds: Set<string>;
  toggleSaved: (story: Story) => void;

  // Personalization
  selectedTopics: string[];
  toggleTopic: (t: string) => void;
  addTopic: (t: string) => void;

  mutedTopics: string[];
  removeMuted: (t: string) => void;
  addMuted: (t: string) => void;

  selectedVoice: Voice['id'];
  setSelectedVoice: (v: Voice['id']) => void;

  deliveryHour: number;
  deliveryMinute: number;
  setDeliveryHour: (h: number) => void;
  setDeliveryMinute: (m: number) => void;

  audioOn: boolean;
  setAudioOn: (v: boolean) => void;
  digestOn: boolean;
  setDigestOn: (v: boolean) => void;

  highQualityOnly: boolean;
  setHighQualityOnly: (v: boolean) => void;
  reduceDuplicates: boolean;
  setReduceDuplicates: (v: boolean) => void;

  playbackSpeed: number;
  cyclePlaybackSpeed: () => Promise<void>;
}

const Ctx = createContext<AppState | undefined>(undefined);

const SPEEDS = [1.0, 1.25, 1.5, 1.75, 2.0, 0.75];

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState<TabKey>('home');

  const [briefing, setBriefing] = useState<Briefing>(mockBriefing);
  const [briefingSource, setBriefingSource] = useState<BriefingSource>('mock');
  const [briefingLoading, setBriefingLoading] = useState(true);

  const [playback, setPlayback] = useState<PlaybackState>(audioController.getState());

  const [savedStories, setSavedStories] = useState<Story[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>(defaultTopics);
  const [mutedTopics, setMutedTopics] = useState<string[]>(defaultMutedTopics);
  const [selectedVoice, setSelectedVoice] = useState<Voice['id']>('onyx');
  const [deliveryHour, setDeliveryHour] = useState(6);
  const [deliveryMinute, setDeliveryMinute] = useState(0);
  const [audioOn, setAudioOn] = useState(true);
  const [digestOn, setDigestOn] = useState(true);
  const [highQualityOnly, setHighQualityOnly] = useState(true);
  const [reduceDuplicates, setReduceDuplicates] = useState(true);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);

  const hydrated = useRef(false);

  const savedStoryIds = useMemo(
    () => new Set(savedStories.map((s) => s.id)),
    [savedStories],
  );

  // Hydrate persisted prefs once on mount.
  useEffect(() => {
    (async () => {
      const prefs = await loadPrefs();
      if (prefs) {
        if (prefs.selectedTopics) setSelectedTopics(prefs.selectedTopics);
        if (prefs.mutedTopics) setMutedTopics(prefs.mutedTopics);
        if (prefs.selectedVoice) setSelectedVoice(prefs.selectedVoice);
        if (typeof prefs.deliveryHour === 'number') setDeliveryHour(prefs.deliveryHour);
        if (typeof prefs.deliveryMinute === 'number') setDeliveryMinute(prefs.deliveryMinute);
        if (typeof prefs.audioOn === 'boolean') setAudioOn(prefs.audioOn);
        if (typeof prefs.digestOn === 'boolean') setDigestOn(prefs.digestOn);
        if (typeof prefs.highQualityOnly === 'boolean') setHighQualityOnly(prefs.highQualityOnly);
        if (typeof prefs.reduceDuplicates === 'boolean') setReduceDuplicates(prefs.reduceDuplicates);
        if (Array.isArray(prefs.savedStories)) setSavedStories(prefs.savedStories);
      }
      hydrated.current = true;
    })();
  }, []);

  // Persist on any change after hydration.
  useEffect(() => {
    if (!hydrated.current) return;
    const prefs: PersistedPrefs = {
      selectedTopics,
      mutedTopics,
      selectedVoice,
      deliveryHour,
      deliveryMinute,
      audioOn,
      digestOn,
      highQualityOnly,
      reduceDuplicates,
      savedStories,
    };
    void savePrefs(prefs);
  }, [
    selectedTopics, mutedTopics, selectedVoice,
    deliveryHour, deliveryMinute,
    audioOn, digestOn, highQualityOnly, reduceDuplicates,
    savedStories,
  ]);

  // Schedule the morning notification when delivery time changes.
  useEffect(() => {
    if (!hydrated.current) return;
    if (!audioOn && !digestOn) {
      void cancelDailyBriefing();
      return;
    }
    void scheduleDailyBriefing(deliveryHour, deliveryMinute);
  }, [deliveryHour, deliveryMinute, audioOn, digestOn]);

  // Initialize audio + subscribe to playback state.
  useEffect(() => {
    void audioController.configure();
    const unsub = audioController.subscribe(setPlayback);
    return unsub;
  }, []);

  // Fetch today's briefing on mount and whenever the user pulls to refresh.
  const refreshBriefing = useCallback(async (): Promise<void> => {
    setBriefingLoading(true);
    try {
      const result = await loadTodayBriefing(true);
      setBriefing(result.briefing);
      setBriefingSource(result.source);
    } finally {
      setBriefingLoading(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      const result = await loadTodayBriefing(false);
      setBriefing(result.briefing);
      setBriefingSource(result.source);
      setBriefingLoading(false);
    })();
  }, []);

  // Pre-load audio whenever the briefing's audio URL changes. Metadata
  // populates the iOS lock-screen / Control Center "Now Playing" widget.
  const audioMetadata = useMemo(
    () => ({
      title: "Today's Briefing",
      artist: 'Daily News',
      artworkUrl: briefing.heroImageUrl,
      date: briefing.date,
    }),
    [briefing.heroImageUrl, briefing.date],
  );

  useEffect(() => {
    const url = briefing.audioUrl;
    if (url) void audioController.load(url, audioMetadata);
  }, [briefing.audioUrl, audioMetadata]);

  const togglePlay = useCallback(async () => {
    await audioController.toggle(briefing.audioUrl, audioMetadata);
  }, [briefing.audioUrl, audioMetadata]);

  const skipForward = useCallback(() => audioController.seekRelative(30_000), []);
  const skipBack = useCallback(() => audioController.seekRelative(-15_000), []);
  const seekTo = useCallback((positionMs: number) => audioController.seekTo(positionMs), []);

  const cyclePlaybackSpeed = useCallback(async () => {
    const next = SPEEDS[(SPEEDS.indexOf(playbackSpeed) + 1) % SPEEDS.length];
    setPlaybackSpeed(next);
    await audioController.setSpeed(next);
  }, [playbackSpeed]);

  const toggleSaved = useCallback((story: Story) => {
    setSavedStories((prev) => {
      const exists = prev.some((s) => s.id === story.id);
      return exists ? prev.filter((s) => s.id !== story.id) : [...prev, story];
    });
  }, []);

  const value = useMemo<AppState>(
    () => ({
      activeTab,
      setActiveTab,
      briefing,
      briefingSource,
      briefingLoading,
      refreshBriefing,
      playback,
      togglePlay,
      skipForward,
      skipBack,
      seekTo,
      savedStories,
      savedStoryIds,
      toggleSaved,
      selectedTopics,
      toggleTopic: (t) =>
        setSelectedTopics((prev) =>
          prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
        ),
      addTopic: (t) =>
        setSelectedTopics((prev) => (prev.includes(t) ? prev : [...prev, t])),
      mutedTopics,
      removeMuted: (t) => setMutedTopics((prev) => prev.filter((x) => x !== t)),
      addMuted: (t) =>
        setMutedTopics((prev) => (prev.includes(t) ? prev : [...prev, t])),
      selectedVoice,
      setSelectedVoice,
      deliveryHour,
      deliveryMinute,
      setDeliveryHour,
      setDeliveryMinute,
      audioOn,
      setAudioOn,
      digestOn,
      setDigestOn,
      highQualityOnly,
      setHighQualityOnly,
      reduceDuplicates,
      setReduceDuplicates,
      playbackSpeed,
      cyclePlaybackSpeed,
    }),
    [
      activeTab,
      briefing,
      briefingSource,
      briefingLoading,
      refreshBriefing,
      playback,
      togglePlay,
      skipForward,
      skipBack,
      seekTo,
      savedStories,
      savedStoryIds,
      toggleSaved,
      selectedTopics,
      mutedTopics,
      selectedVoice,
      deliveryHour,
      deliveryMinute,
      audioOn,
      digestOn,
      highQualityOnly,
      reduceDuplicates,
      playbackSpeed,
      cyclePlaybackSpeed,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApp must be used inside AppProvider');
  return v;
}
