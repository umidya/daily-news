/**
 * Persisted user preferences.
 *
 * AppContext loads this on mount and writes back whenever any setting changes.
 * Versioned key so we can migrate cleanly later.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Voice } from '@/types/news';

const KEY = 'prefs.v1';

export interface PersistedPrefs {
  selectedTopics: string[];
  mutedTopics: string[];
  selectedVoice: Voice['id'];
  deliveryHour: number;
  deliveryMinute: number;
  audioOn: boolean;
  digestOn: boolean;
  highQualityOnly: boolean;
  reduceDuplicates: boolean;
  savedStoryIds: string[];
}

export async function loadPrefs(): Promise<Partial<PersistedPrefs> | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Partial<PersistedPrefs>;
  } catch {
    return null;
  }
}

export async function savePrefs(prefs: PersistedPrefs): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    /* non-fatal */
  }
}
